"""Modelo B – análisis de modelos/boxeador_b.fbx y boxeador_b_rig.fbx.

Mallas, materiales, piezas sueltas (islas) con su hueso dominante y color de textura,
huesos y comparación con el esqueleto de trabajo/boxeador.blend.
Escribe trabajo/b_analisis.txt y trabajo/capturas/b_analisis_textura|islas.png.

Uso:
  blender.exe --background --python scripts/b_analizar.py
"""
import colorsys
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun as C  # noqa: E402
import modelo_b as MB  # noqa: E402

FBX_SIN_RIG = os.path.join(C.RAIZ, "modelos", "boxeador_b.fbx")
BLEND = os.path.join(C.TRABAJO, "boxeador_v2.blend")
out = []


def p(*a):
    linea = " ".join(str(x) for x in a)
    out.append(linea)
    print(linea)


# ---------------------------------------------------------------- esqueleto de referencia (A)
bpy.ops.wm.open_mainfile(filepath=BLEND)
arm_a = bpy.data.objects["Boxeador"]
ref = {b.name: (arm_a.matrix_world @ b.head_local, arm_a.matrix_world @ b.tail_local, b.parent.name if b.parent else None)
       for b in arm_a.data.bones}
rot_a = {b.name: b.matrix_local.to_quaternion() for b in arm_a.data.bones}
cu_a = bpy.data.objects["Cuerpo"]
co_a = np.array([cu_a.matrix_world @ v.co for v in cu_a.data.vertices])
p(f"A (boxeador.blend): esqueleto escala {tuple(arm_a.scale)}, cuerpo z {co_a[:, 2].min():.3f}-{co_a[:, 2].max():.3f} m,"
  f" ancho brazos {co_a[:, 0].min():.3f}..{co_a[:, 0].max():.3f}")

# ---------------------------------------------------------------- B sin rig
C.escena_vacia()
bpy.ops.import_scene.fbx(filepath=FBX_SIN_RIG)
p("=== modelos/boxeador_b.fbx:", [(o.name, o.type) for o in bpy.data.objects],
  f"| esqueletos: {len(bpy.data.armatures)} | grupos de vértices de 'Boxer':",
  len(bpy.data.objects["Boxer"].vertex_groups), "-> NO ESTÁ RIGEADO")

# ---------------------------------------------------------------- B rigeado
C.escena_vacia()
arm, ob = MB.cargar_b()
me = ob.data
co = np.array([ob.matrix_world @ v.co for v in me.vertices])
p("=== modelos/boxeador_b_rig.fbx (Animations/Idle.fbx de la descarga de Creazilla) ===")
p(f"esqueleto: {len(arm.data.bones)} huesos | malla '{ob.name}': {len(me.vertices)} vért., {len(me.polygons)} caras")
p(f"caja (m, normalizada): min {np.round(co.min(0), 3)} max {np.round(co.max(0), 3)} -> alto {co[:, 2].max() - co[:, 2].min():.3f} m")
p(f"materiales: {[m.name for m in me.materials]} (uno solo, con textura 1 imagen); UV: {[u.name for u in me.uv_layers]}")
p(f"grupos de vértices ({len(ob.vertex_groups)}): {[g.name.split(':')[-1] for g in ob.vertex_groups]}")

isl = MB.islas(me)
dom = MB.dominante(ob)
col = MB.color_textura(ob)
n_isl = isl.max() + 1
p(f"\npiezas sueltas (islas): {n_isl}")
p(f"{'isla':>4} {'vért':>6}  {'z (m)':13} {'x (m)':15} {'y (m)':15} {'hueso dominante (%)':38} color textura")
info = []
for i in range(n_isl):
    sel = np.where(isl == i)[0]
    c = co[sel]
    g, cnt = np.unique(dom[sel], return_counts=True)
    top = sorted(zip(cnt, g), reverse=True)[:2]
    huesos = ", ".join(f"{n} {100 * k / len(sel):.0f}" for k, n in top)
    rgb = col[sel].mean(0) if col is not None else np.zeros(3)
    info.append((i, sel, c, top[0][1], rgb))
    p(f"{i:4} {len(sel):6}  {c[:, 2].min():.3f}-{c[:, 2].max():.3f}  {c[:, 0].min():+.3f}..{c[:, 0].max():+.3f}"
      f"  {c[:, 1].min():+.3f}..{c[:, 1].max():+.3f}  {huesos:38} {np.round(rgb, 2)}")

# ---------------------------------------------------------------- huesos
p("\n=== HUESOS B vs A (boxeador.blend), en metros ===")
nb = {b.name: (arm.matrix_world @ b.head_local, arm.matrix_world @ b.tail_local, b.parent.name if b.parent else None)
      for b in arm.data.bones}
p(f"A {len(ref)} huesos, B {len(nb)}, comunes {len(set(ref) & set(nb))}; solo A {sorted(set(ref) - set(nb))};"
  f" solo B {sorted(set(nb) - set(ref))}; padres distintos {[n for n in set(ref) & set(nb) if ref[n][2] != nb[n][2]]}")
for n in sorted(set(ref) & set(nb), key=lambda n: ref[n][0].z, reverse=True):
    da, db = ref[n][0], nb[n][0]
    la, lb = ref[n][1] - ref[n][0], nb[n][1] - nb[n][0]
    ang = np.degrees(np.arccos(max(-1.0, min(1.0, la.normalized().dot(lb.normalized())))))
    ang_eje = np.degrees(rot_a[n].rotation_difference(arm.data.bones[n].matrix_local.to_quaternion()).angle)
    p(f"  {n.split(':')[-1]:14} A {np.round(np.array(da), 3)}  B {np.round(np.array(db), 3)}"
      f"  long A {la.length * 100:5.1f} B {lb.length * 100:5.1f} cm  dirección {ang:5.1f}°  ejes {ang_eje:5.1f}°")

# ---------------------------------------------------------------- renders (textura e islas)
esc = bpy.context.scene
esc.render.engine = "BLENDER_WORKBENCH"
esc.render.resolution_x, esc.render.resolution_y = 1600, 900
sh = esc.display.shading
sh.light = "STUDIO"
w = bpy.data.worlds.new("fondo")
w.color = (0.92, 0.92, 0.92)
esc.world = w
cd = bpy.data.cameras.new("cam")
cd.type, cd.ortho_scale = "ORTHO", 2.1
cam = bpy.data.objects.new("cam", cd)
esc.collection.objects.link(cam)
cam.location = Vector((0, -10, co[:, 2].mean()))
cam.rotation_euler = (Vector((0, 1, 0))).to_track_quat("-Z", "Y").to_euler()
esc.camera = cam
sh.color_type = "TEXTURE"
esc.render.filepath = os.path.join(C.CAPTURAS, "b_analisis_textura.png")
bpy.ops.render.render(write_still=True)
# color por isla (atributo de color de vértice)
ca = me.color_attributes.new("isla", "FLOAT_COLOR", "POINT")
for i, sel, *_ in info:
    rgb = colorsys.hsv_to_rgb((i * 0.618) % 1.0, 0.75, 0.95)
    for v in sel:
        ca.data[v].color = (*rgb, 1.0)
sh.color_type = "VERTEX"
esc.render.filepath = os.path.join(C.CAPTURAS, "b_analisis_islas.png")
bpy.ops.render.render(write_still=True)

with open(os.path.join(C.TRABAJO, "b_analisis.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out) + "\n")
print("FIN ANALISIS B")
