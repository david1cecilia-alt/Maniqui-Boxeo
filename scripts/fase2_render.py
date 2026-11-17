"""Fase 2 – renders de comprobación de trabajo/boxeador.blend (Workbench, 1024 px).

Requiere haber ejecutado antes fase2_montar.py.
Uso:
  blender.exe --background --python scripts/fase2_render.py
"""
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun as C  # noqa: E402

BLEND = os.path.join(C.TRABAJO, "boxeador_v2.blend")
P = "mixamorig:"
VISTAS = {"frente": Vector((0, -1, 0)), "lado": Vector((1, 0, 0))}  # lado = desde su izquierda

bpy.ops.wm.open_mainfile(filepath=BLEND)
esc = bpy.context.scene
arm = bpy.data.objects["Boxeador"]
os.makedirs(C.CAPTURAS, exist_ok=True)

esc.render.engine = "BLENDER_WORKBENCH"
esc.render.resolution_x = esc.render.resolution_y = 1024
esc.render.film_transparent = False
esc.render.image_settings.file_format = "PNG"
sh = esc.display.shading
sh.light = "STUDIO"
sh.color_type = "MATERIAL"
sh.show_cavity = True
sh.show_object_outline = True
w = bpy.data.worlds.new("fondo")
w.color = (0.92, 0.92, 0.92)
esc.world = w


def poner(accion, f):
    a = bpy.data.actions[accion]
    arm.animation_data.action = a
    if arm.animation_data.action_slot is None:
        arm.animation_data.action_slot = a.slots[0]
    esc.frame_set(f)


def bbox():
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in bpy.data.objects:
        if o.type == "MESH":
            oe = o.evaluated_get(dg)
            me = oe.to_mesh()
            pts += [oe.matrix_world @ v.co for v in me.vertices]
            oe.to_mesh_clear()
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def camara(mn, mx, vista, margen=1.15):
    d = VISTAS[vista]
    ancho = (mx.x - mn.x) if vista == "frente" else (mx.y - mn.y)
    cam_d = bpy.data.cameras.new("cam")
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = max(mx.z - mn.z, ancho) * margen
    cam_d.clip_end = 100
    cam = bpy.data.objects.new("cam", cam_d)
    esc.collection.objects.link(cam)
    cam.location = (mn + mx) / 2 + d * 10
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    esc.camera = cam
    return cam


def render(nombre):
    esc.render.filepath = os.path.join(C.CAPTURAS, nombre)
    bpy.ops.render.render(write_still=True)
    print("[PNG]", nombre)


def serie(accion, fotos, vista, prefijo):
    """Misma cámara para todos los fotogramas, para poder compararlos."""
    cajas = []
    for f in fotos.values():
        poner(accion, f)
        cajas.append(bbox())
    mn = Vector((min(c[0][i] for c in cajas) for i in range(3)))
    mx = Vector((max(c[1][i] for c in cajas) for i in range(3)))
    cam = camara(mn, mx, vista)
    for etiqueta, f in fotos.items():
        poner(accion, f)
        render(f"{prefijo}_{accion}_{etiqueta}_f{f:03d}_{vista}.png")
    bpy.data.objects.remove(cam)


def punto_bajo(accion):
    a = bpy.data.actions[accion]
    f0, f1 = int(a.frame_range[0]), int(a.frame_range[1])
    alturas = {}
    for f in range(f0, f1 + 1):
        poner(accion, f)
        alturas[f] = (arm.matrix_world @ arm.pose.bones[P + "Hips"].head).z
    return f0, min(alturas, key=alturas.get), f1


# guardia con ropa y guantes, de frente y de lado
for v in ("frente", "lado"):
    serie("guardia", {"ini": 1}, v, "fase2")

# primer plano de los guantes en la guardia (fot. 1)
poner("guardia", 1)
gl, gr = bpy.data.objects["Guante_Left"], bpy.data.objects["Guante_Right"]
pts = [o.matrix_world @ v.co for o in (gl, gr) for v in o.data.vertices]
mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
for v in ("frente", "lado"):
    cam = camara(mn - Vector((0.05,) * 3), mx + Vector((0.05,) * 3), v, margen=1.0)
    render(f"fase2_guardia_guantes_f001_{v}.png")
    bpy.data.objects.remove(cam)

# animaciones nuevas: inicio, punto bajo, final
for accion, vistas in (("flexion", ["lado"]), ("paso_atras", ["lado"]), ("rueda", ["frente"])):
    ini, bajo, fin = punto_bajo(accion)
    for v in vistas:
        serie(accion, {"1ini": ini, "2bajo": bajo, "3fin": fin}, v, "fase2")
print("FIN RENDERS FASE 2")
