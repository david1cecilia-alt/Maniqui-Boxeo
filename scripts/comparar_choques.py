"""Compara los choques de la Fase 3 con la ropa v1 y con la ropa v2 (Python 3 normal).

Lee trabajo/fase3_resumen_ropa_v1.txt (antes) y trabajo/fase3_resumen.txt (después) y
escribe trabajo/ropa_v2_choques_antes_despues.txt con el máximo (cm) de cada choque.

Uso:
  python scripts/comparar_choques.py   (o el python.exe que trae Blender)
"""
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TR = os.path.join(RAIZ, "trabajo")
RENOMBRE = {"gancho_adelantado": "gancho_adelantado_cuerpo", "gancho_trasero": "gancho_trasero_cuerpo"}
COLUMNAS = [("guante_guante", "guante-guante"), ("guante_cabeza", "guante-cabeza"),
            ("guante_cuerpo", "guante-cuerpo"), ("pantalon_cuerpo", "pantalón"),
            ("botas", "botas"), ("hueco_guante_antebrazo", "hueco")]


def leer(ruta):
    datos, accion = {}, None
    for linea in open(ruta, encoding="utf-8"):
        if linea.startswith("=== 2."):
            break
        m = re.match(r"-- (\S+) \(", linea)
        if m:
            accion = RENOMBRE.get(m.group(1), m.group(1))
            datos[accion] = {}
            continue
        m = re.match(r"\s+(\w+)\s+(OK|.*máx\. ([\d.]+) cm)", linea)
        if m and accion:
            k = m.group(1)
            v = 0.0 if m.group(2) == "OK" else float(m.group(3))
            if k.startswith("botas"):   # botas_cuerpo y botas_suela (v1) -> botas
                k = "botas"
                v = max(v, datos[accion].get(k, 0.0))
            datos[accion][k] = v
    return datos


antes = leer(os.path.join(TR, "fase3_resumen_ropa_v1.txt"))
despues = leer(os.path.join(TR, "fase3_resumen.txt"))
out = ["CHOQUES: ropa v1 -> ropa v2 (máximo en cm de toda la acción; 0 = sin choque > 0,2 cm)",
       "Los guantes cruzados en la guardia y los golpes son de la animación: no se ha tocado la postura.", ""]
cab = f"{'acción':24}" + "".join(f" | {t:>15}" for _, t in COLUMNAS)
out += [cab, "-" * len(cab)]
for accion in sorted(despues):
    fila = f"{accion:24}"
    for k, _ in COLUMNAS:
        a, d = antes.get(accion, {}).get(k, 0.0), despues[accion].get(k, 0.0)
        fila += f" | {a:5.1f} -> {d:5.1f}  "
    out.append(fila)
out.append("")
for k, t in COLUMNAS:
    a = max(v.get(k, 0.0) for v in antes.values())
    d = max(v.get(k, 0.0) for v in despues.values())
    out.append(f"  peor {t:15}: {a:4.1f} cm -> {d:4.1f} cm")
texto = "\n".join(out) + "\n"
open(os.path.join(TR, "ropa_v2_choques_antes_despues.txt"), "w", encoding="utf-8").write(texto)
print(texto)

# ---------------------------------------------------------------- v2 / B / C (si están)
VARS = [("v2", "fase3_resumen.txt"), ("B", "fase3_resumen_b.txt"), ("C", "fase3_resumen_c.txt")]
VARS = [(n, leer(os.path.join(TR, f))) for n, f in VARS if os.path.exists(os.path.join(TR, f))]
if len(VARS) > 1:
    out = ["CHOQUES v2 / B / C (máximo en cm de toda la acción; 0 = sin choque > 0,2 cm)",
           "B: guantes con pesos (soldados al brazo), sin Mask -> 'hueco' no aplica.",
           "C: guantes de B rígidos (hueso Hand), Mask de manos, pies y piel bajo el pantalón.",
           "Guantes de B y C: medida con la superficie (BVH); v2: piezas convexas (exacta).", ""]
    cab = f"{'acción':24}" + "".join(f" | {t:>17}" for _, t in COLUMNAS)
    out += [cab, "-" * len(cab)]
    acciones = sorted(set().union(*(d.keys() for _, d in VARS)))
    for accion in acciones:
        fila = f"{accion:24}"
        for k, _ in COLUMNAS:
            fila += " | " + " ".join(f"{d.get(accion, {}).get(k, 0.0):5.1f}" for _, d in VARS)
        out.append(fila)
    out.append(f"{'':24}" + "".join(f" | {' '.join(f'{n:>5}' for n, _ in VARS)}" for _ in COLUMNAS))
    out.append("")
    for k, t in COLUMNAS:
        out.append(f"  peor {t:15}: " + "   ".join(
            f"{n} {max(v.get(k, 0.0) for v in d.values()):4.1f} cm" for n, d in VARS))
    texto = "\n".join(out) + "\n"
    open(os.path.join(TR, "choques_v2_b_c.txt"), "w", encoding="utf-8").write(texto)
    print(texto)
