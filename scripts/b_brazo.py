"""Brazo más proporcionado en el modelo principal (B): alarga el brazo (hombro -> codo).

En el modelo de Creazilla el hueso Arm (hombro a codo) medía 0,205 m: 0,85 veces el antebrazo y
el 12 % de la altura (en una persona suele ser 1,1-1,25 veces el antebrazo). Se alarga FACTOR:
- Esqueleto (reposo): la cola de LeftArm/RightArm se aleja del hombro y el antebrazo y la mano se
  desplazan lo mismo.
- Mallas (Cuerpo con sus shape keys, guantes): cada vértice se mueve
  delta * (peso del antebrazo y la mano + peso del brazo * s), con s = posición a lo largo del
  hueso del brazo (0 en el hombro, 1 en el codo). El brazo se estira y el antebrazo, la mano y
  el guante se trasladan sin deformarse.
Las acciones guardan rotaciones locales, así que siguen valiendo; después hay que volver a
ejecutar fase4_b.py y fase5_b.py (los IK se calculan con las longitudes nuevas).
No se aplica dos veces: guarda la propiedad `brazo_factor` en el esqueleto.

Uso:
  blender.exe --background --python scripts/b_brazo.py
"""
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun as C  # noqa: E402

BLEND = C.BLEND_TALLER
P = "mixamorig:"
FACTOR = 1.30

bpy.ops.wm.open_mainfile(filepath=BLEND)
arm = bpy.data.objects["Boxeador"]
assert arm.matrix_world == Matrix()
if arm.data.get("brazo_factor"):
    print(f"YA APLICADO (brazo_factor = {arm.data['brazo_factor']}): no se hace nada")
    sys.exit(0)

B = arm.data.bones
lineas = []
datos = {}
for lado in ("Left", "Right"):
    h = B[P + lado + "Arm"].head_local.copy()
    t = B[P + lado + "ForeArm"].head_local.copy()
    w = B[P + lado + "Hand"].head_local.copy()
    eje = t - h
    datos[lado] = (h, eje.normalized(), eje.length, eje * (FACTOR - 1))
    lineas.append(f"  {lado}: brazo {eje.length:.3f} -> {eje.length * FACTOR:.3f} m (antebrazo {(w - t).length:.3f};"
                  f" brazo/antebrazo {eje.length / (w - t).length:.2f} -> {eje.length * FACTOR / (w - t).length:.2f})")

# ---------------------------------------------------------------- mallas (antes de tocar el esqueleto)
mallas = [o for o in bpy.data.objects if o.type == "MESH"
          and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers)]
for o in mallas:
    assert o.matrix_world == Matrix(), o.name
    me = o.data
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    nom = {g.index: g.name.split(":")[-1] for g in o.vertex_groups}
    desp = np.zeros((n, 3))
    for v in me.vertices:
        tot = sum(e.weight for e in v.groups) or 1.0
        for lado, (h, u, lon, delta) in datos.items():
            w_arm = w_rest = 0.0
            for e in v.groups:
                g = nom[e.group]
                if g == lado + "Arm":
                    w_arm += e.weight
                elif g in (lado + "ForeArm", lado + "Hand") or g.startswith(lado + "Hand"):
                    w_rest += e.weight
            if w_arm == 0 and w_rest == 0:
                continue
            s = min(max((co[v.index] - np.array(h)).dot(np.array(u)) / lon, 0.0), 1.0)
            desp[v.index] += np.array(delta) * (w_rest + w_arm * s) / tot
    movidos = int((np.linalg.norm(desp, axis=1) > 1e-6).sum())
    if me.shape_keys:
        for kb in me.shape_keys.key_blocks:
            k = np.empty(n * 3)
            kb.data.foreach_get("co", k)
            kb.data.foreach_set("co", (k.reshape(-1, 3) + desp).ravel())
    me.vertices.foreach_set("co", (co + desp).ravel())
    me.update()
    lineas.append(f"  {o.name}: {movidos} vértices movidos (máx. {np.linalg.norm(desp, axis=1).max() * 100:.1f} cm)")

# ---------------------------------------------------------------- esqueleto (reposo)
bpy.context.view_layer.objects.active = arm
for o in bpy.context.selected_objects:
    o.select_set(False)
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
for lado, (h, u, lon, delta) in datos.items():
    hijos = [b for b in eb if b.parent and (b.parent.name == P + lado + "Arm" or
                                             any(a.name == P + lado + "Arm" for a in b.parent_recursive))]
    viejo = {b.name: (b.head.copy(), b.tail.copy()) for b in hijos}
    eb[P + lado + "Arm"].tail = eb[P + lado + "Arm"].tail + delta
    for b in hijos:
        b.head, b.tail = viejo[b.name][0] + delta, viejo[b.name][1] + delta
    lineas.append(f"  {lado}: se desplazan {', '.join(b.name.split(':')[-1] for b in hijos)}")
bpy.ops.object.mode_set(mode="OBJECT")
arm.data["brazo_factor"] = FACTOR

bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
texto = "=== BRAZO MÁS LARGO (hombro -> codo) x%.2f ===\n" % FACTOR + "\n".join(lineas) + f"\n  GUARDADO {os.path.relpath(BLEND, C.RAIZ)}\n"
print(texto)
with open(os.path.join(C.TRABAJO, "b_brazo_resumen.txt"), "w", encoding="utf-8") as fh:
    fh.write(texto)
