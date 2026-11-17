"""Fichero final para la app: trabajo/boxeador_final.blend, solo con las acciones buenas y nombres limpios.

trabajo/boxeador.blend es el TALLER: guarda las acciones originales de Mixamo, las _v2 de la Fase 4 y las
intermedias, porque fase4_b.py y fase5_b.py las necesitan para rehacerse. Este script lo abre, borra todo
lo que no usa la app, renombra lo bueno (jab_v2 -> jab, etc.) y lo guarda aparte. boxeador.blend no se toca.

Cada acción final lleva las propiedades:
  app      "Nº nombre en la app" (p. ej. "1 Jab")
  origen   nombre de la acción en boxeador.blend de la que sale
  clave    fotograma clave (impacto / punto máximo): el que ya tenía, en los golpes de Mixamo el de impacto
           de fase3_comprobar.py; en el resto, la mitad.

Ejecutar el último, después de fase5_b.py (y cada vez que cambie algo). Escribe trabajo/final_resumen.txt.

Uso:
  blender.exe --background --python scripts/final_b.py
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun as C  # noqa: E402

TALLER = os.path.join(C.TRABAJO, "boxeador.blend")
FINAL = os.path.join(C.TRABAJO, "boxeador_final.blend")
P = "mixamorig:"

# (nº, nombre en la app, acción final, acción en el taller, fotograma de impacto si es golpe de Mixamo sin clave:
#  el de trabajo/fase3_resumen.txt; crochet_trasero +8 por la transición desde la guardia de fase5_b.py)
ACCIONES = [
    (1, "Jab", "jab", "jab_v2", 16),
    (2, "Recto", "recto", "recto_v2", 21),
    (3, "Crochet adelantado", "crochet_adelantado", "crochet_adelantado_v2", 16),
    (4, "Crochet trasero", "crochet_trasero", "crochet_trasero_v2", 19),
    (5, "Gancho adelantado", "gancho_adelantado", "gancho_adelantado", None),
    (6, "Gancho trasero", "gancho_trasero", "gancho_trasero", None),
    (7, "Jab al cuerpo", "jab_cuerpo", "jab_cuerpo", None),
    (8, "Recto al cuerpo", "recto_cuerpo", "recto_cuerpo", None),
    (9, "Crochet adelantado al cuerpo", "crochet_adelantado_cuerpo", "crochet_adelantado_cuerpo", None),
    (10, "Crochet trasero al cuerpo", "crochet_trasero_cuerpo", "crochet_trasero_cuerpo_v2", 24),
    (11, "Gancho adelantado al cuerpo", "gancho_adelantado_cuerpo", "gancho_adelantado_cuerpo", None),
    (12, "Gancho trasero al cuerpo", "gancho_trasero_cuerpo", "gancho_trasero_cuerpo_v2", 19),
    (13, "Guardia", "guardia", "guardia_v2", None),
    (13, "Guardia (alternativa)", "guardia_alt", "guardia_alt_v2", None),
    (14, "Bloqueo cerrado", "bloqueo_cerrado", "bloqueo_cerrado", None),
    (15, "Bloqueo alto izquierdo", "bloqueo_alto_izq", "bloqueo_alto_izq", None),
    (15, "Bloqueo alto derecho", "bloqueo_alto_der", "bloqueo_alto_der", None),
    (16, "Bloqueo bajo izquierdo", "bloqueo_bajo_izq", "bloqueo_bajo_izq", None),
    (16, "Bloqueo bajo derecho", "bloqueo_bajo_der", "bloqueo_bajo_der", None),
    (17, "Parada", "parada", "parada", None),
    (18, "Esquiva lateral derecha", "esquiva_der", "esquiva_der", None),
    (18, "Esquiva lateral izquierda", "esquiva_izq", "esquiva_izq", None),
    (19, "Flexión", "flexion", "flexion", None),
    (20, "Rueda derecha", "rueda_der", "rueda_der", None),
    (20, "Rueda izquierda", "rueda_izq", "rueda_izq", None),
    (21, "Ballesteo", "ballesteo", "ballesteo", None),
    (22, "Paso adelante", "paso_adelante", "paso_adelante", None),
    (23, "Paso atrás", "paso_atras", "paso_atras_v2", None),
    (24, "Paso lateral izquierdo", "paso_lateral_izq", "paso_lateral_izq", None),
    (24, "Paso lateral derecho", "paso_lateral_der", "paso_lateral_der", None),
    (25, "Pivote (ida y vuelta)", "pivote", "pivote_v2", None),
    (25, "Pivote derecha", "pivote_der", "pivote_der_v2", None),
    (25, "Pivote izquierda", "pivote_izq", "pivote_izq_v2", None),
]

out = []


def p(*a):
    out.append(" ".join(str(x) for x in a))
    print(out[-1])


bpy.ops.wm.open_mainfile(filepath=TALLER)
esc = bpy.context.scene
arm = bpy.data.objects["Boxeador"]
acc = bpy.data.actions
faltan = [t for *_, t, _m in ACCIONES if t not in acc]
assert not faltan, f"faltan en el taller: {faltan}"


def poner(a):
    arm.animation_data.action = a
    if arm.animation_data.action_slot is None or arm.animation_data.action_slot.identifier not in [s.identifier for s in a.slots]:
        arm.animation_data.action_slot = a.slots[0]


p("=== FICHERO FINAL PARA LA APP: trabajo/boxeador_final.blend ===")
p("(REVISAR CON ENTRENADOR: toda la técnica)")
datos = {}
for n, app, final, taller, impacto in ACCIONES:
    a = acc[taller]
    f0, f1 = (int(x) for x in a.frame_range)
    if "clave" in a:
        k = int(a["clave"])
    elif impacto:
        k = impacto
    else:
        k = (f0 + f1) // 2
    datos[taller] = (n, app, final, k)

usadas = set(datos)
borradas = sorted(a.name for a in acc if a.name not in usadas)
for nombre in borradas:
    acc.remove(acc[nombre])
for taller, (n, app, final, k) in datos.items():
    a = acc[taller]
    for clave in list(a.keys()):
        del a[clave]
    a.name = final
    assert a.name == final, (taller, a.name)
    a.use_fake_user = True
    a["app"] = f"{n} {app}"
    a["origen"] = taller
    a["clave"] = k
for n, app, final, taller, _m in ACCIONES:
    a = acc[final]
    f0, f1 = (int(x) for x in a.frame_range)
    p(f"  {n:2} {app:30} {final:26} <- {taller:26} fot. {f0}-{f1} ({(f1 - f0) / 30:.1f} s), clave {a['clave']}")
p(f"  Quitadas del fichero final ({len(borradas)}; siguen en boxeador.blend): {', '.join(borradas)}")

poner(acc["guardia"])
esc.frame_set(1)
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=FINAL, compress=True, copy=True)
p(f"  GUARDADO {os.path.relpath(FINAL, C.RAIZ)} ({len(acc)} acciones)")
with open(os.path.join(C.TRABAJO, "final_resumen.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out) + "\n")
