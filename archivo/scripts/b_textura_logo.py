"""Rehace la textura sin logo (modelos/Boxer_texture_sin_logo.png) dentro de boxeador.blend y
boxeador_c.blend sin volver a montar los modelos: parte de la textura original y tapa la
etiqueta de los puños de Guante_Left y Guante_Right (modelo_b.textura_sin_logo).

Uso:
  blender.exe --background --python scripts/b_textura_logo.py
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun as C  # noqa: E402
import modelo_b as MB  # noqa: E402

for fichero in ("boxeador.blend", "boxeador_c.blend"):
    ruta = os.path.join(C.TRABAJO, fichero)
    bpy.ops.wm.open_mainfile(filepath=ruta)
    n = MB.textura_sin_logo(bpy.data.objects["Guante_Left"], desde_original=True)
    n += MB.textura_sin_logo(bpy.data.objects["Guante_Right"])
    for im in [i for i in bpy.data.images if i.users == 0]:
        bpy.data.images.remove(im)
    bpy.ops.wm.save_as_mainfile(filepath=ruta, compress=True)
    print(f"[LOGO] {fichero}: {n} píxeles pintados")
