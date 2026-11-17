"""Fase 5 sobre el modelo principal (B): correcciones de David tras revisar las _v2.

Ejecutar DESPUÉS de fase4_b.py (que rehace las _v2 y deja paso_atras_v2 desplazado al final).
1. La acción `bloqueo` de Mixamo es una reacción a un golpe: se renombra a `reaccion_golpe`
   (sin _v2) y se borran bloqueo_v2, rueda y rueda_v2.
2. Bloqueos hechos a mano desde guardia_v2 (fot. 1) y volviendo a ella (28 fot., 0,9 s):
   bloqueo_cerrado, bloqueo_alto_izq/_der (guante a la sien, antebrazo vertical, codo algo
   arriba), bloqueo_bajo_izq/_der (codo pegado a las costillas, giro y encogimiento hacia ese
   lado). Izquierda y derecha se definen a mano (sin espejo: los pies no cambian).
3. Rueda hecha a mano (37 fot., 1,2 s): rueda_der y rueda_izq. La cabeza dibuja una "U" (sube
   en el lado del nombre); cadera y tronco giran y se inclinan, rodillas flexionadas (la cadera baja hasta 15 cm), pierna de delante adelantada 12 cm,
   guantes en guardia todo el tiempo.
3b. Pasos hechos a mano (25 fot., 0,8 s): paso_adelante, paso_lateral_izq y paso_lateral_der. Como
   paso_atras_v2: sale primero el pie del lado hacia el que se va y le sigue el otro; acaban
   desplazados 25 cm y en guardia (solo la pose coincide con el primer fotograma).
3c. Acciones que faltaban para la app (todas REVISAR CON ENTRENADOR): jab_cuerpo, recto_cuerpo y
   crochet_adelantado_cuerpo (desde las _v2, bajando con las piernas hasta que el hombro queda a la
   altura del objetivo), gancho_adelantado y gancho_trasero a la cara (desde los ganchos al cuerpo,
   puño a la altura de la barbilla, codo ~90°, palma hacia uno mismo), esquiva_der / esquiva_izq,
   ballesteo, parada (mano derecha) y pivote (acaba girado 45°).
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
NUEVAS_APP = ("jab_cuerpo", "recto_cuerpo", "crochet_adelantado_cuerpo", "gancho_adelantado", "gancho_trasero", "esquiva_der", "esquiva_izq", "ballesteo", "parada", "pivote")
for n in [a.name for a in acc if a.name in ("bloqueo", "bloqueo_v2", "rueda", "rueda_v2", "reaccion_golpe_v2") + NUEVAS_APP
          or a.name.startswith(("bloqueo_", "rueda_", "paso_adelante", "paso_lateral_"))]:
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


BOLA0 = {lado: M0[lado + "ToeBase"].translation - Vector((0, 0, s0[lado])) for lado in LADOS}


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
                     coords(pb["Spine1"].head, marco("Spine1"), M0[lado + "ForeArm"].translation, s))
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


def resolver_brazo(lado, gc, polo, dir_emp=None, muneca=False):
    """Brazo con el centro del guante en gc (o la muñeca, si muneca=True); si el guante se mete en la
    cabeza se aparta y se recalcula (desde el centro de la cabeza, o en la dirección dir_emp)."""
    MA0, MF0, MH0 = (pb[lado + n].matrix.copy() for n in ("Arm", "ForeArm", "Hand"))
    rot = q(MH0)
    empuje = Vector()

    def objetivo():
        return (gc if muneca else gc - rot @ CENTRO_PUNO[lado]) + empuje

    for _ in range(3):
        MA, MF, MH = ik_brazo(lado, objetivo(), polo)
        rot = q(MH)
    hq, n = hueco(guante_mundo(lado, MF, MH), pb["Head"].matrix), 0
    while hq < MARGEN and n < 8:
        dirc = dir_emp or (Vector(guante_mundo(lado, MF, MH).mean(axis=0)) - centro_cabeza()).normalized()
        empuje += dirc * (MARGEN - hq + 0.003)
        MA, MF, MH = ik_brazo(lado, objetivo(), polo)
        hq, n = hueco(guante_mundo(lado, MF, MH), pb["Head"].matrix), n + 1
    for parte, M in (("Arm", MA), ("ForeArm", MF), ("Hand", MH)):
        pb[lado + parte].matrix = M
        upd()
    return hq, empuje.length


def base_ortonormal(y, n):
    x = (n - y * n.dot(y)).normalized()
    return Matrix((x, y, x.cross(y))).transposed()


def ik_pierna(lado, T, ref=None, rot=None):
    """Pierna con el tobillo en T y el pie con el mismo giro que en la referencia (apoyado), más
    el giro extra rot (pie que pivota sobre la punta)."""
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
    pb[lado + "Foot"].matrix = Matrix.LocRotScale(T2, (rot or Quaternion()) @ q(RM["Foot"]), None)
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
            cabeza=0.0, hombros=0.0, abdomen=0.0, hL=0.0, hR=0.0, aL=0.0, aR=0.0, wL=0.0, wR=0.0)


def rotar(nombre, R):
    M = pb[nombre].matrix
    pb[nombre].matrix = Matrix.LocRotScale(M.translation, R @ q(M), None)
    upd()


def posar(par, brazos, pies_extra=None, cadera_extra=None, giro_extra=0.0, rot_pies=None):
    """par: parámetros (m y grados). brazos: {lado: (guante en coords. de cabeza, codo en coords. de pecho)}.
    giro/torsion/lado positivos = hacia la izquierda del boxeador."""
    base_cuerpo()
    M = pb["Hips"].matrix
    t = M.translation + X * par["sx"] + DELANTE * par["sy"] - Vector((0, 0, par["baja"])) + (cadera_extra or Vector())
    pb["Hips"].matrix = Matrix.LocRotScale(t, Quaternion((0, 0, 1), math.radians(par["giro"] + giro_extra)) @ q(M), None)
    upd()
    # flex: tronco hacia delante repartido; abdomen: contracción (flexión sobre todo abajo, Spine/Spine1)
    for n, frac, fab in (("Spine", 0.3, 0.5), ("Spine1", 0.35, 0.4), ("Spine2", 0.35, 0.1)):
        cara, arriba, izq = marco(n)
        rotar(n, Quaternion(arriba, math.radians(par["torsion"] * frac))
              @ Quaternion(arriba.cross(izq), math.radians(par["lado"] * frac))
              @ Quaternion(arriba.cross(cara), math.radians(par["flex"] * frac + par["abdomen"] * fab)))
    # hombros: hacia arriba (los dos: hombros; cada uno: hL / hR) y hacia delante (aL / aR, protracción)
    for lado, s in LADOS.items():
        g, adel = par["hombros"] + par["h" + lado[0]], par["a" + lado[0]]
        if g or adel:
            cara, arriba, izq = marco("Spine2")
            rotar(lado + "Shoulder", Quaternion((izq * s).cross(cara), math.radians(adel))
                  @ Quaternion((izq * s).cross(arriba), math.radians(g)))
    cara, arriba, _ = marco("Neck")
    rotar("Neck", Quaternion(arriba, math.radians(par["cuello"])) @ Quaternion(arriba.cross(cara), math.radians(par["cabeza"] * 0.4)))
    cara, arriba, _ = marco("Head")
    rotar("Head", Quaternion(arriba.cross(cara), math.radians(par["cabeza"] * 0.6)))
    # piernas: pies fijos en el suelo
    pies = {lado: PIE0[lado] + (pies_extra or {}).get(lado, Vector()) for lado in LADOS}
    # pie que pivota sobre la punta: giro (grados, + = hacia su izquierda) y talón levantado (grados)
    rot, dedos = {}, {}
    for lado, (yaw, talon) in (rot_pies or {}).items():
        B = BOLA0[lado] + (pies_extra or {}).get(lado, Vector())
        d = B - pies[lado]
        d = Vector((d.x, d.y, 0)).normalized()
        eje = (-d).cross(Vector((0, 0, 1))).normalized()
        Ry = Quaternion((0, 0, 1), math.radians(yaw))
        R = Ry @ Quaternion(eje, math.radians(talon))
        pies[lado] = B + R @ (pies[lado] - B)
        rot[lado], dedos[lado] = R, (Ry @ eje, talon)
    bajada = bajar_para_llegar(pies)
    desliz = max(ik_pierna(lado, T, rot=rot.get(lado)) for lado, T in pies.items())
    for lado, (eje, talon) in dedos.items():   # los dedos siguen planos en el suelo
        if talon:
            rotar(lado + "ToeBase", Quaternion(eje, -math.radians(talon)))
    # brazos
    huecos, emp = {}, 0.0
    for lado, s in LADOS.items():
        w = min(par["w" + lado[0]], 1.0)
        if w <= 0:
            huecos[lado] = hueco(guante_mundo(lado, pb[lado + "ForeArm"].matrix, pb[lado + "Hand"].matrix), pb["Head"].matrix)
            if huecos[lado] >= MARGEN:
                continue   # sigue rígido con el pecho (la guardia de guardia_v2)
            w = 0.0
        spec = brazos.get(lado, GUARDIA[lado])
        sp1 = (pb["Spine1"].head, marco("Spine1"))
        if isinstance(spec[0], str) and spec[0] == "codo":
            # primero el codo (donde tiene que tapar) y el antebrazo sale de él hacia la cara
            _, e_c, d_c, *extra = spec
            S = pb[lado + "Arm"].head
            E = punto(*sp1, e_c, s)
            if (E - S).length > LON[lado + "Arm"] * 0.995:
                E = S + (E - S).normalized() * LON[lado + "Arm"] * 0.995
            dirf = (punto(*sp1, d_c, s) - sp1[0]).normalized()
            Wb = E + dirf * LON[lado + "ForeArm"]
            Wg = punto(centro_cabeza(), marco("Head"), GUARDIA[lado][0], s) - q(pb[lado + "Hand"].matrix) @ CENTRO_PUNO[lado]
            T = Wg.lerp(Wb, w)
            polo = punto(*sp1, GUARDIA[lado][1], s).lerp(E, w)
            dir_emp = marco("Head")[2] * s if extra and extra[0] == "lateral" else None
            huecos[lado], e = resolver_brazo(lado, T, polo, dir_emp, muneca=True)
        else:
            g_obj, c_obj, *extra = spec
            g = GUARDIA[lado][0].lerp(g_obj, w)
            c = GUARDIA[lado][1].lerp(c_obj, w)
            gc = punto(centro_cabeza(), marco("Head"), g, s)
            polo = punto(*sp1, c, s)
            dir_emp = marco("Head")[2] * s if extra and extra[0] == "lateral" else None
            huecos[lado], e = resolver_brazo(lado, gc, polo, dir_emp)
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


def medir_pico(lados):
    """Dónde queda cada brazo que bloquea: codo respecto al hombro y al pecho, guante respecto a la cabeza."""
    txt = []
    for lado in lados:
        s = LADOS[lado]
        codo = pb[lado + "ForeArm"].head
        c = coords(pb["Spine1"].head, marco("Spine1"), codo, s)
        alto = codo.z - pb[lado + "Arm"].head.z
        hq = hueco(guante_mundo(lado, pb[lado + "ForeArm"].matrix, pb[lado + "Hand"].matrix), pb["Head"].matrix)
        g = coords(centro_cabeza(), marco("Head"), pb[lado + "Hand"].matrix @ CENTRO_PUNO[lado], s)
        txt.append(f"{NOMBRE_LADO[lado]}: codo {alto * 100:+.0f} cm sobre el hombro, {c.x * 100:.0f} cm delante del hueso"
                   f" Spine1, {c.z * 100:+.0f} al lado, {c.y * 100:+.0f} de altura; guante (delante, alto, lado) respecto a la"
                   f" cabeza ({g.x * 100:.0f}, {g.y * 100:+.0f}, {g.z * 100:.0f}) cm, aire con la cabeza {hq * 100:.1f} cm")
    return "; ".join(txt)


def crear(nombre, n_fot, claves, modo, brazos, pico=None, pies=None):
    a = bpy.data.actions.new(nombre)
    a.use_fake_user = True
    arm.animation_data.action = a
    arm.animation_data.action_slot = None
    previo = {n: None for n in pb}
    rep = dict(bajada=0.0, desliz=0.0, hueco=1.0, empuje=0.0, guantes=1.0, cab_min=9.0, cab_x=[0.0, 0.0])
    for f in range(1, n_fot + 1):
        esc.frame_set(f)
        # pies(f): {lado: desplazamiento del pie}, o (pies, cadera), o dict(pies=, cadera=, giro=, rotpie=)
        ext = pies(f) if pies else None
        if isinstance(ext, tuple):
            ext = dict(pies=ext[0], cadera=ext[1])
        elif ext is not None and not ({"pies", "cadera", "giro", "rotpie"} & set(ext)):
            ext = dict(pies=ext)
        ext = ext or {}
        r = posar(interp(claves, f, modo), brazos, ext.get("pies"), ext.get("cadera"), ext.get("giro", 0.0),
                  ext.get("rotpie"))
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
        if f == pico:
            rep["pico"] = medir_pico(brazos)
    for fc in a.fcurves:
        for k in fc.keyframe_points:
            k.interpolation = "BEZIER"
            k.handle_left_type = k.handle_right_type = "AUTO_CLAMPED"
        fc.update()
    if pico:
        a["clave"] = pico
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
    if rep.get("pico"):
        p(f"     punto clave -> {rep['pico']}")


# ---------------------------------------------------------------- 3. bloqueos (28 fot.: sube 1-8, aguanta 8-20, vuelve 20-28)
N_BLQ = 28


def claves_bloqueo(pose):
    return [(1, {}), (8, pose), (20, pose), (N_BLQ, {})]


# Brazo que bloquea: ("codo", codo, antebrazo[, "lateral"]). Primero el codo, donde tiene que tapar,
# en (delante, arriba, lateral) respecto al hueso Spine1 (columna a la altura de las costillas bajas;
# la superficie del pecho está ~16 cm por delante); el antebrazo sale del codo en la dirección dada
# (mismas coordenadas) y la muñeca queda a un antebrazo de distancia. Lateral positivo = hacia SU lado.
# Si el codo no llega (brazo de 27 cm desde el hombro) se acerca al hombro en la misma dirección.
# Si el guante se mete en la cabeza se aparta (hacia el lado con "lateral").
BLOQUEOS = {
    # los dos guantes delante de la cara; codos juntos y ADELANTADOS delante de las costillas, antebrazos
    # casi verticales, abdomen contraído y hombros adelantados para tapar el torso (aquí es grande)
    "bloqueo_cerrado": (dict(baja=0.045, flex=10.0, abdomen=14.0, cabeza=7.0, hombros=8.0, aL=16.0, aR=16.0,
                             wL=1.0, wR=1.0),
                        {lado: ("codo", Vector((0.15, 0.06, 0.08)), Vector((0.35, 1.0, 0.05))) for lado in LADOS}),
}
for lado, s in LADOS.items():
    nl = NOMBRE_LADO[lado]
    # tapa el lateral de la cabeza: el codo SUBE (rotando el hombro) y queda delante; el antebrazo sube
    # por el lado de la cabeza y el guante queda PEGADO a la sien/oreja (el derecho, hombro trasero,
    # con el antebrazo más vertical para que el guante no se vaya detrás de la cabeza)
    BLOQUEOS[f"bloqueo_alto_{nl}"] = (
        dict(baja=0.02, cabeza=4.0, torsion=-4.0 * s, **{"h" + lado[0]: 14.0, "w" + lado[0]: 1.0}),
        {lado: ("codo", Vector((0.17, 0.13, 0.17)), Vector((-0.20 if lado == "Left" else -0.02, 1.0, -0.10)), "lateral")})
    # tapa costillas e hígado: el codo baja pegado al cuerpo pero ADELANTADO, por delante de las
    # costillas; antebrazo casi vertical hacia la barbilla; giro y encogimiento del tronco hacia ese lado
    BLOQUEOS[f"bloqueo_bajo_{nl}"] = (
        dict(baja=0.035, flex=4.0, abdomen=9.0, lado=8.0 * s, torsion=6.0 * s, cabeza=5.0,
             **{"a" + lado[0]: 20.0, "w" + lado[0]: 1.0}),
        {lado: ("codo", Vector((0.15, 0.03, 0.11)), Vector((0.25, 1.0, 0.0)))})

_sp1 = [v.co for v in cuerpo.data.vertices if any(nom[e.group] == "Spine1" and e.weight > 0.5 for e in v.groups)]
_cara_sp1 = (q(REST["Spine1"]).inverted() @ Vector((0, -1, 0)))
PECHO = max((REST_INV["Spine1"] @ c).dot(_cara_sp1) for c in _sp1)
p("\n=== BLOQUEOS (desde guardia_v2 y volviendo a ella) ===")
p(f"  (referencia: la superficie del pecho/abdomen a la altura de Spine1 está {PECHO * 100:.0f} cm por delante del hueso;"
  " un codo tapa las costillas si queda cerca o por delante de esa distancia)")
for nombre, (pose, brazos) in BLOQUEOS.items():
    rep = crear(nombre, N_BLQ, claves_bloqueo(pose), "suave", brazos, pico=14)
    informe(nombre, N_BLQ, rep)

# ---------------------------------------------------------------- 4. ruedas (37 fot.)
N_RUEDA = 37


def claves_rueda(s):
    """s = +1: la U empieza a la izquierda y termina a la derecha (rueda_der); s = -1 al revés."""
    # abdomen contraído (el torso baja) y guantes un poco más arriba durante toda la rueda
    a = dict(sx=0.08 * s, giro=15.0 * s, lado=11.0 * s, torsion=8.0 * s, cuello=-11.0 * s,
             baja=0.06, flex=3.0, abdomen=8.0, cabeza=3.0, wL=1.0, wR=1.0)
    fondo = dict(baja=0.15, flex=10.0, abdomen=16.0, cabeza=8.0, wL=1.0, wR=1.0)
    b = {k: (-v if k in ("sx", "giro", "lado", "torsion", "cuello") else v) for k, v in a.items()}
    return [(1, {}), (8, a), (19, fondo), (30, b), (N_RUEDA, {})]


# pierna de delante (izquierda) adelantada PASO_RUEDA durante la rueda: paso al empezar (fot. 1-7,
# antes de la U) y vuelta al final (fot. 31-37) para acabar en la guardia
PASO_RUEDA = 0.12


def pie_delante_rueda(f):
    if f <= 1 or f >= N_RUEDA:
        return {}
    if f < 7:
        t = (f - 1) / 6
    elif f > 31:
        t = (N_RUEDA - f) / 6
    else:
        return {"Left": DELANTE * PASO_RUEDA}
    return {"Left": DELANTE * (PASO_RUEDA * suave(t)) + Vector((0, 0, 0.03 * math.sin(math.pi * t)))}


# guantes 3,5 cm más arriba que en la guardia (respecto a la cabeza) para cubrir los golpes altos
MANOS_ARRIBA = {lado: (GUARDIA[lado][0] + Vector((0.0, 0.035, -0.005)), GUARDIA[lado][1] + Vector((0.0, 0.03, 0.0)))
                for lado in LADOS}
p("\n=== RUEDAS (la cabeza dibuja una U y sube en el lado del nombre) ===")
for nombre, s in (("rueda_der", 1.0), ("rueda_izq", -1.0)):
    rep = crear(nombre, N_RUEDA, claves_rueda(s), "continuo", MANOS_ARRIBA, pies=pie_delante_rueda)
    informe(nombre, N_RUEDA, rep)

# ---------------------------------------------------------------- 4b. pasos (adelante y laterales)
# Como paso_atras_v2: desde la guardia, primero el pie del lado hacia el que se va y luego el otro;
# la cadera acompaña a los pies y el muñeco ACABA DESPLAZADO (solo la pose coincide con el fot. 1).
N_PASO, D_PASO = 25, 0.25
PASOS = {
    # dirección, pie que sale primero, pie que le sigue
    "paso_adelante": (DELANTE, "Left", "Right"),
    "paso_lateral_izq": (X, "Left", "Right"),
    "paso_lateral_der": (-X, "Right", "Left"),
}


def avance(f, f0, f1):
    """0 -> 1 suave entre f0 y f1 y altura del pie en el aire (0 -> 1 -> 0)."""
    t = min(max((f - f0) / (f1 - f0), 0.0), 1.0)
    return suave(t), math.sin(math.pi * t)


def pies_paso(dire, primero, segundo):
    def fn(f):
        k1, a1 = avance(f, 1, 11)
        k2, a2 = avance(f, 11, 21)
        pies = {primero: dire * (D_PASO * k1) + Vector((0, 0, 0.04 * a1)),
                segundo: dire * (D_PASO * k2) + Vector((0, 0, 0.03 * a2))}
        return pies, dire * (D_PASO * (0.6 * k1 + 0.4 * k2))
    return fn


p("\n=== PASOS (adelante y laterales; acaban desplazados, la pose final es la de la guardia) ===")
for nombre, (dire, primero, segundo) in PASOS.items():
    # un poco más bajo mientras se mueve (rodillas), guardia todo el tiempo
    claves = [(1, {}), (11, dict(baja=0.02)), (21, {}), (N_PASO, {})]
    rep_p = crear(nombre, N_PASO, claves, "suave", {}, pies=pies_paso(dire, primero, segundo))
    a = poner(nombre)
    esc.frame_set(1)
    h0 = pb["Hips"].head.copy()
    pose0 = {n: b.head - h0 for n, b in pb.items()}
    zs = []
    for f in range(1, N_PASO + 1):
        esc.frame_set(f)
        zs.append(suelas())
    h1 = pb["Hips"].head.copy()
    dif = max(((b.head - h1) - pose0[n]).length for n, b in pb.items())
    apoyo = [z[l] for f, z in enumerate(zs, 1) for l in LADOS
             if f in (1, N_PASO) or 21 <= f or (l == segundo and f <= 11) or (l == primero and f >= 11)]
    p(f"  {nombre:18} {N_PASO} fot. ({(N_PASO - 1) / 30:.2f} s) | sale el pie {NOMBRE_LADO[primero]} (fot. 1-11) y le sigue el"
      f" {NOMBRE_LADO[segundo]} (fot. 11-21) | desplazamiento {(h1 - h0).length * 100:.1f} cm | pose final vs inicial"
      f" (quitando el desplazamiento) {dif * 1000:.1f} mm | suela de los pies apoyados Z {min(apoyo) * 100:+.2f}/"
      f"{max(apoyo) * 100:+.2f} cm | aire guante-cabeza mín. {rep_p['hueco'] * 100:.1f} cm")

# ================================================================ 4c. acciones que faltaban para la app (25)
# Todas: REVISAR CON ENTRENADOR. Desde guardia_v2 (o desde la _v2 de la que salen) y volviendo a ella.
import re  # noqa: E402

_F3 = open(os.path.join(C.TRABAJO, "fase3_resumen.txt"), encoding="utf-8").read()
Z = Vector((0, 0, 1))


def impacto(golpe):
    m = re.search(rf"^\s+{golpe}\s+mano.*?IMPACTO fot\.\s+(\d+)", _F3, re.M)
    return int(m.group(1))


def curva(f, imp, f1, sube=10, aguanta=3, baja=12):
    """0 -> 1 (suave) hasta el impacto, se mantiene `aguanta` fotogramas y vuelve a 0 antes del final."""
    a = max(2, imp - sube)
    b = min(imp + aguanta, f1 - 3)
    c = min(b + baja, f1 - 1)
    if f <= a or f >= c:
        return 0.0
    if f < imp:
        return suave((f - a) / (imp - a))
    if f <= b:
        return 1.0
    return 1 - suave((f - b) / (c - b))


def rampa(f, claves):
    """claves [(fot, valor)] con transiciones suaves."""
    for (fa, va), (fb, vb) in zip(claves, claves[1:]):
        if fa <= f <= fb:
            return va + (vb - va) * suave((f - fa) / (fb - fa))
    return claves[-1][1]


REST_Z = {n: REST[n].translation.z for n in ("Spine1", "Spine2", "Head")}
OBJ_PLEXO = (REST_Z["Spine1"] + REST_Z["Spine2"]) / 2          # plexo/estómago del rival (mismo muñeco)
OBJ_COSTILLAS = REST_Z["Spine1"] + 0.05                         # costillas flotantes del rival
OBJ_BARBILLA = REST_Z["Head"] - 0.03                            # barbilla del rival
PALMA = {lado: q(REST[lado + "Hand"]).inverted() @ Vector((0, 0, -1)) for lado in LADOS}   # en T las palmas miran abajo
HUESOS_PIERNA6 = [l + x for l in LADOS for x in ("UpLeg", "Leg", "Foot", "ToeBase")]


def gancho_a_la_cara(lado, w):
    """Brazo del gancho a la cara (impacto): codo doblado ~90°, antebrazo vertical delante del pecho y
    el puño a la altura de la barbilla; palma hacia uno mismo. Se mezcla con el brazo de la _v2 (peso w)."""
    s = LADOS[lado]
    sp1 = (pb["Spine1"].head, marco("Spine1"))
    S = pb[lado + "Arm"].head
    E = punto(*sp1, Vector((0.30, 0.12, 0.10)), s)
    if (E - S).length > LON[lado + "Arm"] * 0.995:
        E = S + (E - S).normalized() * LON[lado + "Arm"] * 0.995
    dirf = (punto(*sp1, Vector((0.35, 1.0, 0.0)), s) - sp1[0]).normalized()
    # sube (o baja) codo y muñeca para que el puño quede a la altura de la barbilla del rival
    puno_z = (E + dirf * (LON[lado + "ForeArm"] + CENTRO_PUNO[lado].length)).z
    E = E + Z * (OBJ_BARBILLA - puno_z)
    if (E - S).length > LON[lado + "Arm"] * 0.995:
        E = S + (E - S).normalized() * LON[lado + "Arm"] * 0.995
    W = E + dirf * LON[lado + "ForeArm"]
    T = pb[lado + "Hand"].head.lerp(W, w)
    polo = pb[lado + "ForeArm"].head.lerp(E, w)
    hq, _ = resolver_brazo(lado, T, polo, muneca=True)
    # palma hacia uno mismo: girar la mano sobre su eje
    MH = pb[lado + "Hand"].matrix
    ej = eje_y(MH)
    palma = q(MH) @ PALMA[lado]
    quiero = -sp1[1][0]
    a_ = palma - ej * palma.dot(ej)
    b_ = quiero - ej * quiero.dot(ej)
    if a_.length > 1e-4 and b_.length > 1e-4:
        ang = a_.normalized().angle(b_.normalized())
        if a_.cross(b_).dot(ej) < 0:
            ang = -ang
        rotar(lado + "Hand", Quaternion(ej, ang * w))
    return hq


BAJA_MIN = 0.08


def derivar(origen, nombre, lado_golpe, objetivo=None, paso=0.10, gancho=False):
    """Golpe nuevo a partir de una _v2: se baja con las piernas (rodillas y pierna de delante que
    avanza) hasta que el hombro del brazo que golpea queda a la altura del objetivo; la otra mano sigue
    pegada a la cara. Gancho a la cara: el brazo cambia de trayectoria y las piernas cargan y empujan."""
    base = origen[:-3]
    imp = impacto(base)
    a = bpy.data.actions[origen].copy()
    a.name = nombre
    a.use_fake_user = True
    a["clave"] = imp
    poner(nombre)
    f0, f1 = (int(x) for x in a.frame_range)
    # en los golpes de Mixamo la cadera se desplaza y los pies la acompañan: las piernas siguen los pies de
    # la animación en cada fotograma (suela en el suelo) y encima la pierna de delante avanza y la cadera baja
    esc.frame_set(imp)
    hombro0 = pb[lado_golpe + "Arm"].head.z
    puno0 = (pb[lado_golpe + "Hand"].matrix @ CENTRO_PUNO[lado_golpe]).z
    # se baja con las piernas hasta que el hombro quede a la altura del objetivo (máx. 20 cm). El jab y el recto
    # de Mixamo ya se inclinan y golpean bajo (el hombro casi está a esa altura): como mínimo BAJA_MIN de piernas
    baja_max = 0.0 if objetivo is None else min(max(hombro0 - objetivo, BAJA_MIN), 0.20)
    huesos = HUESOS_PIERNA6 + ([lado_golpe + x for x in ("Arm", "ForeArm", "Hand")] if gancho else [])
    previo = {n: None for n in huesos}
    medida, bajada, aire = {}, 0.0, 1.0
    for f in range(f0, f1 + 1):
        esc.frame_set(f)
        k = curva(f, imp, f1)
        for n in [l + "ToeBase" for l in LADOS]:
            pb[n].rotation_quaternion = BASE[n][1]
        upd()
        sf = suelas()
        pief = {l: pb[l + "Foot"].matrix.translation - Vector((0, 0, sf[l] if sf[l] < 0.015 else min(sf[l], 0.0)))
                for l in LADOS}   # apoyado (menos de 1,5 cm del suelo) -> suela en Z=0; en el aire se deja
        ref = referencia_piernas({n: b.matrix.copy() for n, b in pb.items()}, pief)
        if gancho:   # carga (baja) antes del impacto y empuja hacia arriba hasta el impacto
            dz = 0.05 * rampa(f, [(f0, 0), (max(f0 + 1, imp - 12), 0), (imp - 5, 1), (imp, 0), (f1, 0)])
            kp = curva(f, imp, f1, sube=8, aguanta=2, baja=10)
        else:
            dz = baja_max * k
            kp = k
        M = pb["Hips"].matrix
        pb["Hips"].matrix = Matrix.LocRotScale(M.translation + DELANTE * (paso * 0.5 * kp) - Z * dz, q(M), None)
        upd()
        pies = {lado: pief[lado].copy() for lado in LADOS}
        pies["Left"] += DELANTE * (paso * kp) + Z * (0.03 * math.sin(math.pi * kp))
        bajada = max(bajada, bajar_para_llegar(pies))
        for lado, T in pies.items():
            ik_pierna(lado, T, ref)
        if gancho:
            aire = min(aire, gancho_a_la_cara(lado_golpe, curva(f, imp, f1, sube=8, aguanta=2, baja=10)))
        pb["Hips"].keyframe_insert("location", frame=f, group=pb["Hips"].name)
        for n in huesos:
            previo[n] = clave(pb[n], f, previo[n])
        if f == imp:
            puno = pb[lado_golpe + "Hand"].matrix @ CENTRO_PUNO[lado_golpe]
            MF = pb[lado_golpe + "ForeArm"].matrix
            flex = math.degrees((pb[lado_golpe + "ForeArm"].head - pb[lado_golpe + "Arm"].head).angle(
                pb[lado_golpe + "Hand"].head - pb[lado_golpe + "ForeArm"].head))
            otra = "Right" if lado_golpe == "Left" else "Left"
            medida = dict(hombro=pb[lado_golpe + "Arm"].head.z, puno=puno.z, flex=flex,
                          otra=hueco(guante_mundo(otra, pb[otra + "ForeArm"].matrix, pb[otra + "Hand"].matrix),
                                     pb["Head"].matrix))
    for fc in a.fcurves:
        fc.update()
    txt = (f"  {nombre:26} desde {origen}, impacto fot. {imp} | baja la cadera {baja_max * 100:.0f} cm"
           f" (+{bajada * 100:.1f} para llegar) y la pierna de delante avanza {paso * 100:.0f} cm | en el impacto: hombro"
           f" {medida['hombro']:.2f} m (antes {hombro0:.2f}), puño {medida['puno']:.2f} m (antes {puno0:.2f})")
    if objetivo is not None:
        txt += f", objetivo {objetivo:.2f} m"
    txt += f" | la otra mano a {medida['otra'] * 100:.1f} cm de la cara"
    if gancho:
        txt += (f" | codo doblado {medida['flex']:.0f}° | barbilla del rival a {OBJ_BARBILLA:.2f} m"
                f" | aire guante-cabeza mín. {aire * 100:.1f} cm")
    p(txt)


p("\n=== GOLPES NUEVOS (7, 8, 9 al cuerpo bajando con las piernas; 5 y 6 ganchos a la cara) ===")
p(f"  objetivos (rival del mismo tamaño): plexo/estómago {OBJ_PLEXO:.2f} m, costillas {OBJ_COSTILLAS:.2f} m,"
  f" barbilla {OBJ_BARBILLA:.2f} m")
derivar("jab_v2", "jab_cuerpo", "Left", OBJ_PLEXO)
derivar("recto_v2", "recto_cuerpo", "Right", OBJ_PLEXO)
derivar("crochet_adelantado_v2", "crochet_adelantado_cuerpo", "Left", OBJ_COSTILLAS)
derivar("gancho_adelantado_cuerpo_v2", "gancho_adelantado", "Left", paso=0.05, gancho=True)
derivar("gancho_trasero_cuerpo_v2", "gancho_trasero", "Right", paso=0.05, gancho=True)


# ---------------------------------------------------------------- esquivas laterales
def cabeza_lateral(nombre, f):
    poner(nombre)
    esc.frame_set(1)
    c1 = centro_cabeza().copy()
    esc.frame_set(f)
    d = centro_cabeza() - c1
    return Vector((d.x, d.y, 0)).length, d.z


N_ESQ = 25
p("\n=== ESQUIVAS LATERALES (la cabeza se aparta 20-25 cm y vuelve; pie contrario pivota sin moverse) ===")
for nombre, s in (("esquiva_der", -1.0), ("esquiva_izq", 1.0)):
    opuesto = "Left" if s < 0 else "Right"
    escala = 1.0
    for intento in range(3):
        pose = dict(sx=0.07 * s * escala, lado=14.0 * s * escala, torsion=15.0 * s * escala, giro=8.0 * s * escala,
                    cuello=-8.0 * s * escala, baja=0.04, flex=4.0)

        def pies_esq(f, s=s, opuesto=opuesto):
            k = rampa(f, [(1, 0), (9, 1), (15, 1), (N_ESQ, 0)])
            return dict(rotpie={opuesto: (20.0 * s * k, 15.0 * k)})

        if nombre in bpy.data.actions:
            bpy.data.actions.remove(bpy.data.actions[nombre])
        rep_e = crear(nombre, N_ESQ, [(1, {}), (9, pose), (15, pose), (N_ESQ, {})], "suave", {}, pico=12, pies=pies_esq)
        d, dz = cabeza_lateral(nombre, 12)
        if 0.20 <= d <= 0.25:
            break
        escala *= 0.225 / d
    informe(nombre, N_ESQ, rep_e)
    p(f"     la cabeza se aparta {d * 100:.0f} cm (y baja {-dz * 100:.0f} cm); pivota el pie {NOMBRE_LADO[opuesto]}"
      f" (20° y talón arriba 15°) sin moverse del sitio")

# ---------------------------------------------------------------- ballesteo
N_BAL = 28
p("\n=== BALLESTEO (tronco atrás sin paso; solo el pie de atrás puede retroceder) ===")


def pies_bal(f):
    k, alt = avance(f, 2, 9)
    k2, alt2 = avance(f, 19, 27)
    kk = k * (1 - k2)
    return {"Right": -DELANTE * (0.10 * kk) + Z * (0.03 * (alt + alt2))}


pose_bal = dict(sy=-0.12, flex=-20.0, cabeza=16.0, baja=0.02, wL=1.0, wR=1.0)
rep_b = crear("ballesteo", N_BAL, [(1, {}), (10, pose_bal), (18, pose_bal), (N_BAL, {})], "suave", MANOS_ARRIBA,
              pico=14, pies=pies_bal)
informe("ballesteo", N_BAL, rep_b)
d, dz = cabeza_lateral("ballesteo", 14)
p(f"     la cabeza se echa {d * 100:.0f} cm hacia atrás; el pie de atrás retrocede 10 cm y vuelve; el de delante fijo")

# ---------------------------------------------------------------- parada (mano de atrás)
N_PAR = 18
p("\n=== PARADA (toque corto hacia abajo con la mano de atrás, derecha) ===")
g_par = GUARDIA["Right"][0] + Vector((0.07, -0.07, -0.12))
c_par = GUARDIA["Right"][1] + Vector((0.05, 0.0, -0.03))
pose_par = dict(wR=1.0, torsion=-5.0, lado=-5.0, sx=-0.02, cabeza=2.0)
rep_pa = crear("parada", N_PAR, [(1, {}), (6, pose_par), (9, pose_par), (N_PAR, {})], "suave",
               {"Right": (g_par, c_par)}, pico=7)
informe("parada", N_PAR, rep_pa)
p(f"     la mano se mueve {(g_par - GUARDIA['Right'][0]).length * 100:.0f} cm desde la guardia (un palmo ~20 cm):"
  " hacia dentro, abajo y adelante; la cabeza se aparta un poco a su derecha")

# ---------------------------------------------------------------- pivote
N_PIV = 25
p("\n=== PIVOTE (paso en diagonal con el pie de delante y giro de 45° sobre su punta; acaba girado) ===")
PASO_PIV = (DELANTE + X).normalized() * 0.15
GIRO_PIV = -45.0   # hacia su derecha (sentido horario visto desde arriba): vuelve a encarar al rival


def pies_piv(f):
    k1, a1 = avance(f, 1, 9)
    k2, a2 = avance(f, 9, 24)
    th = GIRO_PIV * k2
    Rz = Quaternion(Z, math.radians(th))
    Bp = BOLA0["Left"] + PASO_PIV * k1
    off_L = PASO_PIV * k1 + Z * (0.035 * a1)
    nb = Bp + Rz @ (BOLA0["Right"] - Bp)
    off_R = nb - BOLA0["Right"] + Z * (0.03 * a2)
    H0 = M0["Hips"].translation
    Hs = H0 + PASO_PIV * (0.6 * k1)
    cad = (Bp + Rz @ (Hs - Bp)) - H0
    return dict(pies={"Left": off_L, "Right": off_R}, cadera=cad, giro=th,
                rotpie={"Left": (th, 10.0 * a2), "Right": (th, 0.0)})


rep_pv = crear("pivote", N_PIV, [(1, {}), (13, dict(baja=0.03)), (N_PIV, {})], "suave", {}, pico=16, pies=pies_piv)
informe("pivote", N_PIV, rep_pv)
poner("pivote")
esc.frame_set(1)
y1 = math.degrees(q(pb["Hips"].matrix).to_euler().z)
h1 = pb["Hips"].head.copy()
esc.frame_set(N_PIV)
y2 = math.degrees(q(pb["Hips"].matrix).to_euler().z)
p(f"     acaba girado {y2 - y1:+.0f}° (negativo = hacia su derecha) y desplazado {(pb['Hips'].head - h1).length * 100:.0f} cm;"
  " el pie de delante gira sobre su punta y el de atrás describe un arco")

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
