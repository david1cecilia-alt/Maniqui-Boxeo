"""Fase 3 – comprobación de trabajo/boxeador.blend (NO se guarda: solo se lee).

1. Fotograma de impacto de cada golpe (+ los 2 de alrededor): renders frente/lado.
2. Choques por acción y fotograma: ropa vs cuerpo, guante vs cabeza / cuerpo /
   otro guante, hueco entre guante y antebrazo.
3. Bloqueo y esquivas: inicio, medio y final (renders).
4. Tabla resumen y datos para la propuesta de la Fase 4.
Escribe trabajo/fase3_resumen.txt y PNG en trabajo/capturas/.

Uso:
  blender.exe --background --python scripts/fase3_comprobar.py
"""
import os
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun as C  # noqa: E402

BLEND = os.path.join(C.TRABAJO, "boxeador.blend")
P = "mixamorig:"
FPS = 30.0
VISTAS = {"frente": Vector((0, -1, 0)), "lado": Vector((1, 0, 0))}  # lado = desde su izquierda

# golpe -> criterio de impacto
GOLPES = {
    "jab": "lejos", "recto": "lejos", "crochet_trasero_cuerpo": "lejos",
    "crochet_adelantado": "velocidad", "crochet_trasero": "velocidad",
    "gancho_adelantado_cuerpo": "velocidad", "gancho_trasero_cuerpo": "velocidad",
}
OTRAS = ["bloqueo", "esquiva_avanzando", "esquiva_retrocediendo"]
UMBRAL_CM = 0.2   # por debajo no se cuenta

bpy.ops.wm.open_mainfile(filepath=BLEND)
esc = bpy.context.scene
arm = bpy.data.objects["Boxeador"]
cuerpo = bpy.data.objects["Cuerpo"]
prendas = [bpy.data.objects["Pantalon"], bpy.data.objects["Botas"]]
guantes = {"Left": bpy.data.objects["Guante_Left"], "Right": bpy.data.objects["Guante_Right"]}
ACCIONES = sorted(a.name for a in bpy.data.actions)

out = []


def p(*a):
    linea = " ".join(str(x) for x in a)
    out.append(linea)
    print(linea)


def poner(accion, f):
    a = bpy.data.actions[accion]
    arm.animation_data.action = a
    if arm.animation_data.action_slot is None:
        arm.animation_data.action_slot = a.slots[0]
    esc.frame_set(f)


def rango(accion):
    a = bpy.data.actions[accion]
    return int(a.frame_range[0]), int(a.frame_range[1])


def tramos(fotos):
    if not fotos:
        return "-"
    fotos = sorted(fotos)
    res, ini, ant = [], fotos[0], fotos[0]
    for f in fotos[1:] + [None]:
        if f is None or f != ant + 1:
            res.append(f"{ini}" if ini == ant else f"{ini}-{ant}")
            if f is not None:
                ini = f
        if f is not None:
            ant = f
    return ", ".join(res)


def coords_eval(ob, normales=False):
    dg = bpy.context.evaluated_depsgraph_get()
    oe = ob.evaluated_get(dg)
    me = oe.to_mesh()
    n = len(me.vertices)
    a = np.empty(n * 3, dtype=np.float64)
    me.vertices.foreach_get("co", a)
    M = np.array(oe.matrix_world)
    a = a.reshape(n, 3) @ M[:3, :3].T + M[:3, 3]
    nr = None
    if normales:
        nr = np.empty(n * 3, dtype=np.float64)
        me.vertex_normals.foreach_get("vector", nr)
        nr = nr.reshape(n, 3) @ np.linalg.inv(M[:3, :3])  # (M^-T n)
        nr /= np.linalg.norm(nr, axis=1, keepdims=True)
    oe.to_mesh_clear()
    return a, nr


# ---------------------------------------------------------------- preparación (solo en memoria)
mod_mask = next(m for m in cuerpo.modifiers if m.type == "MASK")
mod_solid = [next(m for m in o.modifiers if m.type == "SOLIDIFY") for o in prendas]


def modo_analisis(activo):
    """Sin Mask (índices completos del cuerpo) y sin Solidify (cara interior de la ropa)."""
    mod_mask.show_viewport = not activo
    for m in mod_solid:
        m.show_viewport = not activo


# regiones del cuerpo por grupo dominante
vg_nombre = {g.index: g.name.split(":")[-1] for g in cuerpo.vertex_groups}
dominante = []
peso_mano = np.zeros(len(cuerpo.data.vertices))
for v in cuerpo.data.vertices:
    mejor, nombre = 0.0, None
    for e in v.groups:
        n = vg_nombre[e.group]
        if n in ("LeftHand", "RightHand"):
            peso_mano[v.index] = max(peso_mano[v.index], e.weight)
        if not n.startswith("ocultar") and e.weight > mejor:
            mejor, nombre = e.weight, n
    dominante.append(nombre or "")
dominante = np.array(dominante)
# lo que esconde el Mask (manos y, con la ropa v2, también los pies dentro de las botas)
g_mask = cuerpo.vertex_groups[mod_mask.vertex_group].index
peso_mask = np.zeros(len(cuerpo.data.vertices))
for v in cuerpo.data.vertices:
    for e in v.groups:
        if e.group == g_mask:
            peso_mask[v.index] = e.weight
oculto = peso_mask > mod_mask.threshold
CABEZA = np.isin(dominante, ["Head", "Neck", "HeadTop_End"]) & ~oculto
region_cuerpo = {lado: ~np.isin(dominante, ["Head", "Neck", "HeadTop_End", "LeftHand", "RightHand",
                                            lado + "ForeArm"]) & ~oculto
                 for lado in ("Left", "Right")}
# borde del Mask: vértices visibles pegados a vértices ocultos, por lado
borde = {"Left": set(), "Right": set()}
for e in cuerpo.data.edges:
    a, b = e.vertices
    if oculto[a] != oculto[b]:
        vis, osc = (a, b) if not oculto[a] else (b, a)
        if dominante[osc] in ("LeftHand", "RightHand"):   # solo el borde de las manos (guantes)
            borde["Left" if dominante[osc] == "LeftHand" else "Right"].add(vis)
borde = {k: np.array(sorted(v)) for k, v in borde.items()}


# ropa: vértices VISIBLES del cuerpo que en reposo quedan dentro de cada prenda; en cada
# fotograma se mide si salen por fuera de la superficie de la prenda (sin Solidify)
def bvh_prenda(o):
    """Superficie de la prenda; del pantalón solo las perneras (material 0): el borde de la
    cinturilla, al ser la superficie más cercana a la ingle, daba falsos 'fuera'."""
    dg = bpy.context.evaluated_depsgraph_get()
    oe = o.evaluated_get(dg)
    me = oe.to_mesh()
    M = oe.matrix_world
    polys = [p.vertices[:] for p in me.polygons if o.name != "Pantalon" or p.material_index == 0]
    t = BVHTree.FromPolygons([M @ v.co for v in me.vertices], polys)
    oe.to_mesh_clear()
    return t


def fuera_de_prenda(pts, arbol, maxd=0.06):
    """Distancia (m) a la que cada punto queda FUERA de la prenda (0 si está dentro o lejos)."""
    res = np.zeros(len(pts))
    for i, p in enumerate(pts):
        loc, nor, _, dist = arbol.find_nearest(Vector(p), maxd)
        if loc is not None and (Vector(p) - loc).dot(nor) > 0:
            res[i] = dist
    return res


mod_mask.show_viewport = False
for m in [next(m for m in o.modifiers if m.type == "SOLIDIFY") for o in prendas]:
    m.show_viewport = False
arm.data.pose_position = "REST"
bpy.context.view_layer.update()
_cu_rest = np.array([cuerpo.matrix_world @ v.co for v in cuerpo.data.vertices])
DENTRO_ROPA = []
Z_PRENDA = [(0.735, 0.975), (-1.0, 0.29)]   # pantalón (entre el bajo y la cinturilla), botas (caña)
for o, (z0, z1) in zip(prendas, Z_PRENDA):
    arbol = bvh_prenda(o)
    idx = []
    for i in np.where(~oculto & (_cu_rest[:, 2] >= z0) & (_cu_rest[:, 2] <= z1))[0]:
        loc, nor, _, dist = arbol.find_nearest(Vector(_cu_rest[i]), 0.08)
        if loc is not None and (Vector(_cu_rest[i]) - loc).dot(nor) < 0:
            idx.append(i)
    DENTRO_ROPA.append(np.array(idx, dtype=int))
arm.data.pose_position = "POSE"
bpy.context.view_layer.update()


# guantes: piezas convexas (puño y manga) -> test de semiplanos
def piezas(ob):
    me = ob.data
    padre = list(range(len(me.vertices)))

    def raiz(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i
    for e in me.edges:
        a, b = raiz(e.vertices[0]), raiz(e.vertices[1])
        padre[a] = b
    grupos = {}
    for poly in me.polygons:
        grupos.setdefault(raiz(poly.vertices[0]), []).append(poly.vertices[:3])
    return [np.array(t) for t in grupos.values()]


PIEZAS = {lado: piezas(ob) for lado, ob in guantes.items()}
VERTS_G = {lado: np.array([v.co[:] for v in ob.data.vertices]) for lado, ob in guantes.items()}


def verts_guante(lado):
    M = np.array(guantes[lado].matrix_world)
    return VERTS_G[lado] @ M[:3, :3].T + M[:3, 3]


def planos(lado):
    vw = verts_guante(lado)
    res = []
    for tri in PIEZAS[lado]:
        a, b, c = vw[tri[:, 0]], vw[tri[:, 1]], vw[tri[:, 2]]
        n = np.cross(b - a, c - a)
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        cen = vw[np.unique(tri)].mean(axis=0)
        if ((cen - a) * n).sum(axis=1).max() > 0:   # normales hacia fuera
            n = -n
        res.append((a, n, cen, np.linalg.norm(vw[np.unique(tri)] - cen, axis=1).max()))
    return res


def dist_signo(pts, pl):
    """Distancia con signo de cada punto al guante (negativo = dentro; profundidad exacta en piezas convexas)."""
    if len(pts) == 0:
        return np.zeros(0)
    d = np.full(len(pts), np.inf)
    for a, n, cen, rad in pl:
        cerca = np.linalg.norm(pts - cen, axis=1) < rad + 0.15
        if not cerca.any():
            continue
        q = pts[cerca]
        s = ((q[:, None, :] - a[None, :, :]) * n[None, :, :]).sum(axis=2).max(axis=1)
        d[cerca] = np.minimum(d[cerca], s)
    return d


def penetra(pts, pl):
    d = dist_signo(pts, pl)
    dentro = d < 0
    return float(-d[dentro].min()) if dentro.any() else 0.0


def penetra_zonas(idx, cu, pl):
    """Profundidad máx. y zonas del cuerpo (grupo dominante) metidas en el guante (> 2 mm)."""
    d = dist_signo(cu[idx], pl)
    dentro = d < -0.002
    if not dentro.any():
        return max(0.0, float(-d.min())) if len(d) else 0.0, ""
    g, c = np.unique(dominante[idx[dentro]], return_counts=True)
    return float(-d.min()), "+".join(n for _, n in sorted(zip(c, g), reverse=True)[:2])


# ---------------------------------------------------------------- 1. choques por acción
CHOQUES = ["pantalon_cuerpo", "botas_cuerpo", "guante_cabeza", "guante_cuerpo",
           "guante_guante", "hueco_guante_antebrazo"]
datos, zonas = {}, {}
IDX_CUERPO = {l: np.where(region_cuerpo[l])[0] for l in guantes}
modo_analisis(True)
for accion in ACCIONES:
    f0, f1 = rango(accion)
    reg = {k: {} for k in CHOQUES}
    zonas[accion] = {}
    for f in range(f0, f1 + 1):
        poner(accion, f)
        cu, _ = coords_eval(cuerpo)
        # ropa: el cuerpo que en reposo queda dentro no debe salir por fuera de la prenda
        for o, idx, k in zip(prendas, DENTRO_ROPA, ("pantalon_cuerpo", "botas_cuerpo")):
            s = fuera_de_prenda(cu[idx], bvh_prenda(o)) if len(idx) else np.zeros(1)
            reg[k][f] = float(s.max())
        pl = {lado: planos(lado) for lado in guantes}
        reg["guante_cabeza"][f] = max(penetra(cu[CABEZA], pl[l]) for l in guantes)
        res = [(penetra_zonas(IDX_CUERPO[l], cu, pl[l]), l) for l in guantes]
        (prof, zona), lado = max(res, key=lambda x: x[0][0])
        reg["guante_cuerpo"][f] = prof
        zonas[accion][f] = f"guante {lado[0]} en {zona}" if zona else ""
        reg["guante_guante"][f] = max(penetra(verts_guante("Left"), pl["Right"]),
                                      penetra(verts_guante("Right"), pl["Left"]))
        hueco = 0.0
        for l in guantes:
            d = dist_signo(cu[borde[l]], pl[l])
            hueco = max(hueco, float(d.max()))
        reg["hueco_guante_antebrazo"][f] = max(hueco, 0.0)
    datos[accion] = reg
    print("[CHOQUES]", accion)
modo_analisis(False)

p("=== 1. CHOQUES POR ACCIÓN (cm; solo > %.1f cm) ===" % UMBRAL_CM)
p("pantalon/botas_cuerpo = cuánto sale por fuera de la prenda el cuerpo visible que en reposo")
p("queda dentro; guante_* = profundidad de penetración (exacta: el guante son piezas convexas);")
p("hueco = cuánto queda fuera del guante el borde de la mano oculta por el Mask (agujero visible).")
filas = []
GRAV = {  # (alta, media) en cm
    "pantalon_cuerpo": (1.0, 0.3), "botas_cuerpo": (1.0, 0.3),
    "guante_cabeza": (2.0, 0.5), "guante_cuerpo": (3.0, 1.0),
    "guante_guante": (3.0, 1.0), "hueco_guante_antebrazo": (1.0, 0.3),
}
for accion in ACCIONES:
    p(f"\n-- {accion} ({rango(accion)[1]} fot.)")
    for k in CHOQUES:
        serie = {f: v * 100 for f, v in datos[accion][k].items()}
        malos = [f for f, v in serie.items() if v > UMBRAL_CM]
        if not malos:
            p(f"   {k:24} OK")
            continue
        fmax = max(serie, key=serie.get)
        vmax = serie[fmax]
        alta, media = GRAV[k]
        g = "alta" if vmax > alta else ("media" if vmax > media else "baja")
        extra = f" ({zonas[accion][fmax]})" if k == "guante_cuerpo" and zonas[accion].get(fmax) else ""
        p(f"   {k:24} {len(malos):3} fot. [{tramos(malos)}]  máx. {vmax:.1f} cm en fot. {fmax}{extra}  -> {g}")
        filas.append((accion, k + extra, tramos(malos), vmax, fmax, g))


# ---------------------------------------------------------------- 2. impactos
def centro_guante(lado):
    vw = verts_guante(lado)
    return vw[np.unique(PIEZAS[lado][0])].mean(axis=0)   # centro del puño


def pistas(accion):
    f0, f1 = rango(accion)
    res = {"Left": {}, "Right": {}, "Head": {}, "Hips": {}}
    for f in range(f0, f1 + 1):
        poner(accion, f)
        for l in guantes:
            res[l][f] = centro_guante(l)
        res["Head"][f] = np.array(arm.matrix_world @ arm.pose.bones[P + "Head"].head)
        res["Hips"][f] = np.array(arm.matrix_world @ arm.pose.bones[P + "Hips"].head)
    return res


p("\n=== 2. FOTOGRAMA DE IMPACTO ===")
impactos = {}
for golpe, criterio in GOLPES.items():
    pt = pistas(golpe)
    f0, f1 = rango(golpe)
    desp = {l: {f: np.linalg.norm(pt[l][f] - pt[l][f0]) for f in pt[l]} for l in guantes}
    mano = max(guantes, key=lambda l: max(desp[l].values()))
    f_lejos = max(desp[mano], key=desp[mano].get)
    vel = {f: np.linalg.norm(pt[mano][f + 1] - pt[mano][f - 1]) / 2 * FPS for f in range(f0 + 1, f1)}
    ida = {f: v for f, v in vel.items() if f <= f_lejos + 2}
    f_vel = max(ida, key=ida.get)
    f_imp = f_lejos if criterio == "lejos" else f_vel
    # ventana del golpe: arranque (30 % del pico de velocidad) y vuelta (desp. < 20 % del máximo)
    pico = ida[f_vel]
    arranque = next(f for f in sorted(ida) if ida[f] > 0.3 * pico)
    vuelta = next((f for f in range(f_lejos, f1 + 1) if desp[mano][f] < 0.2 * desp[mano][f_lejos]), f1)
    otra = "Right" if mano == "Left" else "Left"
    guardia_otra = np.linalg.norm((pt[otra][f_imp] - pt["Head"][f_imp]) - (pt[otra][f0] - pt["Head"][f0]))
    altura = (pt[mano][f_imp][2] - pt["Head"][f_imp][2]) * 100
    impactos[golpe] = dict(mano=mano, f=f_imp, f_lejos=f_lejos, f_vel=f_vel, vel=pico,
                           alcance=desp[mano][f_lejos], arranque=arranque, vuelta=vuelta,
                           otra_mov=guardia_otra)
    p(f"  {golpe:24} mano {mano:5} criterio {criterio:9} -> IMPACTO fot. {f_imp:3}"
      f" (más lejos fot. {f_lejos}, {desp[mano][f_lejos] * 100:.0f} cm; pico vel. fot. {f_vel}, {pico:.1f} m/s)"
      f" | guante a {altura:+.0f} cm de la base de la cabeza"
      f" | golpe fot. {arranque}-{vuelta} | la otra mano se mueve {guardia_otra * 100:.0f} cm respecto a la cabeza")
p("  Nota: en los dos ganchos de Mixamo el guante golpea a la altura de la cadera/abdomen (gancho")
p("  al cuerpo) y no sube a la barbilla: el pico de velocidad es la salida hacia delante y arriba.")

# ---------------------------------------------------------------- 3. datos para la Fase 4
p("\n=== 3. DATOS PARA LA FASE 4 (guardia) ===")
poner("guardia", 1)
hb = arm.pose.bones[P + "Head"]
Mh = arm.matrix_world @ hb.matrix
eje = {k: np.array(Mh.col[i][:3]) / np.linalg.norm(Mh.col[i][:3]) for i, k in enumerate("xyz")}
# eje adelante de la cabeza: el que más se parece a -Y en el mundo
adel_k = max(("x", "z"), key=lambda k: abs(eje[k] @ np.array([0, -1, 0])))
adel = eje[adel_k] * np.sign(eje[adel_k] @ np.array([0, -1, 0]))
arriba = eje["y"]
lat = np.cross(arriba, adel)            # hacia su izquierda
lat *= np.sign(lat @ np.array([1, 0, 0]))
cab = (np.array(arm.matrix_world @ hb.head) + np.array(arm.matrix_world @ hb.tail)) / 2
p(f"  centro de la cabeza (guardia fot. 1): {np.round(cab, 3)}")
for l in guantes:
    c = centro_guante(l) - cab
    p(f"  guante {l:5}: lateral {c @ lat * 100:+.1f} cm (+ = su izquierda), delante {c @ adel * 100:+.1f} cm,"
      f" altura {c @ arriba * 100:+.1f} cm respecto al centro de la cabeza")
cl, cr = centro_guante("Left") - cab, centro_guante("Right") - cab
p(f"  separación lateral entre guantes: {(cl - cr) @ lat * 100:+.1f} cm"
  f" ({'CRUZADOS' if (cl - cr) @ lat < 0 else 'sin cruzar'}; > 0 = cada uno en su lado)")
p("  ¿Las acciones empiezan en la guardia? diferencia del fot. 1 con guardia fot. 1 (guantes respecto a la cadera):")
pt_g = {l: centro_guante(l) - np.array(arm.matrix_world @ arm.pose.bones[P + "Hips"].head) for l in guantes}
for accion in ACCIONES:
    poner(accion, rango(accion)[0])
    hp = np.array(arm.matrix_world @ arm.pose.bones[P + "Hips"].head)
    d = max(np.linalg.norm((centro_guante(l) - hp) - pt_g[l]) for l in guantes)
    p(f"     {accion:24} {d * 100:5.1f} cm")

# ---------------------------------------------------------------- 4. tabla resumen
p("\n=== 4. TABLA RESUMEN ===")
p(f"{'acción':24} | {'qué falla':44} | {'fotogramas':32} | {'máx.':>8} | gravedad")
orden = {"alta": 0, "media": 1, "baja": 2}
for accion, k, tr, vmax, fmax, g in sorted(filas, key=lambda x: (orden[x[5]], x[0])):
    p(f"{accion:24} | {k:44} | {tr[:32]:32} | {vmax:5.1f} cm | {g} (peor fot. {fmax})")


# ---------------------------------------------------------------- 5. renders
esc.render.engine = "BLENDER_WORKBENCH"
esc.render.resolution_x = esc.render.resolution_y = 1024
esc.render.image_settings.file_format = "PNG"
sh = esc.display.shading
sh.light, sh.color_type = "STUDIO", "MATERIAL"
sh.show_cavity = sh.show_object_outline = True
w = bpy.data.worlds.new("fondo")
w.color = (0.92, 0.92, 0.92)
esc.world = w


def bbox():
    pts = np.vstack([coords_eval(o)[0] for o in bpy.data.objects if o.type == "MESH"])
    return Vector(pts.min(axis=0)), Vector(pts.max(axis=0))


def serie(accion, fotos, vistas, prefijo):
    cajas = []
    for f in fotos.values():
        poner(accion, f)
        cajas.append(bbox())
    mn = Vector([min(c[0][i] for c in cajas) for i in range(3)])
    mx = Vector([max(c[1][i] for c in cajas) for i in range(3)])
    for v in vistas:
        d = VISTAS[v]
        ancho = (mx.x - mn.x) if v == "frente" else (mx.y - mn.y)
        cd = bpy.data.cameras.new("cam")
        cd.type, cd.ortho_scale, cd.clip_end = "ORTHO", max(mx.z - mn.z, ancho) * 1.12, 100
        cam = bpy.data.objects.new("cam", cd)
        esc.collection.objects.link(cam)
        cam.location = (mn + mx) / 2 + d * 10
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        esc.camera = cam
        for etq, f in fotos.items():
            poner(accion, f)
            esc.render.filepath = os.path.join(C.CAPTURAS, f"{prefijo}_{accion}_{etq}_f{f:03d}_{v}.png")
            bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(cam)


for golpe, im in impactos.items():
    f = im["f"]
    serie(golpe, {"1antes": f - 1, "2impacto": f, "3despues": f + 1}, ["frente", "lado"], "fase3")
for accion in OTRAS:
    f0, f1 = rango(accion)
    serie(accion, {"1ini": f0, "2medio": (f0 + f1) // 2, "3fin": f1}, ["frente", "lado"], "fase3")

with open(os.path.join(C.TRABAJO, "fase3_resumen.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out) + "\n")
print("FIN FASE 3 (el .blend no se ha guardado)")
