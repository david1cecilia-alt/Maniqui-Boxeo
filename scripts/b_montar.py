"""Variante B – modelo nuevo (Creazilla "Boxer", rig de Mixamo) reforzado.

1. Carga modelos/boxeador_b_rig.fbx (metros, escala 1, sin la animación Idle).
2. Copia las 15 acciones de trabajo/boxeador.blend (mismos nombres de huesos). La
   traslación (location) se escala por la altura de la cadera B/A (y las unidades).
3. Separa la malla en objetos como en la v2 (Cuerpo, Pantalon, Botas, Guante_Left/Right)
   para poder pasarle los mismos scripts; la geometría y los pesos no cambian. El guante
   va soldado al brazo: se corta bajo el puño de velcro (que tapa el corte).
4. Refuerzo: shape key 'reforzado' (valor 1) que empuja la piel hacia fuera desde el eje
   de cada hueso (escalado radial proporcional, mezclado con los pesos de los huesos):
   hombros/deltoides, brazo y antebrazo hasta la muñeca. Guantes, puños y pantalón no se
   tocan (son otros objetos). Grupo 'engordar' = cuánto se ha engordado (para verlo).
   En el codo el refuerzo baja casi a 0 y los pesos Arm/ForeArm se suavizan: el refuerzo
   radial y el salto brusco de pesos hacían un pico en el pliegue al flexionar.
5. Guantes un 12 % más cortos (solo la manopla, desde el final del puño de velcro).
6. Textura sin el logo de la marca en los puños (copia: modelos/Boxer_texture_sin_logo.png).
7. Pies: la rotación de Foot/ToeBase se rehace para que giren respecto a su reposo igual que
   en la v2 (con la copia directa quedaban ~14° girados, porque el reposo de los pies de B es
   distinto), y la cadera se sube/baja en cada fotograma para que la suela apoye en Z=0.
Modelo principal: guarda trabajo/boxeador.blend y trabajo/b_resumen.txt (acciones de
trabajo/boxeador_v2.blend).

Uso:
  blender.exe --background --python scripts/b_montar.py
"""
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun as C  # noqa: E402
import modelo_b as MB  # noqa: E402

BLEND_A = os.path.join(C.TRABAJO, "boxeador_v2.blend")
BLEND_B = os.path.join(C.TRABAJO, "boxeador.blend")
P = "mixamorig:"
# refuerzo radial (fracción de la distancia al eje del hueso) a lo largo del hueso: [(t, s)]
REFUERZO = {
    "Shoulder": [(0.0, 0.00), (0.5, 0.06), (1.0, 0.12)],                              # trapecio -> hombro
    "Arm": [(0.0, 0.16), (0.30, 0.15), (0.60, 0.12), (0.82, 0.07), (1.0, 0.02)],      # deltoides -> codo
    "ForeArm": [(0.0, 0.02), (0.18, 0.07), (0.45, 0.13), (0.80, 0.09), (1.0, 0.06)],  # codo -> muñeca
}
RAMPA_PUNO = (0.07, 0.015)   # el refuerzo baja a 0 entre 7 y 1,5 cm antes del puño de velcro
CODO_RADIO, CODO_ITER = 0.08, 12   # suavizado de pesos Arm/ForeArm alrededor del codo
K_GUANTE = 0.88                    # largo de la manopla del guante (desde el puño de velcro)
PIES = ["LeftFoot", "LeftToeBase", "RightFoot", "RightToeBase"]

resumen = []


def r(*a):
    linea = " ".join(str(x) for x in a)
    resumen.append(linea)
    print(linea)


# ---------------------------------------------------------------- 1. acciones de A
bpy.ops.wm.open_mainfile(filepath=BLEND_A)
arm_a = bpy.data.objects["Boxeador"]
esc_a = arm_a.matrix_world.to_scale()[0]
cad_a = (arm_a.matrix_world @ arm_a.data.bones[P + "Hips"].head_local).z / esc_a   # en unidades de A
nombres_acc = sorted(a.name for a in bpy.data.actions if not a.name.endswith("_v2"))


def q_mundo(m):
    return m.to_3x3().normalized().to_quaternion()


# giro de cada pie respecto a su reposo, en el mundo, en cada fotograma de cada acción de la v2
GIRO_PIES = {}
for nombre in nombres_acc:
    a = bpy.data.actions[nombre]
    arm_a.animation_data.action = a
    if arm_a.animation_data.action_slot is None:
        arm_a.animation_data.action_slot = a.slots[0]
    f0, f1 = (int(x) for x in a.frame_range)
    GIRO_PIES[nombre] = {}
    for f in range(f0, f1 + 1):
        bpy.context.scene.frame_set(f)
        GIRO_PIES[nombre][f] = {b: q_mundo(arm_a.matrix_world @ arm_a.pose.bones[P + b].matrix)
                                @ q_mundo(arm_a.matrix_world @ arm_a.data.bones[P + b].matrix_local).inverted()
                                for b in PIES}

C.escena_vacia()
arm, ob = MB.cargar_b("Boxeador", "Cuerpo")
n_logo = MB.textura_sin_logo(ob)
with bpy.data.libraries.load(BLEND_A, link=False) as (src, dst):
    dst.actions = list(nombres_acc)
cad_b = (arm.matrix_world @ arm.data.bones[P + "Hips"].head_local).z / arm.matrix_world.to_scale()[0]
k_loc = cad_b / cad_a
arm.animation_data_create()
for a in bpy.data.actions:
    a.use_fake_user = True
    for fc in a.fcurves:
        if fc.data_path.endswith(".location"):
            for kp in fc.keyframe_points:
                kp.co.y *= k_loc
                kp.handle_left.y *= k_loc
                kp.handle_right.y *= k_loc
r("=== VARIANTE B ===")
r(f"  acciones copiadas de boxeador.blend: {len(bpy.data.actions)} ({', '.join(sorted(a.name for a in bpy.data.actions))})")
r(f"  traslación escalada x{k_loc:.5f} (cadera B {cad_b:.3f} m / cadera A {cad_a:.1f} unidades de A)")

# ---------------------------------------------------------------- 2. separar en objetos
objs, sep = MB.separar_piezas(arm, ob)
corte = sep["corte"]
codigos = MB.CODIGOS
ob = objs["Cuerpo"]
me = ob.data
for n in codigos:
    o = bpy.data.objects[n]
    r(f"  {n:13}: {len(o.data.vertices):6} vért., {len(o.data.polygons):6} caras")
r(f"  islas: pantalón {sep['pantalon']}, botas {len(sep['botas'])} piezas (zapatilla + cordones),"
  f" puños de velcro {sep['puno']}; la manopla del guante iba soldada al brazo (isla {sep['principal']}):"
  " cortada a mitad del puño")


def eje_hueso(nombre):
    b = arm.data.bones[P + nombre]
    return Vector(b.head_local), Vector(b.tail_local)


r(f"  textura: logo de la marca tapado con una etiqueta lisa en {n_logo} píxeles (copia de la textura)")

# guantes más cortos: la manopla se acorta hacia el puño de velcro (el puño no se mueve)
for lado in ("Left", "Right"):
    g = objs["Guante_" + lado]
    h0, d, t_ini, t_mitad = corte[lado]
    t_fin = 2 * t_mitad - t_ini
    cg = np.array([v.co[:] for v in g.data.vertices])
    t = (cg - np.array(h0)) @ np.array(d)
    largo0 = t.max() - t_ini
    mas = np.maximum(t - t_fin, 0)
    cg -= np.outer(mas * (1 - K_GUANTE), np.array(d))
    g.data.vertices.foreach_set("co", cg.ravel())
    t2 = (cg - np.array(h0)) @ np.array(d)
    r(f"  Guante_{lado}: manopla x{K_GUANTE} -> largo {largo0 * 100:.1f} -> {(t2.max() - t_ini) * 100:.1f} cm (con el puño)")

# ---------------------------------------------------------------- 3. refuerzo (shape key)
co = np.array([v.co[:] for v in me.vertices])
n = len(co)
gidx = {g.name.split(":")[-1]: g.index for g in ob.vertex_groups}
W = np.zeros((n, len(ob.vertex_groups)))
for v in me.vertices:
    for e in v.groups:
        W[v.index, e.group] = e.weight

# codo: pesos Arm/ForeArm suavizados (manteniendo su suma) cerca de la articulación
ed = np.array([e.vertices[:] for e in me.edges])
grado = np.maximum(np.bincount(ed.ravel(), minlength=n), 1).astype(float)
for lado in ("Left", "Right"):
    ga, gf = gidx[lado + "Arm"], gidx[lado + "ForeArm"]
    codo = np.array(eje_hueso(lado + "ForeArm")[0])
    suma = W[:, ga] + W[:, gf]
    zona = (np.linalg.norm(co - codo, axis=1) < CODO_RADIO) & (suma > 0.05)
    antes_w = W[zona][:, [ga, gf]].copy()
    for _ in range(CODO_ITER):
        for g in (ga, gf):
            S = np.zeros(n)
            np.add.at(S, ed[:, 0], W[ed[:, 1], g])
            np.add.at(S, ed[:, 1], W[ed[:, 0], g])
            W[zona, g] = 0.5 * W[zona, g] + 0.5 * S[zona] / grado[zona]
        tot = W[zona, ga] + W[zona, gf]
        W[zona, ga] *= suma[zona] / np.maximum(tot, 1e-9)
        W[zona, gf] *= suma[zona] / np.maximum(tot, 1e-9)
    for g in (ga, gf):
        vgp = ob.vertex_groups[g]
        for i in np.where(zona)[0]:
            if W[i, g] > 1e-4:
                vgp.add([int(i)], float(W[i, g]), "REPLACE")
            else:
                vgp.remove([int(i)])
    cambio = np.abs(W[zona][:, [ga, gf]] - antes_w).max()
    r(f"  codo {lado}: pesos Arm/ForeArm suavizados en {int(zona.sum())} vért. (radio {CODO_RADIO * 100:.0f} cm),"
      f" cambio máx. {cambio:.2f}")


def interp(t, tabla):
    ts, ss = zip(*tabla)
    return np.interp(t, ts, ss)


desp = np.zeros((n, 3))
for lado in ("Left", "Right"):
    h0c, dc, t_puno, _ = corte[lado]
    t_muneca = (co - np.array(h0c)) @ np.array(dc)
    lim = np.clip((t_puno - RAMPA_PUNO[1] - t_muneca) / (RAMPA_PUNO[0] - RAMPA_PUNO[1]), 0, 1)   # 0 cerca del puño
    lim = lim * lim * (3 - 2 * lim)
    for parte, tabla in REFUERZO.items():
        nombre = lado + parte
        if nombre not in gidx:
            continue
        h0, h1 = (np.array(x) for x in eje_hueso(nombre))
        L = h1 - h0
        t = np.clip(((co - h0) @ L) / (L @ L), 0, 1)
        radial = co - (h0 + t[:, None] * L)
        s = interp(t, tabla)
        w = W[:, gidx[nombre]]
        if parte == "ForeArm":
            s = s * lim
        desp += (w * s)[:, None] * radial
# suavizado del desplazamiento (evita escalones entre huesos)
for _ in range(6):
    S = np.zeros_like(desp)
    np.add.at(S, ed[:, 0], desp[ed[:, 1]])
    np.add.at(S, ed[:, 1], desp[ed[:, 0]])
    desp = 0.5 * desp + 0.5 * S / grado[:, None]
# en los bordes abiertos de la muñeca (bajo el puño) no se mueve nada
borde = np.zeros(n, bool)
bm = bmesh.new()
bm.from_mesh(me)
for v in bm.verts:
    if v.is_boundary and any((Vector(v.co) - corte[l][0]).dot(corte[l][1]) > corte[l][2] - 0.03 for l in corte):
        borde[v.index] = True
bm.free()
desp[borde] = 0
ob.shape_key_add(name="Basis", from_mix=False)
sk = ob.shape_key_add(name="reforzado", from_mix=False)
nuevo = co + desp
sk.data.foreach_set("co", nuevo.ravel())
sk.value = 1.0
mag = np.linalg.norm(desp, axis=1)
vg = ob.vertex_groups.new(name="engordar")
for i in np.nonzero(mag > 1e-4)[0]:
    vg.add([int(i)], float(min(1.0, mag[i] / mag.max())), "REPLACE")
for lado in ("Left", "Right"):
    for parte in REFUERZO:
        g = gidx.get(lado + parte)
        sel = W[:, g] > 0.5
        r(f"  refuerzo {lado + parte:14}: {sel.sum():5} vért. (peso > 0,5), desplazamiento medio {mag[sel].mean() * 1000:.1f} mm,"
          f" máx. {mag[sel].max() * 1000:.1f} mm")
r(f"  refuerzo total: {int((mag > 1e-4).sum())} vért. movidos, máx. {mag.max() * 1000:.1f} mm; guantes/puños/pantalón: 0 (otros objetos)")


def perimetro(nombre, t, co_):
    h0, h1 = (np.array(x) for x in eje_hueso(nombre))
    L = h1 - h0
    p0 = h0 + t * L
    dl = (co_ - p0) @ (L / np.linalg.norm(L))
    sel = (np.abs(dl) < 0.006) & (W[:, gidx[nombre]] > 0.3)
    rad = np.linalg.norm((co_[sel] - p0) - dl[sel, None] * (L / np.linalg.norm(L)), axis=1)
    return 2 * np.pi * rad.mean() * 100 if sel.any() else 0.0


for nombre, t in (("LeftArm", 0.15), ("LeftArm", 0.5), ("LeftForeArm", 0.4), ("LeftForeArm", 0.8)):
    r(f"  contorno aprox. {nombre} al {t * 100:.0f} %: {perimetro(nombre, t, co):.1f} -> {perimetro(nombre, t, nuevo):.1f} cm")

# ---------------------------------------------------------------- 4. dejar listo y guardar
for nombre in codigos:
    o = bpy.data.objects[nombre]
    if not any(m.type == "ARMATURE" for m in o.modifiers):
        am = o.modifiers.new("Armature", "ARMATURE")
        am.object = arm
esc = bpy.context.scene
esc.render.fps = 30


def poner(nombre):
    a = bpy.data.actions[nombre]
    arm.animation_data.action = a
    if arm.animation_data.action_slot is None or arm.animation_data.action_slot.identifier not in [s.identifier for s in a.slots]:
        arm.animation_data.action_slot = a.slots[0]
    return a


def clave_rot(pb, f, previo):
    """Inserta la rotación del hueso en f (cuaternión con el signo continuo respecto a 'previo')."""
    if pb.rotation_mode == "QUATERNION":
        q = pb.rotation_quaternion.copy()
        if previo is not None and q.dot(previo) < 0:
            q.negate()
            pb.rotation_quaternion = q
        pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)
        return q
    pb.keyframe_insert("rotation_euler", frame=f, group=pb.name)
    return None


# pies: mismo giro respecto al reposo que en la v2
rest_pie = {b: arm.data.bones[P + b].matrix_local.to_quaternion() for b in PIES}
dif_max = 0.0
for nombre in nombres_acc:
    a = poner(nombre)
    f0, f1 = (int(x) for x in a.frame_range)
    previo = {b: None for b in PIES}
    for f in range(f0, f1 + 1):
        esc.frame_set(f)
        for b in PIES:
            pb = arm.pose.bones[P + b]
            q = GIRO_PIES[nombre][f][b] @ rest_pie[b]
            ang = np.degrees(pb.matrix.to_quaternion().rotation_difference(q).angle)
            dif_max = max(dif_max, min(ang, 360 - ang))
            pb.matrix = Matrix.LocRotScale(pb.matrix.translation, q, None)
            bpy.context.view_layer.update()
            previo[b] = clave_rot(pb, f, previo[b])
r(f"  pies: Foot/ToeBase rehechos en las {len(nombres_acc)} acciones (corrección máx. {dif_max:.1f}°)")


# suelo: la suela más baja (zapatillas) en Z=0 en cada fotograma
def z_suela():
    dg = bpy.context.evaluated_depsgraph_get()
    oe = bpy.data.objects["Botas"].evaluated_get(dg)
    m = oe.to_mesh()
    z = np.empty(len(m.vertices) * 3)
    m.vertices.foreach_get("co", z)
    oe.to_mesh_clear()
    return float(z.reshape(-1, 3)[:, 2].min())


hips = arm.pose.bones[P + "Hips"]
R_hips = arm.data.bones[P + "Hips"].matrix_local.to_3x3().inverted()
ruta_loc = f'pose.bones["{P}Hips"].location'
peor = {}
for nombre in nombres_acc:
    a = poner(nombre)
    f0, f1 = (int(x) for x in a.frame_range)
    dz = {}
    for f in range(f0, f1 + 1):
        esc.frame_set(f)
        dz[f] = -z_suela()
    fcs = [next(fc for fc in a.fcurves if fc.data_path == ruta_loc and fc.array_index == i) for i in range(3)]
    base = {f: Vector([fc.evaluate(f) for fc in fcs]) for f in dz}
    for f in dz:
        hips.location = base[f] + R_hips @ Vector((0, 0, dz[f]))
        hips.keyframe_insert("location", frame=f, group=hips.name)
    peor[nombre] = (min(dz.values()), max(dz.values()))
r("  suelo: cadera corregida para apoyar en Z=0 (corrección en cm, mín./máx. por acción): "
  + ", ".join(f"{k} {v[0] * 100:+.1f}/{v[1] * 100:+.1f}" for k, v in sorted(peor.items())))
poner("guardia")
esc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=BLEND_B, compress=True)
r("GUARDADO", os.path.relpath(BLEND_B, C.RAIZ))
with open(os.path.join(C.TRABAJO, "b_resumen.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(resumen) + "\n")
