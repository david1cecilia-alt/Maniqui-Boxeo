"""Fase 4 – renders del modelo principal (B): original frente a _v2.

trabajo/capturas/:
  fase4_guardia_v2.png              guardia fot. 1 (filas: frente, lado; columnas: original, _v2)
  fase4_impacto_<golpe>.png         fotograma de impacto de cada golpe (igual distribución)
  fase4_codo_cerca.png              primer plano del codo en su máxima flexión (guardia, jab y
                                    crochet_adelantado; fila de arriba original, abajo _v2)
Los fotogramas de impacto se leen de trabajo/fase3_resumen.txt y los de máxima flexión de
trabajo/b_codo_max_flexion.txt (b_codo_diag.py).

Uso:
  blender.exe --background --python scripts/fase4_render.py
"""
import os
import re
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun as C  # noqa: E402

BLEND = os.path.join(C.TRABAJO, "boxeador.blend")
P = "mixamorig:"
RES, ALTO = 800, 2.0
VISTAS = {"frente": Vector((0, -1, 0)), "lado": Vector((1, 0, 0))}
GOLPES = ["jab", "recto", "crochet_adelantado", "crochet_trasero", "crochet_trasero_cuerpo",
          "gancho_adelantado_mixamo", "gancho_trasero_cuerpo"]
TMP = os.path.join(C.CAPTURAS, "_paneles")
os.makedirs(TMP, exist_ok=True)
txt = open(os.path.join(C.TRABAJO, "fase3_resumen.txt"), encoding="utf-8").read()
IMPACTO = {g: int(re.search(rf"^\s+{g}\s+mano.*?IMPACTO fot\.\s+(\d+)", txt, re.M).group(1)) for g in GOLPES}
FLEX = {}
for linea in open(os.path.join(C.TRABAJO, "b_codo_max_flexion.txt"), encoding="utf-8"):
    a, f, lado = linea.split()
    FLEX[a] = (int(f), lado)

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
    cam.location = centro + d * 10
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    esc.camera = cam
    R = cam.rotation_euler.to_matrix()   # (matrix_world aún no está actualizada)
    arriba = R @ Vector((0, 1, 0))
    der = R @ Vector((1, 0, 0))
    td = bpy.data.curves.new("rot", "FONT")
    td.body, td.size = etiqueta, alto * 0.04
    tx = bpy.data.objects.new("rot", td)
    tx.data.materials.append(m_rot)
    esc.collection.objects.link(tx)
    tx.location = centro - der * (alto / 2 - alto * 0.03) + arriba * (alto / 2 - alto * 0.06) + d * 2
    tx.rotation_euler = cam.rotation_euler
    esc.render.filepath = ruta
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(tx)
    bpy.data.objects.remove(cam)


def centro_cuerpo():
    hp = arm.matrix_world @ arm.pose.bones[P + "Hips"].head
    return Vector((hp.x, hp.y - 0.1, ALTO / 2 - 0.04))


def montar(paneles, filas, cols, nombre, res=RES):
    sep = 6
    imgs = []
    for ruta in paneles:
        im = bpy.data.images.load(ruta)
        imgs.append(np.array(im.pixels[:], dtype=np.float32).reshape(res, res, 4)[::-1, :, :3])
        bpy.data.images.remove(im)
    gris = np.full((res, sep, 3), 0.3, np.float32)
    lineas = []
    for r in range(filas):
        fila = []
        for c in range(cols):
            fila += [imgs[r * cols + c], gris]
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


# guardia e impactos
for toma, (accion, f) in [("guardia_v2", ("guardia", 1))] + [(f"impacto_{g}", (g, IMPACTO[g])) for g in GOLPES]:
    paneles = []
    for vista, d in VISTAS.items():
        for sufijo in ("", "_v2"):
            poner(accion + sufijo, f)
            ruta = os.path.join(TMP, f"{toma}_{vista}{sufijo}.png")
            render(centro_cuerpo(), d, ALTO, f"{accion + sufijo} f{f}  {vista}", ruta)
            paneles.append(ruta)
    montar(paneles, 2, 2, f"fase4_{toma}.png")

# codo de cerca en su máxima flexión
paneles = []
for sufijo in ("", "_v2"):
    for accion in ("guardia", "jab", "crochet_adelantado"):
        f, lado = FLEX[accion + sufijo]
        poner(accion + sufijo, f)
        fa = arm.pose.bones[P + lado + "ForeArm"]
        ua = arm.pose.bones[P + lado + "Arm"]
        codo = arm.matrix_world @ fa.head
        n = (ua.tail - ua.head).cross(fa.tail - fa.head).normalized()   # normal del plano del brazo
        hacia_fuera = (codo - arm.matrix_world @ arm.pose.bones[P + "Spine2"].head)
        if n.dot(hacia_fuera) < 0:
            n = -n
        d = (n + hacia_fuera.normalized() * 0.5).normalized()
        ruta = os.path.join(TMP, f"codo_{accion}{sufijo}.png")
        render(codo, d, 0.32, f"{accion + sufijo} f{f} codo {lado}", ruta, res=600)
        paneles.append(ruta)
montar(paneles, 2, 3, "fase4_codo_cerca.png", res=600)
print("FIN RENDERS FASE 4")
