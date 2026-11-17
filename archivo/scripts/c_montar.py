"""Variante C – mezcla: cuerpo de boxeador.blend (v2) + pantalón y guantes del modelo B.

- Se quitan el pantalón y los guantes de la ropa v2; las botas rojas v2 se quedan.
- Guantes de B (manopla cortada bajo el puño de velcro + puño): se llevan del hueso Hand de B
  al hueso Hand de A (misma posición relativa), escalados para que el puño abrace la muñeca
  de A, y se emparentan al hueso Hand (piezas rígidas, sin pesos), como en la v2.
- Pantalón de B: se lleva de la cadera de B a la de A (alturas por tramos: columna y muslo;
  anchura y fondo por el tamaño de la cintura), se ajusta con un Shrinkwrap 'fuera' (solo
  empuja lo que queda dentro del cuerpo) y se suaviza; pesos copiados del cuerpo (Data
  Transfer) y suavizados, y modificador Armature.
Guarda trabajo/boxeador_c.blend y trabajo/c_resumen.txt.

Uso:
  blender.exe --background --python scripts/c_montar.py
"""
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun as C  # noqa: E402
import modelo_b as MB  # noqa: E402

BLEND_A = os.path.join(C.TRABAJO, "boxeador_v2.blend")
BLEND_C = os.path.join(C.TRABAJO, "boxeador_c.blend")
P = "mixamorig:"
HOLGURA_PUNO = 0.004      # el puño de velcro queda al menos 4 mm por fuera de la muñeca de A
HOLGURA_PANT = 0.006      # el pantalón queda al menos 6 mm por fuera del cuerpo de A

resumen = []


def r(*a):
    linea = " ".join(str(x) for x in a)
    resumen.append(linea)
    print(linea)


# ---------------------------------------------------------------- 0. abrir A y quitar pantalón y guantes v2
bpy.ops.wm.open_mainfile(filepath=BLEND_A)
esc = bpy.context.scene
arm = bpy.data.objects["Boxeador"]
cuerpo = bpy.data.objects["Cuerpo"]
for n in ("Pantalon", "Guante_Left", "Guante_Right"):
    ob = bpy.data.objects.get(n)
    if ob:
        me = ob.data
        bpy.data.objects.remove(ob)
        bpy.data.meshes.remove(me)
accion_a = arm.animation_data.action if arm.animation_data else None
arm.data.pose_position = "REST"
bpy.context.view_layer.update()
mw = cuerpo.matrix_world
CO_A = np.array([mw @ v.co for v in cuerpo.data.vertices])
BVH_A = BVHTree.FromPolygons([Vector(p) for p in CO_A], [p.vertices[:] for p in cuerpo.data.polygons])
W_A = {g.name.split(":")[-1]: np.zeros(len(CO_A)) for g in cuerpo.vertex_groups}
nom = {g.index: g.name.split(":")[-1] for g in cuerpo.vertex_groups}
for v in cuerpo.data.vertices:
    for e in v.groups:
        W_A[nom[e.group]][v.index] = e.weight


def hueso_a(n, cola=False):
    b = arm.data.bones[P + n]
    return arm.matrix_world @ (b.tail_local if cola else b.head_local)


def matriz_a(n):
    m = arm.matrix_world @ arm.data.bones[P + n].matrix_local
    return Matrix.LocRotScale(m.translation, m.to_quaternion(), None)


# ---------------------------------------------------------------- 1. importar B y separar piezas
arm_b, ob_b = MB.cargar_b("B_tmp", "B_tmp_cuerpo")
MB.textura_sin_logo(ob_b)   # guantes sin el logo de la marca
co_b_cuerpo = np.array([v.co[:] for v in ob_b.data.vertices])
W_B = {g.name.split(":")[-1]: np.zeros(len(co_b_cuerpo)) for g in ob_b.vertex_groups}
nom_b = {g.index: g.name.split(":")[-1] for g in ob_b.vertex_groups}
for v in ob_b.data.vertices:
    for e in v.groups:
        W_B[nom_b[e.group]][v.index] = e.weight
objs, sep = MB.separar_piezas(arm_b, ob_b)


def hueso_b(n, cola=False):
    b = arm_b.data.bones[P + n]
    return Vector(b.tail_local if cola else b.head_local)


def matriz_b(n):
    m = arm_b.data.bones[P + n].matrix_local
    return Matrix.LocRotScale(m.translation, m.to_quaternion(), None)


def radio_muneca(co, W, hueso_fn, lado, t_rel):
    """Radio medio de la piel del antebrazo a una distancia t_rel (m) de la muñeca (hacia el codo)."""
    h0, h1 = hueso_fn(lado + "ForeArm"), hueso_fn(lado + "Hand")
    d = (h1 - h0).normalized()
    p0 = h1 - d * t_rel
    dl = (co - np.array(p0)) @ np.array(d)
    sel = (np.abs(dl) < 0.006) & (W[lado + "ForeArm"] + W[lado + "Hand"] > 0.5)
    rad = np.linalg.norm((co[sel] - np.array(p0)) - dl[sel, None] * np.array(d), axis=1)
    return float(np.percentile(rad, 90)) if sel.any() else None


r("=== VARIANTE C ===")
r("  cuerpo, cabeza, ojos y botas rojas de boxeador.blend (v2); pantalón y guantes de B")

# ---------------------------------------------------------------- 2. guantes
ESCALA = {}


def escala_guante(lado):
    g = objs["Guante_" + lado]
    co = np.array([v.co[:] for v in g.data.vertices])
    h0, d, t_ini, t_mitad = sep["corte"][lado]
    muneca_b = hueso_b(lado + "Hand")
    t_rel = float((np.array(muneca_b) - np.array(h0)) @ np.array(d)) - t_ini
    pts = co[((co - np.array(h0)) @ np.array(d)) < t_mitad]
    dl = (pts - np.array(h0)) @ np.array(d)
    r_b = float(np.percentile(np.linalg.norm((pts - np.array(h0)) - dl[:, None] * np.array(d), axis=1), 10))
    r_a = radio_muneca(CO_A, W_A, hueso_a, lado, t_rel) or r_b
    return (r_a + HOLGURA_PUNO) / r_b


# misma escala en los dos guantes (la mayor: el puño abraza las dos muñecas)
S_COMUN = None
for lado in ("Left", "Right"):
    g = objs["Guante_" + lado]
    me = g.data
    co = np.array([v.co[:] for v in me.vertices])
    h0, d, t_ini, t_mitad = sep["corte"][lado]
    muneca_b = hueso_b(lado + "Hand")
    if S_COMUN is None:
        # guante entero: solo la proporción de alturas (más grande chocaban entre sí en la guardia)
        S_COMUN = (CO_A[:, 2].max() - CO_A[:, 2].min()) / (co_b_cuerpo[:, 2].max() - co_b_cuerpo[:, 2].min())
    # el puño de velcro (y la manopla que queda dentro) se ensancha en radial para abrazar la muñeca de A
    k_r = max(1.0, escala_guante(lado) / S_COMUN)
    t_fin = 2 * t_mitad - t_ini
    tv = (co - np.array(h0)) @ np.array(d)
    peso = np.clip((t_fin + 0.01 - tv) / 0.02, 0, 1)
    eje_p = np.array(h0) + tv[:, None] * np.array(d)
    co = eje_p + (co - eje_p) * (1 + (k_r - 1) * peso)[:, None]
    for i, v in enumerate(me.vertices):
        v.co = Vector(co[i])
    # radio interior del puño de velcro de B (piezas sueltas del puño) y de la muñeca de A a esa altura
    t_rel = float((np.array(muneca_b) - np.array(h0)) @ np.array(d)) - t_ini   # inicio del puño -> muñeca
    pts_puno = co[((co - np.array(h0)) @ np.array(d)) < t_mitad]
    dl = (pts_puno - np.array(h0)) @ np.array(d)
    rad_b = np.linalg.norm((pts_puno - np.array(h0)) - dl[:, None] * np.array(d), axis=1)
    r_puno_b = float(np.percentile(rad_b, 10))
    r_mun_a = radio_muneca(CO_A, W_A, hueso_a, lado, t_rel) or r_puno_b
    alto_a, alto_b = CO_A[:, 2].max() - CO_A[:, 2].min(), co_b_cuerpo[:, 2].max() - co_b_cuerpo[:, 2].min()
    s = S_COMUN
    M = matriz_a(lado + "Hand") @ Matrix.Scale(s, 4) @ matriz_b(lado + "Hand").inverted()
    for v in me.vertices:
        v.co = M @ v.co
    g.vertex_groups.clear()
    for m in list(g.modifiers):
        g.modifiers.remove(m)
    g.parent = None
    g.matrix_world = Matrix()
    hn = P + lado + "Hand"
    hueso = arm.data.bones[hn]
    g.parent = arm
    g.parent_type = "BONE"
    g.parent_bone = hn
    g.matrix_parent_inverse = (arm.matrix_world @ hueso.matrix_local @ Matrix.Translation((0, hueso.length, 0))).inverted()
    vs = np.array([v.co[:] for v in me.vertices])
    ext = vs.max(0) - vs.min(0)
    r(f"  Guante_{lado}: {len(me.polygons)} caras, escala x{s:.3f} (altura A/B), puño de velcro ensanchado"
      f" x{k_r:.3f} en radial (puño B r={r_puno_b * 100:.1f} cm, muñeca A r={r_mun_a * 100:.1f} cm),"
      f" caja {np.round(ext * 100, 1)} cm,"
      f" emparentado a {hn}, sin pesos")

# ---------------------------------------------------------------- 3. pantalón: llevar de B a A
pant = objs["Pantalon"]
me = pant.data
co = np.array([v.co[:] for v in me.vertices])
zb_cad, za_cad = hueso_b("Hips").z, hueso_a("Hips").z
zb_col, za_col = hueso_b("Spine1").z, hueso_a("Spine1").z
zb_rod, za_rod = hueso_b("LeftLeg").z, hueso_a("LeftLeg").z
k_arriba = (za_col - za_cad) / (zb_col - zb_cad)
k_abajo = (za_cad - za_rod) / (zb_cad - zb_rod)


def z_a(z):
    return np.where(z >= zb_cad, za_cad + (z - zb_cad) * k_arriba, za_cad + (z - zb_cad) * k_abajo)


def seccion(co_, z, banda=0.012, sel=None):
    m = np.abs(co_[:, 2] - z) < banda
    if sel is not None:
        m &= sel
    c = co_[m]
    return c[:, 0].max() - c[:, 0].min(), c[:, 1].max() - c[:, 1].min(), c[:, 1].mean()


# anchura/fondo de la cintura: B a 6 cm por encima de su cadera (allí aún hay cuerpo), A a la altura equivalente
zb_cin = zb_cad + 0.07
torso_b = W_B["Spine"] + W_B["Hips"] + W_B["Spine1"] > 0.5
torso_a = W_A["Spine"] + W_A["Hips"] + W_A["Spine1"] > 0.5
wb, db, yb = seccion(co_b_cuerpo, zb_cin, sel=torso_b)
wa, da, ya = seccion(CO_A, float(z_a(np.array([zb_cin]))[0]), sel=torso_a)
kx, ky = wa / wb, da / db
# separación de las piernas (cabezas de UpLeg) para el muslo
kx_pierna = (hueso_a("LeftUpLeg").x - hueso_a("RightUpLeg").x) / (hueso_b("LeftUpLeg").x - hueso_b("RightUpLeg").x)
nuevo = co.copy()
nuevo[:, 2] = z_a(co[:, 2])
mezcla = np.clip((zb_cad - co[:, 2]) / 0.12, 0, 1)        # en el muslo se pasa a la escala de las piernas
kx_v = kx * (1 - mezcla) + max(kx, kx_pierna) * mezcla
nuevo[:, 0] = co[:, 0] * kx_v
nuevo[:, 1] = ya + (co[:, 1] - yb) * ky
for i, v in enumerate(me.vertices):
    v.co = Vector(nuevo[i])
r(f"  Pantalon: alturas x{k_arriba:.3f} sobre la cadera y x{k_abajo:.3f} en el muslo; ancho x{kx:.3f}"
  f" (muslo x{max(kx, kx_pierna):.3f}), fondo x{ky:.3f}; z {nuevo[:, 2].min():.3f}-{nuevo[:, 2].max():.3f} m")

# ajuste: Shrinkwrap 'fuera' (solo mueve lo que queda dentro del cuerpo) + suavizado del ajuste
pant.vertex_groups.clear()
for m in list(pant.modifiers):
    pant.modifiers.remove(m)
pant.parent = None
pant.matrix_world = Matrix()
ed = np.array([e.vertices[:] for e in me.edges])
n = len(me.vertices)
grado = np.maximum(np.bincount(ed.ravel(), minlength=n), 1).astype(float)


def shrinkwrap(offset):
    sw = pant.modifiers.new("Ajuste", "SHRINKWRAP")
    sw.target = cuerpo
    sw.wrap_method = "NEAREST_SURFACEPOINT"
    sw.wrap_mode = "OUTSIDE"
    sw.offset = offset
    for o in bpy.context.selected_objects:
        o.select_set(False)
    with bpy.context.temp_override(object=pant, active_object=pant):
        bpy.ops.object.modifier_apply(modifier=sw.name)


# el Mask del cuerpo no influye (el Shrinkwrap usa la malla evaluada): se quita mientras tanto
mk = next((m for m in cuerpo.modifiers if m.type == "MASK"), None)
if mk:
    mk.show_viewport = False
antes = np.array([v.co[:] for v in me.vertices])
shrinkwrap(HOLGURA_PANT)
despues = np.array([v.co[:] for v in me.vertices])
dsp = despues - antes
movidos = int((np.linalg.norm(dsp, axis=1) > 1e-4).sum())
for _ in range(4):
    S = np.zeros_like(dsp)
    np.add.at(S, ed[:, 0], dsp[ed[:, 1]])
    np.add.at(S, ed[:, 1], dsp[ed[:, 0]])
    dsp = np.maximum(np.abs(dsp), np.abs(S / grado[:, None])) * np.sign(dsp + S / grado[:, None])
for i, v in enumerate(me.vertices):
    v.co = Vector(antes[i] + dsp[i])
shrinkwrap(HOLGURA_PANT * 0.7)            # garantiza que nada queda dentro tras el suavizado
final = np.array([v.co[:] for v in me.vertices])
r(f"  Pantalon: Shrinkwrap fuera ({HOLGURA_PANT * 1000:.0f} mm): {movidos} de {n} vért. empujados hacia fuera,"
  f" máx. {np.linalg.norm(final - antes, axis=1).max() * 100:.1f} cm")
if mk:
    mk.show_viewport = True


def pesos(ob, iteraciones):
    for g in cuerpo.vertex_groups:
        if not g.name.startswith("ocultar"):
            ob.vertex_groups.new(name=g.name)
    dt = ob.modifiers.new("Pesos", "DATA_TRANSFER")
    dt.object = cuerpo
    dt.use_vert_data = True
    dt.data_types_verts = {"VGROUP_WEIGHTS"}
    dt.vert_mapping = "POLYINTERP_NEAREST"
    dt.layers_vgroup_select_src = "ALL"
    dt.layers_vgroup_select_dst = "NAME"
    with bpy.context.temp_override(object=ob, active_object=ob):
        bpy.ops.object.modifier_apply(modifier=dt.name)
    me_ = ob.data
    n_, g_ = len(me_.vertices), len(ob.vertex_groups)
    W = np.zeros((n_, g_))
    for v in me_.vertices:
        for e in v.groups:
            W[v.index, e.group] = e.weight
    ed_ = np.array([e.vertices[:] for e in me_.edges])
    gr = np.maximum(np.bincount(ed_.ravel(), minlength=n_), 1).astype(float)
    for _ in range(iteraciones):
        S = np.zeros_like(W)
        np.add.at(S, ed_[:, 0], W[ed_[:, 1]])
        np.add.at(S, ed_[:, 1], W[ed_[:, 0]])
        W = 0.5 * W + 0.5 * S / gr[:, None]
    W[W < 0.01] = 0
    W /= np.maximum(W.sum(axis=1, keepdims=True), 1e-9)
    for gi, vg in enumerate(ob.vertex_groups):
        vg.remove(list(range(n_)))
        for vi in np.nonzero(W[:, gi])[0]:
            vg.add([int(vi)], float(W[vi, gi]), "REPLACE")
    ob.parent = arm
    ob.matrix_parent_inverse = arm.matrix_world.inverted()
    am = ob.modifiers.new("Armature", "ARMATURE")
    am.object = arm


pesos(pant, 10)
r("  Pantalon: pesos del cuerpo (Data Transfer) suavizados x10, modificador Armature")

# el pantalón de B es de poca resolución: en las poses la piel del muslo asomaba. Como con los
# pies dentro de las botas (v2), el Mask oculta la piel que en reposo queda dentro del pantalón,
# salvo los 4 cm de encima del bajo (para que no se vea hueco).
bvh_p = BVHTree.FromPolygons([v.co.copy() for v in pant.data.vertices], [p.vertices[:] for p in pant.data.polygons])
z_bajo, z_alto = final[:, 2].min(), final[:, 2].max()
vg_o = cuerpo.vertex_groups.get("ocultar") or cuerpo.vertex_groups.new(name="ocultar")
n_oc = 0
for i, p in enumerate(CO_A):
    if not (z_bajo + 0.04 < p[2] < z_alto - 0.015):
        continue
    loc, nor, _, dist = bvh_p.find_nearest(Vector(p), 0.12)
    if loc is not None and (Vector(p) - loc).dot(nor) < 0:
        vg_o.add([i], 1.0, "REPLACE")
        n_oc += 1
if mk:
    mk.vertex_group = vg_o.name
r(f"  Cuerpo: Mask amplía 'ocultar' con {n_oc} vért. de piel dentro del pantalón (desde 4 cm sobre el bajo)")

# ---------------------------------------------------------------- 4. quitar el resto de B y guardar
for n in ("Cuerpo", "Botas"):
    o = objs[n]
    me_ = o.data
    bpy.data.objects.remove(o)
    bpy.data.meshes.remove(me_)
ad = arm_b.data
bpy.data.objects.remove(arm_b)
bpy.data.armatures.remove(ad)
for o in (pant, objs["Guante_Left"], objs["Guante_Right"]):
    for m in o.data.materials:
        if m:
            m.name = "Boxer_B"
arm.data.pose_position = "POSE"
if accion_a:
    arm.animation_data.action = accion_a
esc.frame_set(1)
r(f"  objetos: {sorted(o.name for o in bpy.data.objects)}")
bpy.ops.wm.save_as_mainfile(filepath=BLEND_C, compress=True)
r("GUARDADO", os.path.relpath(BLEND_C, C.RAIZ))
with open(os.path.join(C.TRABAJO, "c_resumen.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(resumen) + "\n")
