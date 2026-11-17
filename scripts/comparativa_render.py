"""Comparativa v2 / B / C: guardia (fot. 1) e impactos del jab y del crochet adelantado,
de frente y de lado, con la misma cámara para las tres (mismo tamaño en pantalla).

Escribe en trabajo/capturas/:
  comparativa_v2_b_c.png                     guardia (filas: frente, lado; columnas: v2, B, C)
  comparativa_impacto_jab_v2_b_c.png         impacto del jab
  comparativa_impacto_crochet_adelantado_v2_b_c.png
El fotograma de impacto se lee de trabajo/fase3_resumen.txt (es la misma animación en las tres).

Uso:
  blender.exe --background --python scripts/comparativa_render.py
"""
import os
import re
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun as C  # noqa: E402

VARIANTES = [("v2", "boxeador.blend"), ("B", "boxeador_b.blend"), ("C", "boxeador_c.blend")]
VISTAS = {"frente": Vector((0, -1, 0)), "lado": Vector((1, 0, 0))}
P = "mixamorig:"
RES = 900          # píxeles por panel (cuadrado)
ALTO = 2.15        # metros que cubre el panel
TMP = os.path.join(C.CAPTURAS, "_paneles")
os.makedirs(TMP, exist_ok=True)


def impacto(golpe):
    txt = open(os.path.join(C.TRABAJO, "fase3_resumen.txt"), encoding="utf-8").read()
    return int(re.search(rf"^\s+{golpe}\s+mano.*?IMPACTO fot\.\s+(\d+)", txt, re.M).group(1))


TOMAS = {"guardia": ("guardia", 1), "impacto_jab": ("jab", impacto("jab")),
         "impacto_crochet_adelantado": ("crochet_adelantado", impacto("crochet_adelantado"))}


def poner(arm, accion, f):
    a = bpy.data.actions[accion]
    arm.animation_data.action = a
    if arm.animation_data.action_slot is None:
        arm.animation_data.action_slot = a.slots[0]
    bpy.context.scene.frame_set(f)


def preparar(esc):
    esc.render.engine = "BLENDER_WORKBENCH"
    esc.render.resolution_x = esc.render.resolution_y = RES
    esc.render.image_settings.file_format = "PNG"
    esc.render.image_settings.color_mode = "RGB"
    esc.view_settings.view_transform = "Standard"
    sh = esc.display.shading
    sh.light, sh.color_type = "STUDIO", "TEXTURE"
    sh.show_cavity = True
    sh.cavity_type = "BOTH"
    sh.show_object_outline = False
    w = bpy.data.worlds.new("fondo")
    w.color = (0.85, 0.85, 0.86)
    esc.world = w
    m = bpy.data.materials.new("rotulo")
    m.diffuse_color = (0.05, 0.05, 0.05, 1)
    return m


def render(esc, arm, d, etiqueta, ruta, mat_rotulo):
    hp = arm.matrix_world @ arm.pose.bones[P + "Hips"].head
    cd = bpy.data.cameras.new("cam")
    cd.type, cd.ortho_scale, cd.clip_end = "ORTHO", ALTO, 100
    cam = bpy.data.objects.new("cam", cd)
    esc.collection.objects.link(cam)
    dg = bpy.context.evaluated_depsgraph_get()
    zmin = 0.0
    for o in esc.objects:
        if o.type == "MESH" and o.visible_get():
            oe = o.evaluated_get(dg)
            m = oe.to_mesh()
            if len(m.vertices):
                zmin = min(zmin, min((oe.matrix_world @ v.co).z for v in m.vertices))
            oe.to_mesh_clear()
    centro = Vector((hp.x, hp.y, zmin + ALTO / 2 - 0.04))   # los pies siempre dentro (la guardia los hunde)
    if d.x:                       # de lado: centrado en la cadera, algo hacia delante (golpes)
        centro.y -= 0.12
    cam.location = centro + d * 10
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    esc.camera = cam
    der = (-d).cross(Vector((0, 0, 1)))
    td = bpy.data.curves.new("rot", "FONT")
    td.body, td.size = etiqueta, 0.085
    tx = bpy.data.objects.new("rot", td)
    tx.data.materials.append(mat_rotulo)
    esc.collection.objects.link(tx)
    tx.location = centro - der * (ALTO / 2 - 0.06) + Vector((0, 0, ALTO / 2 - 0.12)) + d * 2
    tx.rotation_euler = cam.rotation_euler
    esc.render.filepath = ruta
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(tx)
    bpy.data.objects.remove(cam)


hechas = []
for var, fichero in VARIANTES:
    ruta = os.path.join(C.TRABAJO, fichero)
    if not os.path.exists(ruta):
        print("[FALTA]", ruta)
        continue
    bpy.ops.wm.open_mainfile(filepath=ruta)
    esc = bpy.context.scene
    arm = bpy.data.objects["Boxeador"]
    mat = preparar(esc)
    for toma, (accion, f) in TOMAS.items():
        for vista, d in VISTAS.items():
            poner(arm, accion, f)
            texto = f"{var}  {vista}" + ("" if toma == "guardia" else f"  {accion} f{f}")
            render(esc, arm, d, texto, os.path.join(TMP, f"{toma}_{var}_{vista}.png"), mat)
    hechas.append(var)


def pixeles(img):
    px = np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], 4)
    return px[::-1, :, :3]


bpy.ops.wm.read_factory_settings(use_empty=True)
SEP = 8
for toma in TOMAS:
    filas = []
    for vista in VISTAS:
        cols = []
        for var in hechas:
            img = bpy.data.images.load(os.path.join(TMP, f"{toma}_{var}_{vista}.png"))
            cols.append(pixeles(img))
            cols.append(np.full((RES, SEP, 3), 0.3, np.float32))
            bpy.data.images.remove(img)
        filas.append(np.concatenate(cols[:-1], axis=1))
        filas.append(np.full((SEP, filas[-1].shape[1], 3), 0.3, np.float32))
    lienzo = np.concatenate(filas[:-1], axis=0)
    h, w = lienzo.shape[:2]
    out = bpy.data.images.new(toma, w, h, alpha=False)
    out.pixels[:] = np.concatenate([lienzo, np.ones((h, w, 1), np.float32)], axis=2)[::-1].ravel()
    nombre = "comparativa_v2_b_c.png" if toma == "guardia" else f"comparativa_{toma}_v2_b_c.png"
    out.filepath_raw = os.path.join(C.CAPTURAS, nombre)
    out.file_format = "PNG"
    out.save()
    print("[PNG]", out.filepath_raw, "variantes:", hechas)
print("FIN COMPARATIVA")
