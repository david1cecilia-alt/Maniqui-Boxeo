"""Láminas de las acciones de la app (trabajo/boxeador.blend, el bueno, de final_b.py).

trabajo/capturas/app/NN_<acción>.png, una por acción, numerada como en la app: 5 fotogramas (inicio, a
medio camino, CLAVE, a medio camino y final), fila de arriba de frente y abajo de lado desde su izquierda.
La cámara no se mueve dentro de cada lámina (se ve el desplazamiento) y el suelo (Z=0) es la línea gris.
Sin argumentos hace todas; con nombres de acción (finales, p. ej. jab rueda_der) solo esas.

Uso:
  blender.exe --background --python scripts/final_render.py [-- jab rueda_der ...]
"""
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun as C  # noqa: E402

BLEND = C.BLEND_FINAL
DEST = os.path.join(C.CAPTURAS, "app")
os.makedirs(DEST, exist_ok=True)
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
    out.filepath_raw = os.path.join(DEST, nombre)
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
            ruta = os.path.join(TMP, f"app_{nombre}_{f}_{vista}.png")
            render(centro, d, alto, f"{accion} f{f} {texto}  {vista}", ruta)
            paneles.append(ruta)
    montar(paneles, 2, len(tomas), f"{nombre}.png")

solo = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
acciones = sorted((a for a in bpy.data.actions if "app" in a), key=lambda a: (int(a["app"].split()[0]), a["app"]))
for a in acciones:
    if solo and a.name not in solo:
        continue
    n0, n = (int(x) for x in a.frame_range)
    k = int(a["clave"])
    fotos = sorted({n0, max(n0 + 1, (n0 + k) // 2), k, min(n - 1, (k + n) // 2), n})
    lamina(f"{int(a['app'].split()[0]):02d}_{a.name}", [(a.name, f, "clave" if f == k else "") for f in fotos], alto=2.2)
print("FIN LAMINAS APP")
