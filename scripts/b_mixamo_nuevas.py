"""Animaciones nuevas de Mixamo directamente al modelo B y renombres de acciones.

Ejecutar después de b_montar.py y b_brazo.py y antes de fase4_b.py (que les hace la _v2).
1. Renombres (si no están hechos):
   - paso_atras (hecho a mano en la Fase 2) -> paso_atras_mano.
   - gancho_adelantado_cuerpo (Mixamo) -> gancho_adelantado_mixamo: de su _v2 salen el gancho
     adelantado a la cara (5, tal cual) y el gancho adelantado al cuerpo (11, nuevo) en fase5_b.py.
   - esquiva_avanzando / esquiva_retrocediendo (Mixamo) -> futuro_esquiva_*: la cadera se rompe con
     el pantalón; quedan para más adelante y fuera de las acciones de la app.
2. FBX nuevos (comun.FBX_B): pivote (ida y vuelta), pivote_der, pivote_izq y paso_atras. Como con
   los demás: se copian las curvas de los huesos que tiene B (mismos nombres de Mixamo), la
   traslación se escala por la altura de la cadera, los pies se rehacen para que giren respecto a su
   reposo igual que en el FBX (el reposo de los pies de B es distinto) y la cadera se sube/baja en
   cada fotograma para que la suela más baja apoye en Z=0.
Guarda trabajo/taller/boxeador_taller.blend y trabajo/b_mixamo_nuevas.txt.

Uso:
  blender.exe --background --python scripts/b_mixamo_nuevas.py
"""
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun as C  # noqa: E402

BLEND = C.BLEND_TALLER
P = "mixamorig:"
PIES = ["LeftFoot", "LeftToeBase", "RightFoot", "RightToeBase"]
RENOMBRES = [("paso_atras", "paso_atras_mano"), ("gancho_adelantado_cuerpo", "gancho_adelantado_mixamo"),
             ("esquiva_avanzando", "futuro_esquiva_avanzando"),
             ("esquiva_retrocediendo", "futuro_esquiva_retrocediendo")]
out = []


def p(*a):
    out.append(" ".join(str(x) for x in a))
    print(out[-1])


def qm(m):
    return m.to_3x3().normalized().to_quaternion()


bpy.ops.wm.open_mainfile(filepath=BLEND)
esc = bpy.context.scene
arm = bpy.data.objects["Boxeador"]
assert arm.matrix_world == Matrix()
acc = bpy.data.actions
p("=== ANIMACIONES NUEVAS DE MIXAMO Y RENOMBRES (modelo B) ===")

# ---------------------------------------------------------------- 1. renombres
for viejo, nuevo in RENOMBRES:
    if viejo in acc and nuevo not in acc and not acc[viejo].get("mixamo_b"):
        for v in [a for a in acc if a.name == viejo + "_v2"]:
            acc.remove(v)            # fase4_b.py rehace la _v2 con el nombre nuevo
        acc[viejo].name = nuevo
        p(f"  {viejo} -> {nuevo}")
    elif nuevo in acc:
        p(f"  {nuevo}: ya renombrada")

# ---------------------------------------------------------------- 2. FBX nuevos
cad_b = arm.data.bones[P + "Hips"].head_local.z
huesos_b = {b.name for b in arm.data.bones}
rest_pie_b = {b: arm.data.bones[P + b].matrix_local.to_quaternion() for b in PIES}
botas = bpy.data.objects["Botas"]


def z_suela():
    dg = bpy.context.evaluated_depsgraph_get()
    oe = botas.evaluated_get(dg)
    m = oe.to_mesh()
    z = np.empty(len(m.vertices) * 3)
    m.vertices.foreach_get("co", z)
    oe.to_mesh_clear()
    return float(z.reshape(-1, 3)[:, 2].min())


def poner(a):
    arm.animation_data.action = a
    if arm.animation_data.action_slot is None or arm.animation_data.action_slot.identifier not in [s.identifier for s in a.slots]:
        arm.animation_data.action_slot = a.slots[0]


def clave_rot(pb, f, previo):
    q = pb.rotation_quaternion.copy()
    if previo is not None and q.dot(previo) < 0:
        q.negate()
        pb.rotation_quaternion = q
    pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)
    return q


for nombre, ruta in C.FBX_B.items():
    if nombre in acc:
        acc.remove(acc[nombre])
    for v in [a for a in acc if a.name == nombre + "_v2"]:
        acc.remove(v)
    antes_o, antes_a = set(bpy.data.objects), set(acc)
    bpy.ops.import_scene.fbx(filepath=ruta)
    nuevos = [o for o in bpy.data.objects if o not in antes_o]
    arm_f = next(o for o in nuevos if o.type == "ARMATURE")
    a = next(x for x in acc if x not in antes_a and arm_f.animation_data and x == arm_f.animation_data.action)
    esc_f = arm_f.matrix_world.to_scale()[0]
    cad_f = (arm_f.matrix_world @ arm_f.data.bones[P + "Hips"].head_local).z / esc_f
    k = cad_b / cad_f
    f0, f1 = (int(x) for x in a.frame_range)
    # giro de cada pie respecto a su reposo (en el mundo) en el FBX, fotograma a fotograma
    giro = {}
    for f in range(f0, f1 + 1):
        esc.frame_set(f)
        giro[f] = {b: qm(arm_f.matrix_world @ arm_f.pose.bones[P + b].matrix)
                   @ qm(arm_f.matrix_world @ arm_f.data.bones[P + b].matrix_local).inverted() for b in PIES}
    # curvas: solo los huesos de B; traslación escalada
    quitadas = 0
    for fc in list(a.fcurves):
        hueso = fc.data_path.split('"')[1] if '"' in fc.data_path else ""
        if hueso not in huesos_b:
            a.fcurves.remove(fc)
            quitadas += 1
            continue
        if fc.data_path.endswith(".location"):
            for kp in fc.keyframe_points:
                kp.co.y *= k
                kp.handle_left.y *= k
                kp.handle_right.y *= k
    for o in nuevos:
        bpy.data.objects.remove(o, do_unlink=True)
    for x in set(acc) - antes_a - {a}:
        acc.remove(x)
    a.name = nombre
    a.use_fake_user = True
    a["mixamo_b"] = True
    poner(a)
    # pies como en el FBX y suela en Z=0
    previo = {b: None for b in PIES}
    hips = arm.pose.bones[P + "Hips"]
    R_hips = arm.data.bones[P + "Hips"].matrix_local.to_3x3().inverted()
    ruta_loc = f'pose.bones["{P}Hips"].location'
    fcs = [next(fc for fc in a.fcurves if fc.data_path == ruta_loc and fc.array_index == i) for i in range(3)]
    dzs = []
    for f in range(f0, f1 + 1):
        esc.frame_set(f)
        for b in PIES:
            pb = arm.pose.bones[P + b]
            pb.matrix = Matrix.LocRotScale(pb.matrix.translation, giro[f][b] @ rest_pie_b[b], None)
            bpy.context.view_layer.update()
            previo[b] = clave_rot(pb, f, previo[b])
        dz = -z_suela()
        base = Vector([fc.evaluate(f) for fc in fcs])
        hips.location = base + R_hips @ Vector((0, 0, dz))
        hips.keyframe_insert("location", frame=f, group=hips.name)
        dzs.append(dz)
    esc.frame_set(f0)
    h0 = hips.head.copy()
    esc.frame_set(f1)
    d = hips.head - h0
    p(f"  {nombre:11} <- {os.path.relpath(ruta, C.RAIZ)}: fot. {f0}-{f1} ({(f1 - f0) / 30:.1f} s), traslación x{k:.4f},"
      f" {quitadas} curvas de huesos que B no tiene (dedos) quitadas, suelo corregido {min(dzs) * 100:+.1f}/"
      f"{max(dzs) * 100:+.1f} cm | cadera del primer al último fot.: {d.x * 100:+.0f}, {d.y * 100:+.0f} cm")

poner(acc["guardia"])
esc.frame_set(1)
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
p(f"  GUARDADO {os.path.relpath(BLEND, C.RAIZ)}")
with open(os.path.join(C.TRABAJO, "b_mixamo_nuevas.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out) + "\n")
