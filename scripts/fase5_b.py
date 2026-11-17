"""Fase 5 sobre el modelo principal (B): correcciones de David tras revisar las _v2.

Ejecutar DESPUÉS de fase4_b.py (que rehace las _v2 y deja paso_atras_v2 desplazado al final).
1. La acción `bloqueo` de Mixamo es una reacción a un golpe: se renombra a `reaccion_golpe`
   (sin _v2) y se borran bloqueo_v2, rueda y rueda_v2.
2. Bloqueos hechos a mano desde guardia_v2 (fot. 1) y volviendo a ella (28 fot., 0,9 s):
   bloqueo_cerrado, bloqueo_alto_izq/_der (guante a la sien, antebrazo vertical, codo algo
   arriba), bloqueo_bajo_izq/_der (codo pegado a las costillas, giro y encogimiento hacia ese
   lado). Izquierda y derecha se definen a mano (sin espejo: los pies no cambian).
3. Rueda hecha a mano (37 fot., 1,2 s): rueda_der y rueda_izq. La cabeza dibuja una "U" (sube
   en el lado del nombre); cadera y tronco giran y se inclinan, rodillas un poco flexionadas,
   guantes en guardia todo el tiempo.
4. Esquivas _v2: los pies resbalaban bajo una cadera fija (sin desplazamiento X/Y): parecía
   que flotaba. Ahora los pies van fijos en el suelo con IK (suela en Z=0) donde están en el
   fot. 1 de la esquiva (la postura de Mixamo va con su tronco, girado ~45° respecto a la
   guardia) y dan un paso real: el pie de atrás hacia atrás (retrocediendo) o el de delante
   hacia delante (avanzando), y vuelven al final. La cadera acompaña medio paso.
Todas: pies con IK analítico (fijos en el suelo), brazos con IK analítico de 2 huesos y
seguridad guante-cabeza (si un guante se mete en la cabeza se aparta y se recalcula).
Guarda trabajo/boxeador.blend y trabajo/fase5_resumen.txt.

Uso:
  blender.exe --background --python scripts/fase5_b.py
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
LADOS = {"Left": 1.0, "Right": -1.0}   # +X = izquierda del boxeador
NOMBRE_LADO = {"Left": "izq", "Right": "der"}
FLEX_MAX = 150.0        # flexión máxima del codo en los bloqueos (en la guardia de la Fase 4: 140)
MARGEN = 0.006          # aire mínimo guante-cabeza (bloqueos: guantes pegados)
X = Vector((1, 0, 0))   # izquierda del boxeador
DELANTE = Vector((0, -1, 0))

out = []


def p(*a):
    out.append(" ".join(str(x) for x in a))
    print(out[-1])


bpy.ops.wm.open_mainfile(filepath=BLEND)
esc = bpy.context.scene
arm = bpy.data.objects["Boxeador"]
cuerpo = bpy.data.objects["Cuerpo"]
assert arm.matrix_world == Matrix(), "se espera el esqueleto con las transformaciones aplicadas"
pb = {n.split(":")[-1]: b for n, b in arm.pose.bones.items()}
REST = {n.split(":")[-1]: b.matrix_local.copy() for n, b in arm.data.bones.items()}
REST_INV = {k: m.inverted() for k, m in REST.items()}
assert all(b.rotation_mode == "QUATERNION" for b in pb.values())


def q(m):
    return m.to_3x3().normalized().to_quaternion()


def eje_y(m):
    return m.col[1].xyz.normalized()


def np_m(m):
    return np.array(m)


def upd():
    bpy.context.view_layer.update()


def marco(nombre, M=None):
    """Delante, arriba e izquierda del hueso en pose, a partir de su reposo."""
    M = pb[nombre].matrix if M is None else M
    R = q(M) @ q(REST[nombre]).inverted()
    return R @ Vector((0, -1, 0)), R @ Vector((0, 0, 1)), R @ Vector((1, 0, 0))


def poner(nombre):
    a = bpy.data.actions[nombre]
    arm.animation_data.action = a
    if arm.animation_data.action_slot is None or arm.animation_data.action_slot.identifier not in [s.identifier for s in a.slots]:
        arm.animation_data.action_slot = a.slots[0]
    return a


# ---------------------------------------------------------------- 1. limpieza de acciones
p("=== FASE 5 (modelo B) ===")
acc = bpy.data.actions
if "bloqueo" in acc and "reaccion_golpe" not in acc:
    acc["bloqueo"].name = "reaccion_golpe"
    p("  bloqueo (Mixamo) -> reaccion_golpe (sin _v2)")
for n in [a.name for a in acc if a.name in ("bloqueo", "bloqueo_v2", "rueda", "rueda_v2", "reaccion_golpe_v2")
          or a.name.startswith(("bloqueo_", "rueda_"))]:
    acc.remove(acc[n])
    p(f"  borrada {n}")

# ---------------------------------------------------------------- cabeza y guantes (como en la Fase 4)
nom = {g.index: g.name.split(":")[-1] for g in cuerpo.vertex_groups}
cab_idx = [v.index for v in cuerpo.data.vertices if any(nom[e.group] == "Head" and e.weight > 0.5 for e in v.groups)]
cab_co = np.array([cuerpo.data.vertices[i].co[:] for i in cab_idx])
cab_n = np.array([cuerpo.data.vertices[i].normal[:] for i in cab_idx])
cab_loc = (cab_co - np.array(REST["Head"].translation)) @ np.array(REST["Head"].to_3x3())
cab_nloc = cab_n @ np.array(REST["Head"].to_3x3())
KD = KDTree(len(cab_loc))
for i, c in enumerate(cab_loc):
    KD.insert(c, i)
KD.balance()
CAB_CEN = cab_loc.mean(axis=0)
CAB_RAD = np.linalg.norm(cab_loc - CAB_CEN, axis=1).max()


def puntos_guante(lado):
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
CENTRO_PUNO = {lado: Vector(GPTS[lado][0].mean(axis=0)) for lado in LADOS}
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
    ql = (pts - np.array(MHead.translation)) @ np_m(MHead.to_3x3().normalized())
    cerca = np.linalg.norm(ql - CAB_CEN, axis=1) < CAB_RAD + 0.08
    mejor = 1.0
    for x in ql[cerca]:
        co, i, d = KD.find(x)
        s = d if np.dot(x - np.array(co), cab_nloc[i]) >= 0 else -d
        mejor = min(mejor, s)
    return mejor


def hueco_guantes():
    a = guante_mundo("Left", pb["LeftForeArm"].matrix, pb["LeftHand"].matrix)
    b = guante_mundo("Right", pb["RightForeArm"].matrix, pb["RightHand"].matrix)
    kd = KDTree(len(b))
    for i, x in enumerate(b):
        kd.insert(x, i)
    kd.balance()
    return min(kd.find(x)[2] for x in a)


# ---------------------------------------------------------------- 2. pose base: guardia_v2 fot. 1
poner("guardia_v2")
esc.frame_set(1)
BASE = {n: (b.location.copy(), b.rotation_quaternion.copy(), b.scale.copy()) for n, b in pb.items()}
M0 = {n: b.matrix.copy() for n, b in pb.items()}
LON = {n: (REST[h].translation - REST[n].translation).length
       for n, h in (("LeftArm", "LeftForeArm"), ("LeftForeArm", "LeftHand"), ("RightArm", "RightForeArm"),
                    ("RightForeArm", "RightHand"), ("LeftUpLeg", "LeftLeg"), ("LeftLeg", "LeftFoot"),
                    ("RightUpLeg", "RightLeg"), ("RightLeg", "RightFoot"))}

botas = bpy.data.objects["Botas"]
_nb = {g.index: g.name.split(":")[-1] for g in botas.vertex_groups}
BOTA_IZQ = np.array([sum(e.weight for e in v.groups if _nb[e.group].startswith("Left")) >
                     sum(e.weight for e in v.groups if _nb[e.group].startswith("Right")) for v in botas.data.vertices])


def suelas():
    """Z más baja (m) de la suela de cada pie con la pose actual."""
    dg = bpy.context.evaluated_depsgraph_get()
    oe = botas.evaluated_get(dg)
    m = oe.to_mesh()
    c = np.empty(len(m.vertices) * 3)
    m.vertices.foreach_get("co", c)
    oe.to_mesh_clear()
    c = c.reshape(-1, 3)
    return {"Left": float(c[BOTA_IZQ, 2].min()), "Right": float(c[~BOTA_IZQ, 2].min())}


# pies de la guardia con la suela en Z=0 (el pie gira igual que en la guardia: la suela queda a la
# misma distancia bajo el tobillo)
s0 = suelas()
PIE0 = {lado: M0[lado + "Foot"].translation - Vector((0, 0, s0[lado])) for lado in LADOS}
p(f"  guardia_v2 fot. 1: suela izq. {s0['Left'] * 100:+.1f} cm, der. {s0['Right'] * 100:+.1f} cm -> en los pies"
  " fijos se apoyan las dos en Z=0")


def referencia_piernas(M, pie):
    """Pose de referencia de las piernas: matrices, pie apoyado y polo de la rodilla (sigue al pie)."""
    ref = {}
    for lado in LADOS:
        S0, E0, T0 = (M[lado + n].translation for n in ("UpLeg", "Leg", "Foot"))
        u = (T0 - S0).normalized()
        k = (E0 - S0) - u * (E0 - S0).dot(u)
        ref[lado] = dict(M={n: M[lado + n].copy() for n in ("UpLeg", "Leg", "Foot")}, pie=pie[lado].copy(),
                         polo=E0 + k.normalized() * 0.5 - pie[lado])
    return ref


REF_GUARDIA = referencia_piernas(M0, PIE0)


def base_cuerpo():
    for n, b in pb.items():
        b.location, b.rotation_quaternion, b.scale = BASE[n]
    upd()


def coords(o, base, v, s=1.0):
    """Coordenadas (delante, arriba, lateral hacia su lado) de v respecto a o y su marco."""
    cara, arriba, izq = base
    d = v - o
    return Vector((d.dot(cara), d.dot(arriba), d.dot(izq) * s))


def punto(o, base, c, s=1.0):
    cara, arriba, izq = base
    return o + cara * c[0] + arriba * c[1] + izq * (c[2] * s)


def centro_cabeza():
    return (pb["Head"].head + pb["HeadTop_End"].head) / 2


# guardia: centro del guante en coordenadas de la cabeza y codo en coordenadas del pecho
base_cuerpo()
GUARDIA = {}
for lado, s in LADOS.items():
    gc = M0[lado + "Hand"] @ CENTRO_PUNO[lado]
    GUARDIA[lado] = (coords(centro_cabeza(), marco("Head"), gc, s),
                     coords(pb["Spine2"].head, marco("Spine2"), M0[lado + "ForeArm"].translation, s))
gl, cl = GUARDIA["Left"]
p(f"  guardia (izq.): guante a {gl.x * 100:.1f} cm delante, {gl.y * 100:+.1f} cm de altura y {gl.z * 100:.1f} cm"
  f" al lado del centro de la cabeza; codo {cl.x * 100:.1f} delante, {cl.y * 100:+.1f} alto, {cl.z * 100:.1f} cm al lado del pecho")


# ---------------------------------------------------------------- IK
def rot_hacia(eje, dest, rot):
    return eje.rotation_difference(dest) @ rot


def ik_brazo(lado, T, polo):
    MA0, MF0 = pb[lado + "Arm"].matrix.copy(), pb[lado + "ForeArm"].matrix.copy()
    S = MA0.translation.copy()
    a, b = LON[lado + "Arm"], LON[lado + "ForeArm"]
    dvec = T - S
    d_min = math.sqrt(a * a + b * b - 2 * a * b * math.cos(math.radians(180 - FLEX_MAX)))
    dist = min(max(dvec.length, d_min), a + b - 1e-4)
    u = dvec.normalized()
    T2 = S + u * dist
    cosA = (a * a + dist * dist - b * b) / (2 * a * dist)
    sinA = math.sqrt(max(0.0, 1 - cosA * cosA))
    v = polo - S
    v = v - u * v.dot(u)
    v.normalize()
    E = S + u * a * cosA + v * a * sinA
    MA = Matrix.LocRotScale(S, rot_hacia(eje_y(MA0), (E - S).normalized(), q(MA0)), None)
    MFc = MA @ (MA0.inverted() @ MF0)
    rotF = rot_hacia(eje_y(MFc), (T2 - E).normalized(), q(MFc))
    MF = Matrix.LocRotScale(E, rotF, None)
    MH = Matrix.LocRotScale(T2, rotF @ REL_MANO[lado], None)
    return MA, MF, MH


def resolver_brazo(lado, gc, polo):
    """Brazo con el centro del guante en gc; si se mete en la cabeza se aparta y se recalcula."""
    MA0, MF0, MH0 = (pb[lado + n].matrix.copy() for n in ("Arm", "ForeArm", "Hand"))
    rot = q(MH0)
    empuje = Vector()
    for _ in range(3):
        MA, MF, MH = ik_brazo(lado, gc - rot @ CENTRO_PUNO[lado] + empuje, polo)
        rot = q(MH)
    hq, n = hueco(guante_mundo(lado, MF, MH), pb["Head"].matrix), 0
    while hq < MARGEN and n < 8:
        dirc = (Vector(guante_mundo(lado, MF, MH).mean(axis=0)) - centro_cabeza()).normalized()
        empuje += dirc * (MARGEN - hq + 0.003)
        MA, MF, MH = ik_brazo(lado, gc - rot @ CENTRO_PUNO[lado] + empuje, polo)
        hq, n = hueco(guante_mundo(lado, MF, MH), pb["Head"].matrix), n + 1
    for parte, M in (("Arm", MA), ("ForeArm", MF), ("Hand", MH)):
        pb[lado + parte].matrix = M
        upd()
    return hq, empuje.length


def base_ortonormal(y, n):
    x = (n - y * n.dot(y)).normalized()
    return Matrix((x, y, x.cross(y))).transposed()


def ik_pierna(lado, T, ref=None):
    """Pierna con el tobillo en T y el pie con el mismo giro que en la referencia (apoyado)."""
    r = (ref or REF_GUARDIA)[lado]
    RM = r["M"]
    S = pb[lado + "UpLeg"].matrix.translation.copy()
    a, b = LON[lado + "UpLeg"], LON[lado + "Leg"]
    dvec = T - S
    dist = min(dvec.length, a + b - 1e-4)
    u = dvec.normalized()
    T2 = S + u * dist
    cosA = (a * a + dist * dist - b * b) / (2 * a * dist)
    sinA = math.sqrt(max(0.0, 1 - cosA * cosA))
    polo = T + r["polo"]
    v = polo - S
    v = (v - u * v.dot(u)).normalized()
    E = S + u * a * cosA + v * a * sinA
    n = u.cross(v)
    S0, E0, T0 = (RM[x].translation for x in ("UpLeg", "Leg", "Foot"))
    u0 = (T0 - S0).normalized()
    v0 = (E0 - S0) - u0 * (E0 - S0).dot(u0)
    n0 = u0.cross(v0.normalized())
    for hueso, (i, f, i0, f0) in (("UpLeg", (S, E, S0, E0)), ("Leg", (E, T2, E0, T0))):
        R = base_ortonormal((f - i).normalized(), n) @ base_ortonormal((f0 - i0).normalized(), n0).inverted()
        pb[lado + hueso].matrix = Matrix.LocRotScale(i, R.to_quaternion() @ q(RM[hueso]), None)
        upd()
    pb[lado + "Foot"].matrix = Matrix.LocRotScale(T2, q(RM["Foot"]), None)
    upd()
    return (T2 - T).length


def bajar_para_llegar(pies):
    """Baja la cadera lo justo para que las dos piernas lleguen a sus pies (casi estiradas)."""
    dz = 0.0
    for lado, T in pies.items():
        S = pb[lado + "UpLeg"].matrix.translation
        lmax = (LON[lado + "UpLeg"] + LON[lado + "Leg"]) * 0.985
        h = (S - T).xy.length
        vmax = math.sqrt(max(lmax * lmax - h * h, 0.0))
        dz = max(dz, (S.z - T.z) - vmax)
    if dz > 0:
        M = pb["Hips"].matrix
        pb["Hips"].matrix = Matrix.LocRotScale(M.translation - Vector((0, 0, dz)), q(M), None)
        upd()
    return dz


# ---------------------------------------------------------------- pose a mano a partir de parámetros
CERO = dict(sx=0.0, sy=0.0, baja=0.0, giro=0.0, flex=0.0, lado=0.0, torsion=0.0, cuello=0.0,
            cabeza=0.0, hombros=0.0, wL=0.0, wR=0.0)


def rotar(nombre, R):
    M = pb[nombre].matrix
    pb[nombre].matrix = Matrix.LocRotScale(M.translation, R @ q(M), None)
    upd()


def posar(par, brazos):
    """par: parámetros (m y grados). brazos: {lado: (guante en coords. de cabeza, codo en coords. de pecho)}.
    giro/torsion/lado positivos = hacia la izquierda del boxeador."""
    base_cuerpo()
    M = pb["Hips"].matrix
    t = M.translation + X * par["sx"] + DELANTE * par["sy"] - Vector((0, 0, par["baja"]))
    pb["Hips"].matrix = Matrix.LocRotScale(t, Quaternion((0, 0, 1), math.radians(par["giro"])) @ q(M), None)
    upd()
    for n, frac in (("Spine", 0.3), ("Spine1", 0.35), ("Spine2", 0.35)):
        cara, arriba, izq = marco(n)
        rotar(n, Quaternion(arriba, math.radians(par["torsion"] * frac))
              @ Quaternion(arriba.cross(izq), math.radians(par["lado"] * frac))
              @ Quaternion(arriba.cross(cara), math.radians(par["flex"] * frac)))
    if par["hombros"]:
        for lado, s in LADOS.items():
            cara, arriba, izq = marco("Spine2")
            rotar(lado + "Shoulder", Quaternion((izq * s).cross(arriba), math.radians(par["hombros"])))
    cara, arriba, _ = marco("Neck")
    rotar("Neck", Quaternion(arriba, math.radians(par["cuello"])) @ Quaternion(arriba.cross(cara), math.radians(par["cabeza"] * 0.4)))
    cara, arriba, _ = marco("Head")
    rotar("Head", Quaternion(arriba.cross(cara), math.radians(par["cabeza"] * 0.6)))
    # piernas: pies fijos en el suelo
    pies = {lado: PIE0[lado] + par.get("pie_" + lado, Vector()) for lado in LADOS}
    bajada = bajar_para_llegar(pies)
    desliz = max(ik_pierna(lado, T) for lado, T in pies.items())
    # brazos
    huecos, emp = {}, 0.0
    for lado, s in LADOS.items():
        w = par["w" + lado[0]]
        if w <= 0:
            huecos[lado] = hueco(guante_mundo(lado, pb[lado + "ForeArm"].matrix, pb[lado + "Hand"].matrix), pb["Head"].matrix)
            if huecos[lado] >= MARGEN:
                continue   # sigue rígido con el pecho (la guardia de guardia_v2)
            w = 0.0
        g_obj, c_obj = brazos.get(lado, GUARDIA[lado])
        g = GUARDIA[lado][0].lerp(g_obj, w)
        c = GUARDIA[lado][1].lerp(c_obj, w)
        gc = punto(centro_cabeza(), marco("Head"), g, s)
        polo = punto(pb["Spine2"].head, marco("Spine2"), c, s)
        huecos[lado], e = resolver_brazo(lado, gc, polo)
        emp = max(emp, e)
    return dict(bajada=bajada, desliz=desliz, huecos=huecos, empuje=emp)


def suave(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def interp(claves, f, modo):
    """claves: [(fot, {param: valor})]. modo 'suave' (ease in/out entre claves) o 'continuo' (Catmull-Rom)."""
    fs = [c[0] for c in claves]
    i = max(j for j in range(len(fs)) if fs[j] <= f) if f >= fs[0] else 0
    i = min(i, len(fs) - 2)
    t = (f - fs[i]) / (fs[i + 1] - fs[i])
    res = dict(CERO)
    for k in CERO:
        v = [c[1].get(k, CERO[k]) for c in claves]
        if modo == "suave":
            res[k] = v[i] + (v[i + 1] - v[i]) * suave(t)
        else:
            p0, p1, p2, p3 = v[max(i - 1, 0)], v[i], v[i + 1], v[min(i + 2, len(v) - 1)]
            t = min(max(t, 0.0), 1.0)
            res[k] = 0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                            + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)
    return res


def clave(b, f, previo):
    qq = b.rotation_quaternion.copy()
    if previo is not None and qq.dot(previo) < 0:
        qq.negate()
        b.rotation_quaternion = qq
    b.keyframe_insert("rotation_quaternion", frame=f, group=b.name)
    return qq


def crear(nombre, n_fot, claves, modo, brazos):
    a = bpy.data.actions.new(nombre)
    a.use_fake_user = True
    arm.animation_data.action = a
    arm.animation_data.action_slot = None
    previo = {n: None for n in pb}
    rep = dict(bajada=0.0, desliz=0.0, hueco=1.0, empuje=0.0, guantes=1.0, cab_min=9.0, cab_x=[0.0, 0.0])
    for f in range(1, n_fot + 1):
        esc.frame_set(f)
        r = posar(interp(claves, f, modo), brazos)
        for n, b in pb.items():
            previo[n] = clave(b, f, previo[n])
        pb["Hips"].keyframe_insert("location", frame=f, group=pb["Hips"].name)
        if arm.animation_data.action_slot is None and len(a.slots):
            arm.animation_data.action_slot = a.slots[0]
        rep["bajada"] = max(rep["bajada"], r["bajada"])
        rep["desliz"] = max(rep["desliz"], r["desliz"])
        rep["hueco"] = min(rep["hueco"], min(r["huecos"].values()))
        rep["empuje"] = max(rep["empuje"], r["empuje"])
        rep["guantes"] = min(rep["guantes"], hueco_guantes())
        cab = centro_cabeza()
        rep["cab_min"] = min(rep["cab_min"], cab.z)
        rep["cab_x"] = [min(rep["cab_x"][0], cab.x), max(rep["cab_x"][1], cab.x)]
    for fc in a.fcurves:
        for k in fc.keyframe_points:
            k.interpolation = "BEZIER"
            k.handle_left_type = k.handle_right_type = "AUTO_CLAMPED"
        fc.update()
    return rep


def comprobar_inicio_fin(nombre):
    """Diferencia (mm) de la pose del fot. 1 y del último con guardia_v2 fot. 1 (posiciones de las articulaciones)."""
    poner("guardia_v2")
    esc.frame_set(1)
    g = {n: b.head.copy() for n, b in pb.items()}
    a = poner(nombre)
    f0, f1 = (int(x) for x in a.frame_range)
    res = []
    for f in (f0, f1):
        esc.frame_set(f)
        res.append(max((b.head - g[n]).length for n, b in pb.items()) * 1000)
    return res


def informe(nombre, n_fot, rep):
    ini, fin = comprobar_inicio_fin(nombre)
    a = poner(nombre)
    zs = []
    for f in range(1, n_fot + 1):
        esc.frame_set(f)
        s = suelas()
        zs += [s["Left"], s["Right"]]
    p(f"  {nombre:20} {n_fot:3} fot. ({(n_fot - 1) / 30:.2f} s) | aire guante-cabeza mín. {rep['hueco'] * 100:4.1f} cm"
      f" (empuje {rep['empuje'] * 100:3.1f}) | guante-guante mín. {rep['guantes'] * 100:4.1f} cm"
      f" | suelas Z {min(zs) * 100:+.1f}/{max(zs) * 100:+.1f} cm | cabeza: baja hasta {rep['cab_min']:.2f} m,"
      f" X {rep['cab_x'][0] * 100:+.0f}/{rep['cab_x'][1] * 100:+.0f} cm | fot.1 y último vs guardia_v2: {ini:.0f} / {fin:.0f} mm")


# ---------------------------------------------------------------- 3. bloqueos (28 fot.: sube 1-8, aguanta 8-20, vuelve 20-28)
N_BLQ = 28


def claves_bloqueo(pose):
    return [(1, {}), (8, pose), (20, pose), (N_BLQ, {})]


# coordenadas de los objetivos: guante (delante, arriba, lateral) respecto al centro de la cabeza;
# codo (delante, arriba, lateral) respecto al pecho (Spine2). Lateral positivo = hacia SU lado.
BLOQUEOS = {
    # los dos guantes pegados a la cara (por delante, casi juntos), codos juntos delante de las costillas
    "bloqueo_cerrado": (dict(baja=0.045, flex=10.0, cabeza=7.0, hombros=7.0, wL=1.0, wR=1.0),
                        {lado: (Vector((0.14, 0.005, 0.078)), Vector((0.30, -0.32, 0.02))) for lado in LADOS}),
}
for lado, s in LADOS.items():
    nl = NOMBRE_LADO[lado]
    # guante a la sien/oreja de ese lado, antebrazo vertical, codo algo levantado y hacia fuera
    BLOQUEOS[f"bloqueo_alto_{nl}"] = (
        dict(baja=0.02, cabeza=4.0, torsion=-4.0 * s, **{"w" + lado[0]: 1.0}),
        {lado: (Vector((0.04, -0.015, 0.165)), Vector((0.14, -0.04, 0.36)))})
    # codo pegado a las costillas de ese lado, guante cerca de la cara; giro y encogimiento hacia ese lado
    BLOQUEOS[f"bloqueo_bajo_{nl}"] = (
        dict(baja=0.035, flex=6.0, lado=8.0 * s, torsion=10.0 * s, cabeza=5.0, **{"w" + lado[0]: 1.0}),
        {lado: (Vector((0.15, -0.06, 0.085)), Vector((0.06, -0.42, 0.12)))})

p("\n=== BLOQUEOS (desde guardia_v2 y volviendo a ella) ===")
for nombre, (pose, brazos) in BLOQUEOS.items():
    rep = crear(nombre, N_BLQ, claves_bloqueo(pose), "suave", brazos)
    informe(nombre, N_BLQ, rep)

# ---------------------------------------------------------------- 4. ruedas (37 fot.)
N_RUEDA = 37


def claves_rueda(s):
    """s = +1: la U empieza a la izquierda y termina a la derecha (rueda_der); s = -1 al revés."""
    a = dict(sx=0.08 * s, giro=15.0 * s, lado=11.0 * s, torsion=8.0 * s, cuello=-11.0 * s,
             baja=0.03, flex=4.0, cabeza=3.0)
    fondo = dict(baja=0.09, flex=16.0, cabeza=8.0)
    b = {k: (-v if k in ("sx", "giro", "lado", "torsion", "cuello") else v) for k, v in a.items()}
    return [(1, {}), (8, a), (19, fondo), (30, b), (N_RUEDA, {})]


p("\n=== RUEDAS (la cabeza dibuja una U y sube en el lado del nombre) ===")
for nombre, s in (("rueda_der", 1.0), ("rueda_izq", -1.0)):
    rep = crear(nombre, N_RUEDA, claves_rueda(s), "continuo", {})
    informe(nombre, N_RUEDA, rep)

# ---------------------------------------------------------------- 5. esquivas: pies fijos en el suelo y paso real
PASO = 0.22
ESQUIVAS = {
    # pie que da el paso (guardia ortodoxa: izquierdo delante, derecho detrás), sentido
    # (-1 hacia atrás, +1 hacia delante) y fotogramas (despega, apoya) del paso y de la vuelta
    "esquiva_retrocediendo_v2": ("Right", -1, (2, 9), (58, 66)),
    "esquiva_avanzando_v2": ("Left", 1, (2, 9), (61, 69)),
}
HUESOS_PIERNA = [l + x for l in LADOS for x in ("UpLeg", "Leg", "Foot", "ToeBase")]


def desplazamiento_paso(f, ida, vuelta, f1):
    """0 -> 1 entre los fotogramas de ida, 1 -> 0 entre los de vuelta; altura del pie en el aire."""
    if f <= ida[0] or f >= vuelta[1]:
        return 0.0, 0.0
    if f < ida[1]:
        t = (f - ida[0]) / (ida[1] - ida[0])
        return suave(t), math.sin(math.pi * t)
    if f > vuelta[0]:
        t = (f - vuelta[0]) / (vuelta[1] - vuelta[0])
        return 1 - suave(t), math.sin(math.pi * t)
    return 1.0, 0.0


p("\n=== ESQUIVAS: pies fijos en el suelo (IK) en su postura del fot. 1 y paso real ===")
for nombre, (pie, sentido, ida, vuelta) in ESQUIVAS.items():
    a = poner(nombre)
    f0, f1 = (int(x) for x in a.frame_range)
    esc.frame_set(f0)
    for n in [l + "ToeBase" for l in LADOS]:   # el dedo del pie como en la guardia (pie plano)
        pb[n].rotation_quaternion = BASE[n][1]
    upd()
    yaw0 = math.degrees((q(pb["Hips"].matrix) @ q(M0["Hips"]).inverted()).to_euler().z)
    s1 = suelas()
    pie1 = {l: pb[l + "Foot"].matrix.translation - Vector((0, 0, s1[l])) for l in LADOS}
    ref = referencia_piernas({n: b.matrix.copy() for n, b in pb.items()}, pie1)
    dire = DELANTE * sentido   # el muñeco mira hacia -Y
    cad1 = pb["Hips"].matrix.translation.copy()
    previo = {n: None for n in HUESOS_PIERNA}
    bajada, desliz, zs_apoyo = 0.0, 0.0, []
    for f in range(f0, f1 + 1):
        esc.frame_set(f)
        k, alt = desplazamiento_paso(f, ida, vuelta, f1)
        for n in [l + "ToeBase" for l in LADOS]:
            pb[n].rotation_quaternion = BASE[n][1]
        M = pb["Hips"].matrix
        t = Vector((cad1.x, cad1.y, M.translation.z)) + dire * (PASO * 0.5 * k)
        pb["Hips"].matrix = Matrix.LocRotScale(t, q(M), None)
        upd()
        pies = {lado: pie1[lado].copy() for lado in LADOS}
        pies[pie] += dire * (PASO * k) + Vector((0, 0, 0.035 * alt))
        bajada = max(bajada, bajar_para_llegar(pies))
        desliz = max(desliz, max(ik_pierna(lado, T, ref) for lado, T in pies.items()))
        pb["Hips"].keyframe_insert("location", frame=f, group=pb["Hips"].name)
        for n in HUESOS_PIERNA:
            previo[n] = clave(pb[n], f, previo[n])
        s = suelas()
        zs_apoyo += [s[l] for l in LADOS if l != pie or alt == 0]
    for fc in a.fcurves:
        fc.update()
    ini, fin = comprobar_inicio_fin(nombre)
    p(f"  {nombre:26} paso de {PASO * 100:.0f} cm {'hacia atrás con el pie de atrás' if sentido < 0 else 'hacia delante con el pie de delante'}"
      f" ({NOMBRE_LADO[pie]})"
      f" fot. {ida[0]}-{ida[1]}, vuelve fot. {vuelta[0]}-{vuelta[1]} | giro de la cadera respecto a la guardia en el fot. 1: {yaw0:+.0f}°\n"
      f"     suela de los pies apoyados: Z {min(zs_apoyo) * 100:+.2f}/{max(zs_apoyo) * 100:+.2f} cm | cadera bajada para llegar:"
      f" {bajada * 100:.1f} cm máx. | tobillo fuera del objetivo: {desliz * 1000:.1f} mm | fot.1 y último vs guardia_v2:"
      f" {ini:.0f} / {fin:.0f} mm (el tronco es el de Mixamo)")

# ---------------------------------------------------------------- 6. paso_atras_v2 (lo deja fase4_b.py)
a = poner("paso_atras_v2")
f0, f1 = (int(x) for x in a.frame_range)
esc.frame_set(f0)
h0 = pb["Hips"].head.copy()
pose0 = {n: b.head - h0 for n, b in pb.items()}
esc.frame_set(f1)
h1 = pb["Hips"].head.copy()
dif = max(((b.head - h1) - pose0[n]).length for n, b in pb.items())
p(f"\n=== paso_atras_v2 ===\n  desplazamiento de la cadera fot. {f0} -> {f1}: {(h1 - h0).y * 100:+.1f} cm en Y (hacia atrás),"
  f" {(h1 - h0).z * 100:+.1f} cm en Z | pose final vs inicial (quitando el desplazamiento): {dif * 1000:.1f} mm")

poner("guardia_v2")
esc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
p("\n  Acciones:", ", ".join(sorted(a.name for a in bpy.data.actions)))
p(f"  GUARDADO {os.path.relpath(BLEND, C.RAIZ)}")
p("  REVISAR CON ENTRENADOR: cómo quiere Iván el bloqueo del crochet (guante a la sien, codo arriba...)"
  " y qué crochet del rival evita cada rueda.")
with open(os.path.join(C.TRABAJO, "fase5_resumen.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out) + "\n")
