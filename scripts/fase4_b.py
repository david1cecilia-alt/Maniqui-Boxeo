"""Fase 4 sobre el modelo principal (B): guardia corregida en todas las acciones -> <acción>_v2.

Ver trabajo/fase4_propuesta.md. Las acciones originales no se tocan.
- Barbilla al pecho: Neck +NECK_DEG y Head +HEAD_DEG de flexión (hacia la cara) en todos los fotogramas.
- Guardia: cada guante a un lado de la cara (sin taparla ni cruzarse), por delante de los
  pómulos; objetivos PEGADOS A LA CABEZA (siguen a la cabeza aunque se mueva). La distancia
  lateral se calibra en guardia fot. 1 para dejar AIRE_GUARDIA de aire entre guante y cara.
- Codos cerrados: el polo del IK (dirección del codo) va abajo, delante y cerca del pecho.
  La flexión del codo se limita a FLEX_MAX (más cerrada, la malla del codo se estira x2).
- IK analítico de 2 huesos (Arm, ForeArm) + mano con la muñeca recta en guardia.
- Brazo que golpea (o que bloquea): se suelta hacia la animación original cuando su mano se
  separa más de UMBRAL_SUELTA de su posición inicial respecto a la cabeza, con rampa suave de
  RAMPA fotogramas antes y después. Suelto = objetivo y polo del IK = muñeca y codo originales,
  así que en el impacto el brazo es el de Mixamo.
- Seguridad: en cada fotograma, si un guante queda a menos de MARGEN de la cabeza (o dentro),
  se aparta de la cabeza y se recalcula.
- Primer y último fotograma iguales: los últimos FINAL fotogramas se llevan suavemente al primero.
  Excepción: en las acciones que DESPLAZAN (paso_atras) solo coincide la pose; la traslación de
  la cadera no se toca y el muñeco acaba desplazado.
- bloqueo (ahora reaccion_golpe) y rueda no tienen _v2: fase5_b.py crea a mano los bloqueos y
  las ruedas (y arregla los pies de las esquivas). Ejecutar fase5_b.py después de este script.
Guarda trabajo/boxeador.blend y trabajo/fase4_resumen.txt.

Uso:
  blender.exe --background --python scripts/fase4_b.py
"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.kdtree import KDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun as C  # noqa: E402

BLEND = os.path.join(C.TRABAJO, "boxeador.blend")
P = "mixamorig:"
NECK_DEG, HEAD_DEG = 6.0, 10.0
DELANTE, ALTURA = 0.13, -0.03      # centro del guante respecto al centro de la cabeza (m)
AIRE_GUARDIA = 0.028               # aire guante-cara en la guardia (objetivo 2-3 cm)
MARGEN_GUARDIA, MARGEN_GOLPE = 0.022, 0.008
UMBRAL_SUELTA, RAMPA, FINAL = 0.12, 5, 6
FLEX_MAX = 140.0                   # flexión máxima del codo en el IK (grados)
LADOS = {"Left": 1.0, "Right": -1.0}   # +X en reposo = izquierda del boxeador
# qué brazos se pueden soltar: golpes -> solo el que golpea; bloqueo -> los dos; el resto -> ninguno
GOLPES = {"jab", "recto", "crochet_adelantado", "crochet_trasero", "crochet_trasero_cuerpo",
          "gancho_adelantado_cuerpo", "gancho_trasero_cuerpo"}
SUELTA_LIBRE = {"bloqueo"}
DESPLAZA = {"paso_atras"}          # acaban desplazadas: la cadera no vuelve al sitio
# sin _v2: la reacción a un golpe de Mixamo, la rueda antigua y las acciones hechas a mano (fase5_b.py)
SIN_V2 = {"bloqueo", "reaccion_golpe", "rueda"}

out = []


def p(*a):
    out.append(" ".join(str(x) for x in a))
    print(out[-1])


bpy.ops.wm.open_mainfile(filepath=BLEND)
esc = bpy.context.scene
arm = bpy.data.objects["Boxeador"]
cuerpo = bpy.data.objects["Cuerpo"]
assert arm.matrix_world == Matrix(), "se espera el esqueleto con las transformaciones aplicadas"
for a in [a for a in bpy.data.actions if a.name.endswith("_v2")]:
    bpy.data.actions.remove(a)
ORIGINALES = sorted(a.name for a in bpy.data.actions
                    if a.name not in SIN_V2 and not a.name.startswith(("bloqueo_", "rueda_", "paso_adelante", "paso_lateral_")))
pb = {n.split(":")[-1]: b for n, b in arm.pose.bones.items()}
REST = {n.split(":")[-1]: b.matrix_local.copy() for n, b in arm.data.bones.items()}
REST_INV = {k: m.inverted() for k, m in REST.items()}


def q(m):
    return m.to_3x3().normalized().to_quaternion()


def eje_y(m):
    return m.col[1].xyz.normalized()


def np_m(m):
    return np.array(m)


# ---------------------------------------------------------------- datos de reposo
nom = {g.index: g.name.split(":")[-1] for g in cuerpo.vertex_groups}
cab_idx = [v.index for v in cuerpo.data.vertices if any(nom[e.group] == "Head" and e.weight > 0.5 for e in v.groups)]
cab_co = np.array([cuerpo.data.vertices[i].co[:] for i in cab_idx])
cab_n = np.array([cuerpo.data.vertices[i].normal[:] for i in cab_idx])
cab_loc = (cab_co - np.array(REST["Head"].translation)) @ np.array(REST["Head"].to_3x3())   # local del hueso
cab_nloc = cab_n @ np.array(REST["Head"].to_3x3())
KD = KDTree(len(cab_loc))
for i, c in enumerate(cab_loc):
    KD.insert(c, i)
KD.balance()
CARA = cab_nloc @ np.array(REST["Head"].to_3x3().inverted() @ Vector((0, -1, 0))) > 0.35   # mira hacia delante


def puntos_guante(lado):
    """Puntos del guante (1 de cada 3) en local de Hand o de ForeArm según el hueso dominante."""
    g = bpy.data.objects["Guante_" + lado]
    nm = {x.index: x.name.split(":")[-1] for x in g.vertex_groups}
    loc_h, loc_f = [], []
    for v in list(g.data.vertices)[::3]:
        wh = sum(e.weight for e in v.groups if nm[e.group] == lado + "Hand")
        wf = sum(e.weight for e in v.groups if nm[e.group] == lado + "ForeArm")
        co = Vector(v.co)
        if wh >= wf:
            loc_h.append(REST_INV[lado + "Hand"] @ co)
        else:
            loc_f.append(REST_INV[lado + "ForeArm"] @ co)
    return np.array(loc_h), np.array(loc_f)


GPTS = {lado: puntos_guante(lado) for lado in LADOS}
CENTRO_PUNO = {lado: Vector(GPTS[lado][0].mean(axis=0)) for lado in LADOS}   # centro de la manopla (local Hand)
REL_MANO = {lado: q(REST[lado + "ForeArm"]).inverted() @ q(REST[lado + "Hand"]) for lado in LADOS}


def transformar(M, pts):
    A = np_m(M)
    return pts @ A[:3, :3].T + A[:3, 3]


def guante_mundo(lado, MF, MH):
    lh, lf = GPTS[lado]
    partes = [transformar(MH, lh)]
    if len(lf):
        partes.append(transformar(MF, lf))
    return np.vstack(partes)


def hueco(pts, MHead):
    """Distancia con signo (m) del guante a la cabeza (negativo = dentro)."""
    ql = (pts - np.array(MHead.translation)) @ np_m(MHead.to_3x3().normalized())   # local del hueso en pose
    cen = cab_loc.mean(axis=0)
    rad = np.linalg.norm(cab_loc - cen, axis=1).max()
    cerca = np.linalg.norm(ql - cen, axis=1) < rad + 0.08
    mejor = 1.0
    for x in ql[cerca]:
        co, i, d = KD.find(x)
        s = d if np.dot(x - np.array(co), cab_nloc[i]) >= 0 else -d
        mejor = min(mejor, s)
    return mejor


# ---------------------------------------------------------------- utilidades de pose
def poner(nombre):
    a = bpy.data.actions[nombre]
    arm.animation_data.action = a
    if arm.animation_data.action_slot is None or arm.animation_data.action_slot.identifier not in [s.identifier for s in a.slots]:
        arm.animation_data.action_slot = a.slots[0]
    return a


def marco(nombre, M):
    """Delante, arriba y lateral (izquierda) del hueso en pose, a partir de su reposo."""
    R = q(M) @ q(REST[nombre]).inverted()
    return R @ Vector((0, -1, 0)), R @ Vector((0, 0, 1)), R @ Vector((1, 0, 0))


def datos_fk():
    d = {}
    for lado in LADOS:
        d[lado] = dict(muneca=pb[lado + "Hand"].head.copy(), codo=pb[lado + "ForeArm"].head.copy(),
                       rot_mano=q(pb[lado + "Hand"].matrix), MA=pb[lado + "Arm"].matrix.copy(),
                       MF=pb[lado + "ForeArm"].matrix.copy(), MH=pb[lado + "Hand"].matrix.copy())
    d["neck"] = pb["Neck"].matrix.copy()
    d["head"] = pb["Head"].matrix.copy()
    d["head_local"] = {lado: pb["Head"].matrix.inverted() @ pb[lado + "Hand"].head for lado in LADOS}
    return d


def rot_hacia(eje, dest, rot):
    return eje.rotation_difference(dest) @ rot


def barbilla(fk):
    """Flexiona Neck y Head hacia la cara (se aplica a la pose original guardada)."""
    for n, grados, M0 in (("Neck", NECK_DEG, fk["neck"]), ("Head", HEAD_DEG, None)):
        M = M0 if M0 is not None else pb["Head"].matrix.copy()
        cara, arriba, _ = marco(n, M)
        eje = arriba.cross(cara).normalized()
        R = Quaternion(eje, math.radians(grados))
        pb[n].matrix = Matrix.LocRotScale(M.translation, R @ q(M), None)
        bpy.context.view_layer.update()


def ik(lado, fk, T, polo, w):
    """IK de 2 huesos. Devuelve las matrices nuevas de Arm, ForeArm y Hand y la rotación de guardia."""
    MA0, MF0, MH0 = fk[lado]["MA"], fk[lado]["MF"], fk[lado]["MH"]
    S = MA0.translation.copy()
    a = (MF0.translation - S).length
    b = (MH0.translation - MF0.translation).length
    dvec = T - S
    # flexión de codo como mucho FLEX_MAX (más cerrado la malla del codo se estira y hace pico)
    d_min = math.sqrt(a * a + b * b - 2 * a * b * math.cos(math.radians(180 - FLEX_MAX)))
    dist = min(max(dvec.length, d_min), a + b - 1e-4)
    u = dvec.normalized()
    T2 = S + u * dist
    cosA = (a * a + dist * dist - b * b) / (2 * a * dist)
    sinA = math.sqrt(max(0.0, 1 - cosA * cosA))
    v = polo - S
    v = v - u * v.dot(u)
    if v.length < 1e-6:
        v = Vector((0, 0, -1)) - u * u.z
    v.normalize()
    E = S + u * a * cosA + v * a * sinA
    MA = Matrix.LocRotScale(S, rot_hacia(eje_y(MA0), (E - S).normalized(), q(MA0)), None)
    MFc = MA @ (MA0.inverted() @ MF0)
    rotF = rot_hacia(eje_y(MFc), (T2 - E).normalized(), q(MFc))
    MF = Matrix.LocRotScale(E, rotF, None)
    rot_g = rotF @ REL_MANO[lado]
    rot_h = rot_g.slerp(fk[lado]["rot_mano"], w) if w > 0 else rot_g
    MH = Matrix.LocRotScale(T2, rot_h, None)
    return MA, MF, MH, rot_g


def objetivos(lado, lateral):
    """Centro del guante en guardia y polo del codo, pegados a la cabeza / al pecho (pose actual)."""
    s = LADOS[lado]
    MHd = pb["Head"].matrix
    cara, arriba, izq = marco("Head", MHd)
    centro = (pb["Head"].head + pb["HeadTop_End"].head) / 2
    gc = centro + izq * (s * lateral) + cara * DELANTE + arriba * ALTURA
    cara_t, arriba_t, izq_t = marco("Spine2", pb["Spine2"].matrix)
    polo = pb["Spine2"].head + cara_t * 0.28 - arriba_t * 0.30 + izq_t * (s * 0.10)
    return gc, polo, centro


def resolver(lado, fk, w, lateral, rot_prev, corregir=True):
    gc, polo_g, centro = objetivos(lado, lateral)
    rot = rot_prev
    empuje = Vector()
    for _ in range(3):
        T = (gc - rot @ CENTRO_PUNO[lado]).lerp(fk[lado]["muneca"], w) + empuje
        polo = polo_g.lerp(fk[lado]["codo"], w)
        MA, MF, MH, rot = ik(lado, fk, T, polo, w)
    hq, n_emp = hueco(guante_mundo(lado, MF, MH), pb["Head"].matrix), 0
    margen = MARGEN_GUARDIA if w < 0.5 else MARGEN_GOLPE
    while corregir and hq < margen and n_emp < 6:
        cg = Vector(guante_mundo(lado, MF, MH).mean(axis=0))
        dirc = (cg - centro).normalized()
        empuje += dirc * (margen - hq + 0.004)
        T = (gc - rot @ CENTRO_PUNO[lado]).lerp(fk[lado]["muneca"], w) + empuje
        MA, MF, MH, rot = ik(lado, fk, T, polo, w)
        hq = hueco(guante_mundo(lado, MF, MH), pb["Head"].matrix)
        n_emp += 1
    return MA, MF, MH, rot, hq, empuje.length


def aplicar(mats):
    for parte in ("Arm", "ForeArm", "Hand"):
        for lado, (MA, MF, MH) in mats.items():
            pb[lado + parte].matrix = {"Arm": MA, "ForeArm": MF, "Hand": MH}[parte]
        bpy.context.view_layer.update()


# ---------------------------------------------------------------- calibración en guardia fot. 1
poner("guardia")
esc.frame_set(1)
fk1 = datos_fk()
barbilla(fk1)
rot0 = {lado: q(fk1[lado]["MH"]) for lado in LADOS}


def hueco_guardia(lateral):
    res = []
    for lado in LADOS:
        _, MF, MH, _, hq, _ = resolver(lado, fk1, 0.0, lateral, rot0[lado], corregir=False)
        res.append(hq)
    return min(res)


lo, hi = 0.05, 0.30
for _ in range(14):
    mid = (lo + hi) / 2
    if hueco_guardia(mid) < AIRE_GUARDIA:
        lo = mid
    else:
        hi = mid
LATERAL = hi
p("=== FASE 4 (modelo B) ===")
p(f"  barbilla al pecho: Neck +{NECK_DEG:.0f}°, Head +{HEAD_DEG:.0f}° (total {NECK_DEG + HEAD_DEG:.0f}°)")
p(f"  guardia: centro de cada guante a ±{LATERAL * 100:.1f} cm del centro de la cabeza, {DELANTE * 100:.0f} cm"
  f" delante, {ALTURA * 100:+.0f} cm de altura -> aire guante-cara {hueco_guardia(LATERAL) * 100:.1f} cm (objetivo"
  f" {AIRE_GUARDIA * 100:.1f})")

# cara visible de frente en la guardia nueva (fot. 1)
mats = {}
for lado in LADOS:
    MA, MF, MH, _, _, _ = resolver(lado, fk1, 0.0, LATERAL, rot0[lado])
    mats[lado] = (MA, MF, MH)
gpts = np.vstack([guante_mundo(lado, mats[lado][1], mats[lado][2]) for lado in LADOS])
MHd = pb["Head"].matrix
cara_w = transformar(MHd @ REST_INV["Head"], cab_co[CARA])
cara_d, arriba_d, izq = marco("Head", MHd)
# vista de frente a la cara (hacia donde mira la cabeza): coordenadas (lateral, altura, profundidad)
B3 = np.array([izq, arriba_d, cara_d])
g2, c2 = gpts @ B3.T, cara_w @ B3.T
kd2 = KDTree(len(g2))
for i, g in enumerate(g2):
    kd2.insert((g[0], g[1], 0.0), i)
kd2.balance()
tapada = sum(1 for c in c2 if any(g2[i][2] > c[2] for _, i, _ in kd2.find_range((c[0], c[1], 0.0), 0.012)))
cg = {lado: Vector(guante_mundo(lado, mats[lado][1], mats[lado][2]).mean(axis=0)) for lado in LADOS}
sep = (cg["Left"] - cg["Right"]).dot(izq)
p(f"  cara vista de frente (desde donde mira la cabeza): {100 * (1 - tapada / len(c2)):.0f} % de la cara sin tapar por los guantes;"
  f" separación entre guantes {sep * 100:.1f} cm ({'sin cruzar' if sep > 0 else 'CRUZADOS'})")
codos = [(mats[l][1].translation - pb["Spine2"].head).dot(marco("Spine2", pb["Spine2"].matrix)[2]) * LADOS[l] for l in LADOS]
p(f"  codos (fot. 1): a {codos[0] * 100:.1f} / {codos[1] * 100:.1f} cm del eje del pecho hacia su lado")


# ---------------------------------------------------------------- hornear las acciones _v2
def curva_suelta(lejos):
    """lejos: {f: bool}. Peso 1 donde la mano va suelta, rampas suaves de RAMPA fotogramas."""
    fs = sorted(lejos)
    w = {f: 0.0 for f in fs}
    for f in fs:
        if lejos[f]:
            for g in range(f - RAMPA, f + RAMPA + 1):
                if g in w:
                    t = 1 - abs(g - f) / RAMPA
                    w[g] = max(w[g], t * t * (3 - 2 * t))
    return w


def clave(b, f, previo):
    if b.rotation_mode == "QUATERNION":
        qq = b.rotation_quaternion.copy()
        if previo is not None and qq.dot(previo) < 0:
            qq.negate()
            b.rotation_quaternion = qq
        b.keyframe_insert("rotation_quaternion", frame=f, group=b.name)
        return qq
    b.keyframe_insert("rotation_euler", frame=f, group=b.name)
    return None


HUESOS_V2 = ["Neck", "Head"] + [l + x for l in LADOS for x in ("Arm", "ForeArm", "Hand")]
p("\n  acción                   fot.  suelta (brazo: fotogramas con peso > 0)        aire mín. guante-cabeza   empuje máx.")
for nombre in ORIGINALES:
    a = poner(nombre)
    f0, f1 = (int(x) for x in a.frame_range)
    fk = {}
    for f in range(f0, f1 + 1):
        esc.frame_set(f)
        fk[f] = datos_fk()
    pesos = {}
    desp = {lado: {f: (fk[f]["head_local"][lado] - fk[f0]["head_local"][lado]).length for f in fk} for lado in LADOS}
    golpea = max(LADOS, key=lambda l: max(desp[l].values()))
    for lado in LADOS:
        puede = nombre in SUELTA_LIBRE or (nombre in GOLPES and lado == golpea)
        pesos[lado] = curva_suelta({f: puede and desp[lado][f] > UMBRAL_SUELTA for f in fk})
    a2 = a.copy()
    a2.name = nombre + "_v2"
    a2.use_fake_user = True
    poner(a2.name)
    previo = {b: None for b in HUESOS_V2}
    rot_prev = {lado: q(fk[f0][lado]["MH"]) for lado in LADOS}
    aire = {lado: 1.0 for lado in LADOS}
    emp_max = 0.0
    for f in range(f0, f1 + 1):
        esc.frame_set(f)
        barbilla(fk[f])
        mats = {}
        for lado in LADOS:
            MA, MF, MH, rot, hq, emp = resolver(lado, fk[f], pesos[lado][f], LATERAL, rot_prev[lado])
            rot_prev[lado] = rot
            mats[lado] = (MA, MF, MH)
            aire[lado] = min(aire[lado], hq)
            emp_max = max(emp_max, emp)
        aplicar(mats)
        for b in HUESOS_V2:
            previo[b] = clave(pb[b], f, previo[b])
    # primer y último fotograma iguales: rampa suave en los últimos FINAL fotogramas (todas las curvas)
    por_hueso = {}
    for fc in a2.fcurves:
        por_hueso.setdefault(fc.data_path, []).append(fc)
    for ruta, fcs in por_hueso.items():
        if nombre in DESPLAZA and ruta.endswith('Hips"].location'):
            continue
        fcs.sort(key=lambda c: c.array_index)
        v0 = [fc.evaluate(f0) for fc in fcs]
        v1 = [fc.evaluate(f1) for fc in fcs]
        if ruta.endswith("rotation_quaternion") and sum(x * y for x, y in zip(v0, v1)) < 0:
            v0 = [-x for x in v0]
        for fc, x0, x1 in zip(fcs, v0, v1):
            for f in range(f1 - FINAL, f1 + 1):
                t = (f - (f1 - FINAL)) / FINAL
                t = t * t * (3 - 2 * t)
                val = fc.evaluate(f) + t * (x0 - x1)
                kp = next((k for k in fc.keyframe_points if abs(k.co.x - f) < 1e-3), None)
                if kp is None:
                    fc.keyframe_points.insert(f, val)
                else:
                    kp.co.y = val
                    kp.handle_left.y = kp.handle_right.y = val
            fc.update()
    sueltas = []
    for lado in LADOS:
        fs = [f for f, w in pesos[lado].items() if w > 0]
        if fs:
            sueltas.append(f"{lado[0]} {min(fs)}-{max(fs)}")
    p(f"  {a2.name:26} {f1:3}  {', '.join(sueltas) or 'ninguno (guardia todo el tiempo)':46} "
      f"{min(aire.values()) * 100:6.1f} cm               {emp_max * 100:5.1f} cm")

poner("guardia_v2")
esc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
p(f"\n  {len(ORIGINALES)} acciones _v2 nuevas (las originales se conservan). GUARDADO {os.path.relpath(BLEND, C.RAIZ)}")
with open(os.path.join(C.TRABAJO, "fase4_resumen.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out) + "\n")
