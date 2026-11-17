"""Fase 5 – renders de las correcciones (modelo B, trabajo/boxeador.blend).

trabajo/capturas/ (fila de arriba de frente, abajo de lado desde su izquierda):
  fase5_paso_atras_v2.png              inicio, punto clave (pie de atrás ya apoyado) y final
  fase5_bloqueos.png                   los 5 bloqueos en su punto clave (fot. 14)
  fase5_bloqueos_cerca.png             los mismos, de cerca (cabeza y tronco)
  fase5_esquiva_retrocediendo_v2.png   5 fotogramas
  fase5_esquiva_avanzando_v2.png       5 fotogramas
  fase5_rueda_der.png / fase5_rueda_izq.png   5 fotogramas de la "U"
La cámara no se mueve dentro de cada lámina (se ve el desplazamiento) y el suelo (Z=0) es la
línea gris.

Uso:
  blender.exe --background --python scripts/fase5_render.py
"""
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun as C  # noqa: E402

BLEND = os.path.join(C.TRABAJO, "boxeador.blend")
P = "mixamorig:"
RES, ALTO = 640, 2.0
VISTAS = {"frente": Vector((0, -1, 0)), "lado": Vector((1, 0, 0))}
TMP = os.path.join(C.CAPTURAS, "_paneles")
os.makedirs(TMP, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=BLEND)
esc = bpy.context.scene
arm = bpy.data.objects["Boxeador"]
esc.render.engine = "BLENDER_WORKBENCH"
esc.render.image_settings.file_format = "PNG"
esc.render.image_settings.color_mode = "RGB"
esc.view_settings.view_transform = "Standard"
sh = esc.display.shading
sh.light, sh.color_type = "STUDIO", "TEXTURE"
sh.show_cavity = True
sh.cavity_type = "BOTH"
w = bpy.data.worlds.new("fondo")
w.color = (0.85, 0.85, 0.86)
esc.world = w
m_rot = bpy.data.materials.new("rotulo")
m_rot.diffuse_color = (0.05, 0.05, 0.05, 1)
# suelo: plano fino gris oscuro en Z=0 (se ve como una línea de lado y de frente)
bpy.ops.mesh.primitive_plane_add(size=3, location=(0, 0, -0.001))
suelo = bpy.context.object
m_suelo = bpy.data.materials.new("suelo")
m_suelo.diffuse_color = (0.45, 0.45, 0.47, 1)
suelo.data.materials.append(m_suelo)
sh.color_type = "TEXTURE"


def poner(accion, f):
    a = bpy.data.actions[accion]
    arm.animation_data.action = a
    if arm.animation_data.action_slot is None or arm.animation_data.action_slot.identifier not in [s.identifier for s in a.slots]:
        arm.animation_data.action_slot = a.slots[0]
    esc.frame_set(f)


def render(centro, d, alto, etiqueta, ruta, res=RES):
    esc.render.resolution_x = esc.render.resolution_y = res
    cd = bpy.data.cameras.new("cam")
    cd.type, cd.ortho_scale, cd.clip_end = "ORTHO", alto, 100
    cam = bpy.data.objects.new("cam", cd)
    esc.collection.objects.link(cam)
    # un poco desde arriba para ver el suelo
    dd = (d + Vector((0, 0, 0.12))).normalized()
    cam.location = centro + dd * 10
    cam.rotation_euler = (-dd).to_track_quat("-Z", "Y").to_euler()
    esc.camera = cam
    R = cam.rotation_euler.to_matrix()
    arriba = R @ Vector((0, 1, 0))
    der = R @ Vector((1, 0, 0))
    td = bpy.data.curves.new("rot", "FONT")
    td.body, td.size = etiqueta, alto * 0.045
    tx = bpy.data.objects.new("rot", td)
    tx.data.materials.append(m_rot)
    esc.collection.objects.link(tx)
    tx.location = centro - der * (alto / 2 - alto * 0.03) + arriba * (alto / 2 - alto * 0.07) + dd * 2
    tx.rotation_euler = cam.rotation_euler
    esc.render.filepath = ruta
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(tx)
    bpy.data.objects.remove(cam)


def montar(paneles, filas, cols, nombre, res=RES):
    sep = 6
    imgs = []
    for ruta in paneles:
        im = bpy.data.images.load(ruta)
        imgs.append(np.array(im.pixels[:], dtype=np.float32).reshape(res, res, 4)[::-1, :, :3])
        bpy.data.images.remove(im)
    lineas = []
    for r in range(filas):
        fila = []
        for c in range(cols):
            fila += [imgs[r * cols + c], np.full((res, sep, 3), 0.3, np.float32)]
        lineas.append(np.concatenate(fila[:-1], axis=1))
        lineas.append(np.full((sep, lineas[-1].shape[1], 3), 0.3, np.float32))
    lienzo = np.concatenate(lineas[:-1], axis=0)
    h, w_ = lienzo.shape[:2]
    out = bpy.data.images.new(nombre, w_, h, alpha=False)
    out.pixels[:] = np.concatenate([lienzo, np.ones((h, w_, 1), np.float32)], axis=2)[::-1].ravel()
    out.filepath_raw = os.path.join(C.CAPTURAS, nombre)
    out.file_format = "PNG"
    out.save()
    print("[PNG]", out.filepath_raw)


def lamina(nombre, tomas, alto=ALTO, cerca=False):
    """tomas: [(acción, fotograma, texto)]. Cámara fija (centrada en la primera toma)."""
    poner(tomas[0][0], tomas[0][1])
    hp = arm.pose.bones[P + "Hips"].head
    if cerca:
        cab = arm.pose.bones[P + "Head"].head
        centro = Vector((hp.x, hp.y - 0.05, cab.z - 0.15))
    else:
        centro = Vector((hp.x, hp.y - 0.1, alto / 2 - 0.06))
    paneles = []
    for vista, d in VISTAS.items():
        for accion, f, texto in tomas:
            poner(accion, f)
            ruta = os.path.join(TMP, f"f5_{nombre}_{accion}_{f}_{vista}.png")
            render(centro, d, alto, f"{accion} f{f} {texto}  {vista}", ruta)
            paneles.append(ruta)
    montar(paneles, 2, len(tomas), f"fase5_{nombre}.png")


def ultimo(accion):
    return int(bpy.data.actions[accion].frame_range[1])


lamina("paso_atras_v2", [("paso_atras_v2", 1, "inicio"), ("paso_atras_v2", 13, "clave"),
                         ("paso_atras_v2", ultimo("paso_atras_v2"), "final")], alto=2.2)
BLQ = ["bloqueo_cerrado", "bloqueo_alto_izq", "bloqueo_alto_der", "bloqueo_bajo_izq", "bloqueo_bajo_der"]
lamina("bloqueos", [("guardia_v2", 1, "")] + [(b, 14, "") for b in BLQ])
lamina("bloqueos_cerca", [("guardia_v2", 1, "")] + [(b, 14, "") for b in BLQ], alto=0.9, cerca=True)
for e in ("esquiva_retrocediendo_v2", "esquiva_avanzando_v2"):
    n = ultimo(e)
    lamina(e, [(e, f, "") for f in (1, 10, 28, 46, n)], alto=2.2)
for r in ("rueda_der", "rueda_izq"):
    lamina(r, [(r, f, "") for f in (1, 8, 19, 30, 37)])
print("FIN RENDERS FASE 5")
