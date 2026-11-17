"""Fase 1 – analiza trabajo/diagnostico.json (no necesita Blender, solo Python 3).

Uso:
  python scripts/fase1_analizar.py   (o el python.exe que trae Blender)
Escribe trabajo/diagnostico_resumen.txt y trabajo/fotogramas_clave.json
"""
import json
import math
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TR = os.path.join(RAIZ, "trabajo")
D = json.load(open(os.path.join(TR, "diagnostico.json"), encoding="utf-8"))
out = []


def p(*a):
    out.append(" ".join(str(x) for x in a))


def sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def dist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def corto(n):
    return n.split(":")[-1]


ref = D["guardia"]
ref_h = [corto(h) for h in ref["huesos"]]

# ---------- 1. guardia ----------
p("=== 1. GUARDIA (", ref["archivo"], ") ===")
p("Armature:", ref["arm_nombre"], "| huesos:", len(ref_h))
p("Huesos:", ", ".join(ref_h))
dedos = [h for h in ref_h if any(k in h for k in ("Thumb", "Index", "Middle", "Ring", "Pinky"))]
p("Huesos de dedos:", dedos if dedos else "NINGUNO (confirmado)")
for m in ref["mallas"]:
    p(f"Malla {m['nombre']}: {m['vertices']} vért, {m['caras']} caras, materiales={m['materiales']}, "
      f"grupos de vértices={len(m['grupos_vertices'])}")
    p("   grupos:", ", ".join(corto(g) for g in m["grupos_vertices"]))
fig = D["figura"]
p("BoxeoFigura.fbx: huesos", len(fig["huesos"]), "| mallas",
  [(m["nombre"], m["vertices"]) for m in fig["mallas"]], "| acciones", [a["nombre"] for a in fig["acciones"]])

# ---------- 2. tabla ----------
p("\n=== 2. ACCIONES ===")
p(f"{'nombre':24} {'acción':30} {'fps':>4} {'fot':>4} {'seg':>6}  esqueleto=guardia  malla")
for n, d in D.items():
    if n == "figura":
        continue
    mismo_nombres = d["huesos"] == ref["huesos"]
    mismo_jer = d["jerarquia"] == ref["jerarquia"]
    dmax = max(dist(d["reposo"][b], ref["reposo"][b]) for b in ref["reposo"]) if mismo_nombres else None
    ok = mismo_nombres and mismo_jer and dmax < 1e-3
    malla = "; ".join(f"{m['vertices']}v" for m in d["mallas"])
    p(f"{n:24} {d['accion']:30} {d['fps']:>4.0f} {d['n_fotogramas']:>4} {d['duracion_s']:>6.2f}  "
      f"{'SÍ' if ok else 'NO'} (nombres={mismo_nombres}, jerarquía={mismo_jer}, dif.reposo={dmax and round(dmax, 5)})  {malla}")
p("Nº de acciones en cada FBX:", {n: len(d["acciones"]) for n, d in D.items()})

# orientación: hacia dónde mira el muñeco (dedo del pie - pie)
# en reposo: frente = (hombro izq - hombro der) x arriba
rp = {corto(k): v for k, v in ref["reposo"].items()}
lr = sub(rp["LeftArm"], rp["RightArm"])
fwd = [lr[1] * 1 - lr[2] * 0, lr[2] * 0 - lr[0] * 1, 0]  # lr x (0,0,1)
eje_frente = 1 if abs(fwd[1]) > abs(fwd[0]) else 0
signo = 1 if fwd[eje_frente] > 0 else -1
p(f"\nOrientación: mira hacia {'+' if signo > 0 else '-'}{'XY'[eje_frente]} (Z arriba)")


def adelante(v):  # coordenada "hacia delante"
    return v[eje_frente] * signo


def lateral(v):
    return v[1 - eje_frente]


# ---------- 3. 5 vs 6 ----------
p("\n=== 3. GANCHO ADELANTADO AL CUERPO vs GANCHO TRASERO AL CUERPO ===")
A, Bd = D["gancho_adelantado_cuerpo"], D["gancho_trasero_cuerpo"]
dif_rot = max(abs(x - y) for b in A["rot_local"] for fa, fb in zip(A["rot_local"][b], Bd["rot_local"][b]) for x, y in zip(fa, fb))
p("Diferencia máxima de rotaciones locales (cuaternión):", round(dif_rot, 5),
  "=> IDÉNTICAS" if dif_rot < 1e-3 else "=> distintas")


def espejo_err(a, b):
    """Error medio entre a y el espejo lateral de b (izq<->der, lateral -> -lateral)."""
    err, n = 0, 0
    for k in a["pistas"]:
        k2 = k.replace("Left", "TMP").replace("Right", "Left").replace("TMP", "Right")
        for pa, pb in zip(a["pistas"][k], b["pistas"][k2]):
            pb2 = list(pb)
            pb2[1 - eje_frente] = 2 * a["pistas"]["Hips"][0][1 - eje_frente] - pb2[1 - eje_frente]
            err += dist(pa, pb2); n += 1
    return err / n


def directo_err(a, b):
    err, n = 0, 0
    for k in a["pistas"]:
        for pa, pb in zip(a["pistas"][k], b["pistas"][k]):
            err += dist(pa, pb); n += 1
    return err / n


p("Error medio posiciones directo:", round(directo_err(A, Bd), 4), "m | con espejo:", round(espejo_err(A, Bd), 4), "m")


def pie_delantero(d, f=0):
    return "izquierdo" if adelante(d["pistas"]["LeftFoot"][f]) > adelante(d["pistas"]["RightFoot"][f]) else "derecho"


def mano_golpe(d):
    h0 = {k: d["pistas"][k][0] for k in ("LeftHand", "RightHand")}
    best = {k: max(range(len(d["pistas"][k])), key=lambda i: dist(d["pistas"][k][i], h0[k])) for k in h0}
    k = max(h0, key=lambda k: dist(d["pistas"][k][best[k]], h0[k]))
    return k, best[k], dist(d["pistas"][k][best[k]], h0[k])


for n in ("guardia", "gancho_adelantado_cuerpo", "gancho_trasero_cuerpo"):
    d = D[n]
    extra = ""
    if n != "guardia":
        k, f, dd = mano_golpe(d)
        extra = f", golpea con {'IZQ' if 'Left' in k else 'DER'} (máx fot. {f + d['frame_ini']}, {dd:.2f} m)"
    p(f"  {n}: pie delantero = {pie_delantero(d)}{extra}")

# ---------- 4. esquiva retrocediendo ----------
p("\n=== 4. ESQUIVA RETROCEDIENDO como 'paso atrás' ===")
for n in ("esquiva_retrocediendo", "esquiva_avanzando"):
    d = D[n]
    t = d["pistas"]
    p(f"-- {n} ({d['n_fotogramas']} fot.) pie delantero al inicio: {pie_delantero(d)}")
    for k in ("LeftFoot", "RightFoot", "Hips"):
        serie = [adelante(v) for v in t[k]]
        p(f"   {k:9} adelante: ini {serie[0]:+.3f} min {min(serie):+.3f}(f{serie.index(min(serie))}) "
          f"max {max(serie):+.3f}(f{serie.index(max(serie))}) fin {serie[-1]:+.3f}")
    # cuándo se mueve cada pie (velocidad > umbral)
    for k in ("LeftFoot", "RightFoot"):
        mov = [i for i in range(1, len(t[k])) if dist(t[k][i], t[k][i - 1]) > 0.006]
        tramos = []
        for i in mov:
            if tramos and i - tramos[-1][1] <= 2:
                tramos[-1][1] = i
            else:
                tramos.append([i, i])
        p(f"   {k} se mueve en fotogramas: {tramos}")
    hz = [t["Hips"][i][2] for i in range(len(t["Hips"]))]
    p(f"   cadera altura: ini {hz[0]:.3f} min {min(hz):.3f}(f{hz.index(min(hz))}) fin {hz[-1]:.3f}")
    gm = []
    for i in range(len(t["Head"])):
        cab = t["Head"][i][2]
        gm.append(min(t["LeftHand"][i][2], t["RightHand"][i][2]) - cab)
    p(f"   mano más baja respecto a la cabeza: peor {min(gm):+.3f} m (f{gm.index(min(gm))}), inicio {gm[0]:+.3f}")
    hl = [lateral(t['Hips'][i]) for i in range(len(t['Hips']))]
    p(f"   cadera lateral: ini {hl[0]:+.3f} min {min(hl):+.3f} max {max(hl):+.3f} fin {hl[-1]:+.3f}")


# ---------- 5. guardias ----------
p("\n=== 5. GUARDIA vs GUARDIA_ALT (medias de toda la animación) ===")


def metricas(d):
    t = d["pistas"]
    n = len(t["Head"])
    r = {"mano_vs_barbilla_z": 0, "mano_sep_lateral": 0, "codo_sep_lateral": 0, "codo_altura_vs_mano": 0,
         "mano_delante_cara": 0, "cabeza_inclinada_grados": 0, "cabeza_adelantada": 0}
    for i in range(n):
        neck, head, top = t["Neck"][i], t["Head"][i], t["HeadTop_End"][i]
        barbilla_z = head[2] - 0.03  # aprox: base del cráneo un poco por encima de la barbilla
        sp = t["Spine2"][i]
        for L in ("Left", "Right"):
            m, c = t[L + "Hand"][i], t[L + "ForeArm"][i]
            r["mano_vs_barbilla_z"] += (m[2] - barbilla_z) / (2 * n)
            r["mano_sep_lateral"] += abs(lateral(m) - lateral(sp)) / (2 * n)
            r["codo_sep_lateral"] += abs(lateral(c) - lateral(sp)) / (2 * n)
            r["codo_altura_vs_mano"] += (c[2] - m[2]) / (2 * n)
            r["mano_delante_cara"] += (adelante(m) - adelante(head)) / (2 * n)
        v = sub(top, neck)
        ang = math.degrees(math.atan2(adelante(v), v[2]))
        r["cabeza_inclinada_grados"] += ang / n
        r["cabeza_adelantada"] += (adelante(head) - adelante(t["Hips"][i])) / n
    r["pie_delantero"] = pie_delantero(d)
    r["cadera_z"] = sum(v[2] for v in t["Hips"]) / n
    return r


mg = {n: metricas(D[n]) for n in ("guardia", "guardia_alt")}
for k in mg["guardia"]:
    a, b = mg["guardia"][k], mg["guardia_alt"][k]
    if isinstance(a, float):
        p(f"  {k:26} guardia {a:+.3f}   guardia_alt {b:+.3f}")
    else:
        p(f"  {k:26} guardia {a}   guardia_alt {b}")
p("  (mano_vs_barbilla_z >0 = manos por encima de la barbilla; codo_sep_lateral menor = codos más cerrados;"
  " cabeza_inclinada >0 = cabeza hacia delante/abajo)")

# ---------- 6. fotogramas de máximo movimiento ----------
clave = {}
for n in D:
    if n in ("figura", "guardia", "guardia_alt"):
        continue
    k, f, dd = mano_golpe(D[n])
    clave[n] = {"fotograma": f + D[n]["frame_ini"], "mano": k, "desplazamiento_m": round(dd, 3)}
p("\n=== 6. FOTOGRAMA DE MÁXIMO MOVIMIENTO (mano que más se aleja de su posición inicial) ===")
for n, v in clave.items():
    p(f"  {n:24} fot. {v['fotograma']:>3}  mano {v['mano']:9}  {v['desplazamiento_m']} m  pie delantero: {pie_delantero(D[n])}")
json.dump({"clave": clave, "eje_frente": eje_frente, "signo": signo},
          open(os.path.join(TR, "fotogramas_clave.json"), "w"), indent=1)

txt = "\n".join(out)
open(os.path.join(TR, "diagnostico_resumen.txt"), "w", encoding="utf-8").write(txt)
print(txt)
