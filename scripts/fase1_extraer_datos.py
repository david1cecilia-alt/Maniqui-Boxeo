"""Fase 1 – extrae datos de cada FBX y los guarda en trabajo/diagnostico.json.

Uso:
  blender.exe --background --python scripts/fase1_extraer_datos.py
"""
import json
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun as C  # noqa: E402

CLAVE = ["Hips", "Spine2", "Neck", "Head", "HeadTop_End",
         "LeftShoulder", "RightShoulder", "LeftArm", "RightArm",
         "LeftForeArm", "RightForeArm", "LeftHand", "RightHand",
         "LeftUpLeg", "RightUpLeg", "LeftLeg", "RightLeg",
         "LeftFoot", "RightFoot", "LeftToeBase", "RightToeBase"]

os.makedirs(C.TRABAJO, exist_ok=True)
salida = {}

for nombre, ruta in C.FBX.items():
    d = {"archivo": os.path.relpath(ruta, C.RAIZ), "bytes": os.path.getsize(ruta)}
    arm, mallas = C.importar(nombre)
    esc = bpy.context.scene
    d["fps"] = esc.render.fps / esc.render.fps_base
    d["arm_nombre"] = arm.name if arm else None
    d["huesos"] = [b.name for b in arm.data.bones] if arm else []
    d["jerarquia"] = {b.name: (b.parent.name if b.parent else None) for b in arm.data.bones} if arm else {}
    d["mallas"] = []
    for m in mallas:
        d["mallas"].append({
            "nombre": m.name,
            "vertices": len(m.data.vertices),
            "caras": len(m.data.polygons),
            "materiales": [s.material.name if s.material else None for s in m.material_slots],
            "grupos_vertices": [g.name for g in m.vertex_groups],
            "padre": m.parent.name if m.parent else None,
        })
    d["acciones"] = []
    for a in bpy.data.actions:
        d["acciones"].append({"nombre": a.name,
                              "rango": [a.frame_range[0], a.frame_range[1]],
                              "curvas": len(a.fcurves)})
    act = arm.animation_data.action if (arm and arm.animation_data) else None
    if act:
        f0, f1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))
        d["accion"] = act.name
        d["frame_ini"], d["frame_fin"] = f0, f1
        d["n_fotogramas"] = f1 - f0 + 1
        d["duracion_s"] = round((f1 - f0) / d["fps"], 3)
        pistas = {k: [] for k in CLAVE}
        rot_local = {b.name: [] for b in arm.pose.bones}
        loc_local = {b.name: [] for b in arm.pose.bones}
        for f in range(f0, f1 + 1):
            esc.frame_set(f)
            for k in CLAVE:
                p = C.pos_mundo(arm, k)
                pistas[k].append([round(x, 5) for x in p] if p is not None else None)
            for pb in arm.pose.bones:
                q = pb.rotation_quaternion if pb.rotation_mode == "QUATERNION" else pb.rotation_euler.to_quaternion()
                rot_local[pb.name].append([round(x, 5) for x in q])
                loc_local[pb.name].append([round(x, 5) for x in pb.location])
        d["pistas"] = pistas
        d["rot_local"] = rot_local
        d["loc_local"] = loc_local
    # longitudes de huesos en reposo para comparar esqueletos
    if arm:
        d["reposo"] = {b.name: [round(x, 4) for x in (arm.matrix_world @ b.head_local)] for b in arm.data.bones}
    salida[nombre] = d
    print(f"[OK] {nombre}: {d.get('accion')} {d.get('n_fotogramas')} fot.")

with open(os.path.join(C.TRABAJO, "diagnostico.json"), "w", encoding="utf-8") as fh:
    json.dump(salida, fh)
print("GUARDADO", os.path.join(C.TRABAJO, "diagnostico.json"))
