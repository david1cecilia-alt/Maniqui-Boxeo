"""Utilidades comunes para los scripts de Blender (Fase 1).

Los FBX originales se leen EN SU SITIO y nunca se modifican.
"""
import os
import bpy

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FBX_DIR = os.path.join(RAIZ, "fbx")
TRABAJO = os.path.join(RAIZ, "trabajo")
CAPTURAS = os.path.join(TRABAJO, "capturas")

# sin copias .blend1 al guardar (boxeador.blend es el taller; lo antiguo está en archivo/)
bpy.context.preferences.filepaths.save_version = 0

# nombre lógico -> ruta del FBX (originales de Mixamo, no incluidos en el repo)
FBX = {
    "figura": os.path.join(FBX_DIR, "extra", "BoxeoFigura.fbx"),
    "guardia": os.path.join(FBX_DIR, "guardia.fbx"),
    "guardia_alt": os.path.join(FBX_DIR, "guardia_alt.fbx"),
    "jab": os.path.join(FBX_DIR, "1_jab.fbx"),
    "recto": os.path.join(FBX_DIR, "2_recto.fbx"),
    "crochet_adelantado": os.path.join(FBX_DIR, "3_crochet_adelantado.fbx"),
    "crochet_trasero": os.path.join(FBX_DIR, "4_crochet_trasero.fbx"),
    "gancho_adelantado_cuerpo": os.path.join(FBX_DIR, "11_gancho_adelantado_cuerpo.fbx"),
    "gancho_trasero_cuerpo": os.path.join(FBX_DIR, "12_gancho_trasero_cuerpo.fbx"),
    "crochet_cuerpo": os.path.join(FBX_DIR, "10_crochet_cuerpo.fbx"),
    "bloqueo": os.path.join(FBX_DIR, "bloqueo.fbx"),
    "esquiva_avanzando": os.path.join(FBX_DIR, "extra", "futuros", "esquiva_avanzando_REVISAR.fbx"),
    "esquiva_retrocediendo": os.path.join(FBX_DIR, "extra", "futuros", "esquiva_retrocediendo_REVISAR.fbx"),
}

# FBX de Mixamo que se añaden directamente al modelo B (b_mixamo_nuevas.py): acción -> FBX
FBX_B = {
    "pivote": os.path.join(FBX_DIR, "pivote.fbx"),            # pivote de ida y vuelta
    "pivote_der": os.path.join(FBX_DIR, "pivote_der.fbx"),
    "pivote_izq": os.path.join(FBX_DIR, "pivote_izq.fbx"),
    "paso_atras": os.path.join(FBX_DIR, "paso_atras.fbx"),
}

GOLPES = ["jab", "recto", "crochet_adelantado", "crochet_trasero",
          "gancho_adelantado_cuerpo", "gancho_trasero_cuerpo", "crochet_cuerpo"]


def escena_vacia():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def importar(nombre):
    escena_vacia()
    bpy.ops.import_scene.fbx(filepath=FBX[nombre])
    arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
    mallas = [o for o in bpy.data.objects if o.type == "MESH"]
    return arm, mallas


def hueso(arm, sufijo):
    """Busca un hueso por sufijo (p.ej. 'LeftHand') ignorando el prefijo mixamorig."""
    for pb in arm.pose.bones:
        if pb.name.split(":")[-1] == sufijo:
            return pb
    return None


def pos_mundo(arm, sufijo, cola=False):
    pb = hueso(arm, sufijo)
    if pb is None:
        return None
    v = pb.tail if cola else pb.head
    return arm.matrix_world @ v
