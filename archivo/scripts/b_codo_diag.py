"""Diagnóstico del pico en el pliegue del codo de B (no guarda nada).

En el fotograma de máxima flexión de codo de guardia, jab y crochet_adelantado mide el
estiramiento de las aristas del brazo (largo en pose / largo en reposo) con la shape key
'reforzado' a 1 y a 0, y lista los pesos de los vértices peor parados.
Uso: blender.exe --background --python scripts/b_codo_diag.py -- [blend]
"""
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun as C  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
BLEND = os.path.join(C.TRABAJO, ARGS[0] if ARGS else "boxeador.blend")
P = "mixamorig:"
bpy.ops.wm.open_mainfile(filepath=BLEND)
esc = bpy.context.scene
arm = bpy.data.objects["Boxeador"]
objs = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(("Cuerpo", "Guante"))]
out = []


def p(*a):
    out.append(" ".join(str(x) for x in a))
    print(out[-1])


def flexion(lado):
    a = arm.pose.bones[P + lado + "Arm"]
    f = arm.pose.bones[P + lado + "ForeArm"]
    da = (a.tail - a.head).normalized()
    df = (f.tail - f.head).normalized()
    return np.degrees(da.angle(df))


def coords(o):
    dg = bpy.context.evaluated_depsgraph_get()
    oe = o.evaluated_get(dg)
    me = oe.to_mesh()
    co = np.array([v.co[:] for v in me.vertices])
    oe.to_mesh_clear()
    return co


for o in objs:
    nom = {g.index: g.name.split(":")[-1] for g in o.vertex_groups}
    raros = 0
    for v in o.data.vertices:
        gs = {nom[e.group]: e.weight for e in v.groups if e.weight > 0.02 and not nom[e.group].startswith("engordar")}
        if not gs:
            continue
        lados = {n[:4] for n in gs if n.startswith(("Left", "Righ"))}
        if len(lados) > 1:
            raros += 1
    p(f"{o.name}: vértices con pesos de los dos lados: {raros}; suma de pesos != 1:",
      sum(1 for v in o.data.vertices if v.groups and abs(sum(e.weight for e in v.groups
          if not nom[e.group].startswith('engordar')) - 1) > 0.02))

ACCIONES = ARGS[1:] or ["guardia", "jab", "crochet_adelantado", "guardia_v2", "jab_v2", "crochet_adelantado_v2"]
MAX_FLEX = {}
for accion in [x for x in ACCIONES if x in bpy.data.actions]:
    a = bpy.data.actions[accion]
    arm.animation_data.action = a
    if arm.animation_data.action_slot is None:
        arm.animation_data.action_slot = a.slots[0]
    f0, f1 = (int(x) for x in a.frame_range)
    mejor = (0, None, None)
    for f in range(f0, f1 + 1):
        esc.frame_set(f)
        for lado in ("Left", "Right"):
            fl = flexion(lado)
            if fl > mejor[0]:
                mejor = (fl, f, lado)
    fl, f, lado = mejor
    MAX_FLEX[accion] = (f, lado)
    esc.frame_set(f)
    p(f"\n== {accion}: máxima flexión {fl:.0f}° en fot. {f} ({lado})")
    for o in objs:
        me = o.data
        ed = np.array([e.vertices[:] for e in me.edges])
        rest = np.array([v.co[:] for v in me.vertices])
        L0 = np.linalg.norm(rest[ed[:, 0]] - rest[ed[:, 1]], axis=1) + 1e-9
        nom = {g.index: g.name.split(":")[-1] for g in o.vertex_groups}
        zona = np.array([any(nom[e.group] in (lado + "Arm", lado + "ForeArm") and e.weight > 0.1 for e in v.groups)
                         for v in me.vertices])
        sk = o.data.shape_keys.key_blocks.get("reforzado") if o.data.shape_keys else None
        for val in ((1.0, 0.0) if sk else (None,)):
            if sk:
                sk.value = val
            co = coords(o)
            L = np.linalg.norm(co[ed[:, 0]] - co[ed[:, 1]], axis=1)
            r = L / L0
            m = zona[ed[:, 0]] | zona[ed[:, 1]]
            if not m.any():
                continue
            idx = np.where(m)[0][np.argsort(-r[m])][:3]
            p(f"  {o.name:13} shape key={val}: estiramiento máx. {r[m].max():.2f}, aristas > 1.6: {(r[m] > 1.6).sum()}")
            for i in idx[:2]:
                vi = ed[i, 0]
                gs = sorted(((round(e.weight, 2), nom[e.group]) for e in me.vertices[vi].groups), reverse=True)[:4]
                p(f"      arista {ed[i].tolist()} x{r[i]:.2f}  pesos v{vi}: {gs}")
        if sk:
            sk.value = 1.0
with open(os.path.join(C.TRABAJO, "b_codo_diag.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out) + "\n")
# para los renders de cerca del codo (fase4_render.py)
with open(os.path.join(C.TRABAJO, "b_codo_max_flexion.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(f"{a} {f} {l}" for a, (f, l) in MAX_FLEX.items()) + "\n")
