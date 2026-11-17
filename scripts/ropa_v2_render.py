"""Ropa v2 – renders de la guardia (fot. 1) junto a las referencias 07, 08 y 09.

Para cada referencia se mide dónde está la figura (píxeles más claros que el fondo) y
se encuadra el muñeco con una cámara ortográfica para que ocupe la misma altura y
posición, a la misma resolución. Se monta: referencia | muñeco (gris) | muñeco (color).
Las referencias NO se suben al repo (referencias/ está en .gitignore).

Uso:
  blender.exe --background --python scripts/ropa_v2_render.py
"""
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun as C  # noqa: E402

BLEND = os.path.join(C.TRABAJO, "boxeador_v2.blend")
REF = os.path.join(C.RAIZ, "referencias")
# vista: (referencia, dirección desde la que mira la cámara)
VISTAS = {
    "frente": ("07_cuerpo_entero_frente.png", Vector((0, -1, 0))),
    "espalda": ("08_cuerpo_entero_espalda.png", Vector((0, 1, 0))),
    "lado": ("09_cuerpo_entero_lado.png", Vector((1, 0, 0))),
}

bpy.ops.wm.open_mainfile(filepath=BLEND)
esc = bpy.context.scene
arm = bpy.data.objects["Boxeador"]
a = bpy.data.actions["guardia"]
arm.animation_data.action = a
if arm.animation_data.action_slot is None:
    arm.animation_data.action_slot = a.slots[0]
esc.frame_set(1)

esc.render.engine = "BLENDER_WORKBENCH"
esc.render.image_settings.file_format = "PNG"
esc.render.image_settings.color_mode = "RGB"
esc.view_settings.view_transform = "Standard"
sh = esc.display.shading
sh.light = "STUDIO"
sh.show_cavity = True
sh.cavity_type = "BOTH"
sh.show_object_outline = False
w = bpy.data.worlds.new("fondo")
w.color = (0.018, 0.020, 0.024)
esc.world = w


def pixeles(img):
    px = np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], 4)
    return px[::-1]  # fila 0 = arriba


def caja_figura(px):
    luz = px[..., :3].mean(axis=2)
    m = luz > 0.30
    filas, cols = np.where(m)
    return filas.min(), filas.max(), cols.min(), cols.max()


def puntos_mundo():
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in bpy.data.objects:
        if o.type == "MESH":
            oe = o.evaluated_get(dg)
            me = oe.to_mesh()
            M = np.array(oe.matrix_world)
            co = np.empty(len(me.vertices) * 3)
            me.vertices.foreach_get("co", co)
            pts.append(co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3])
            oe.to_mesh_clear()
    return np.vstack(pts)


PTS = puntos_mundo()


def render(vista, color, ruta):
    ref, d = VISTAS[vista]
    img = bpy.data.images.load(os.path.join(REF, ref))
    W, H = img.size
    top, bot, izq, der = caja_figura(pixeles(img))
    bpy.data.images.remove(img)
    derecha = d.cross(Vector((0, 0, 1)))  # eje horizontal de la imagen (hacia la derecha)
    derecha = -derecha                    # cámara mirando hacia -d
    xs = PTS @ np.array(derecha)
    zs = PTS[:, 2]
    # metros por píxel: misma altura que la figura de la referencia, salvo que la guardia
    # (base larga) no quepa a lo ancho; entonces se reduce para que quepa con margen
    escala = max((zs.max() - zs.min()) / (bot - top), (xs.max() - xs.min()) / (0.92 * W))
    cd = bpy.data.cameras.new("cam")
    cd.type = "ORTHO"
    cd.sensor_fit = "VERTICAL"
    cd.ortho_scale = escala * H
    cd.clip_end = 100
    cam = bpy.data.objects.new("cam", cd)
    esc.collection.objects.link(cam)
    zc = (zs.max() + zs.min()) / 2 - ((top + bot) / 2 - H / 2) * escala * -1   # centro vertical = el de la referencia
    xc = (xs.min() + xs.max()) / 2 - ((izq + der) / 2 - W / 2) * escala
    if (xs.max() - xs.min()) / escala > 0.85 * W:      # muy ancha: centrada en la imagen
        xc = (xs.min() + xs.max()) / 2
    centro = Vector(PTS.mean(axis=0))
    base = centro - derecha * centro.dot(derecha)
    base.z = zc
    cam.location = base + derecha * xc + d * 10
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    esc.camera = cam
    esc.render.resolution_x, esc.render.resolution_y = W, H
    sh.color_type = "MATERIAL" if color else "SINGLE"
    sh.single_color = (0.75, 0.75, 0.75)
    esc.render.filepath = ruta
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)


for vista, (ref, _) in VISTAS.items():
    tmp = [os.path.join(C.CAPTURAS, f"ropa_v2_guardia_{vista}_{t}.png") for t in ("gris", "color")]
    render(vista, False, tmp[0])
    render(vista, True, tmp[1])
    paneles = [bpy.data.images.load(os.path.join(REF, ref))] + [bpy.data.images.load(t) for t in tmp]
    px = [pixeles(i)[..., :3] for i in paneles]
    sep = np.full((px[0].shape[0], 6, 3), 0.5, dtype=np.float32)
    lienzo = np.concatenate([px[0], sep, px[1], sep, px[2]], axis=1)
    h, wd = lienzo.shape[:2]
    out = bpy.data.images.new(f"comp_{vista}", wd, h, alpha=False)
    rgba = np.concatenate([lienzo, np.ones((h, wd, 1), dtype=np.float32)], axis=2)[::-1]
    out.pixels[:] = rgba.ravel()
    out.filepath_raw = os.path.join(C.CAPTURAS, f"ropa_v2_comparativa_{vista}.png")
    out.file_format = "PNG"
    out.save()
    for i in paneles:
        bpy.data.images.remove(i)
    print("[PNG]", out.filepath_raw)
print("FIN RENDERS ROPA V2")
