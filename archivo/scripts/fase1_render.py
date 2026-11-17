"""Fase 1 – renders de diagnóstico (Workbench, 1024 px) en trabajo/capturas/.

Requiere haber ejecutado antes fase1_extraer_datos.py y fase1_analizar.py
(lee trabajo/fotogramas_clave.json).
Uso:
  blender.exe --background --python scripts/fase1_render.py
"""
import json
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun as C  # noqa: E402

os.makedirs(C.CAPTURAS, exist_ok=True)
CLAVE = json.load(open(os.path.join(C.TRABAJO, "fotogramas_clave.json")))["clave"]

# Vistas (el muñeco mira hacia -Y): dirección desde la que mira la cámara
VISTAS = {"frente": Vector((0, -1, 0)), "lado": Vector((1, 0, 0))}  # lado = desde su izquierda


def preparar_render():
    esc = bpy.context.scene
    esc.render.engine = "BLENDER_WORKBENCH"
    esc.render.resolution_x = esc.render.resolution_y = 1024
    esc.render.film_transparent = False
    sh = esc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "SINGLE"
    sh.single_color = (0.75, 0.62, 0.5)
    sh.show_cavity = True
    sh.show_object_outline = True
    w = bpy.data.worlds.new("fondo")
    w.color = (0.92, 0.92, 0.92)
    esc.world = w
    esc.render.image_settings.file_format = "PNG"


def bbox_mallas():
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in bpy.data.objects:
        if o.type == "MESH" and len(o.data.vertices) > 0:
            oe = o.evaluated_get(dg)
            me = oe.to_mesh()
            pts += [oe.matrix_world @ v.co for v in me.vertices]
            oe.to_mesh_clear()
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def render(nombre_archivo, vista):
    mn, mx = bbox_mallas()
    centro = (mn + mx) / 2
    tam = max((mx - mn).length * 0.75, 1.0)
    cam_d = bpy.data.cameras.new("cam")
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = max(mx.z - mn.z, abs((mx - mn).dot(Vector((1, 1, 0)) - Vector((abs(VISTAS[vista].x), abs(VISTAS[vista].y), 0))))) * 1.15
    cam = bpy.data.objects.new("cam", cam_d)
    bpy.context.scene.collection.objects.link(cam)
    d = VISTAS[vista]
    cam.location = centro + d * (tam + 5)
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    cam_d.clip_end = 100
    bpy.context.scene.camera = cam
    bpy.context.scene.render.filepath = os.path.join(C.CAPTURAS, nombre_archivo)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    print("[PNG]", nombre_archivo)


def toma(anim, fotograma, vistas, sufijo):
    C.importar(anim)
    preparar_render()
    bpy.context.scene.frame_set(fotograma)
    for v in vistas:
        render(f"{anim}_{sufijo}_{v}.png", v)


# guardias: frente y lado (fotograma 1)
for g in ("guardia", "guardia_alt"):
    toma(g, 1, ["frente", "lado"], "f001")

# golpes y resto: fotograma de máximo movimiento, de frente
for anim, info in CLAVE.items():
    f = info["fotograma"]
    toma(anim, f, ["frente"], f"max_f{f:03d}")

# esquiva retrocediendo: secuencia de lado para valorar el "paso atrás"
for f in (1, 10, 23, 38, 51, 67):
    toma("esquiva_retrocediendo", f, ["lado"], f"seq_f{f:03d}")
print("FIN RENDERS")
