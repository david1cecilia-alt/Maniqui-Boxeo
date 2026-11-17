"""Ropa v2 – rehace pantalón, botas y guantes en trabajo/boxeador.blend.

Mallas NUEVAS (no son caras duplicadas del cuerpo):
- Pantalón corto de boxeo: secciones (anillos) sacadas lanzando rayos desde dentro
  de cada pierna, con holgura creciente hacia el bajo, pliegues en la cintura, raja
  lateral y cinturilla gruesa aparte. Pesos: Data Transfer desde el cuerpo + suavizado.
- Botas: envolvente convexa del pie y la pantorrilla, remallada (voxel) y suavizada
  (puntera lisa, sin dedos), suela fina, ribete arriba y cordones delante.
  Pesos: Data Transfer + suavizado. El pie del cuerpo se oculta con el Mask.
- Guantes (~15 cm de ancho): piezas convexas (puño, dedos doblados, pulgar, puño de
  la muñeca, tira de velcro y lengüeta), emparentados al hueso Hand, sin pesos.
Requiere haber ejecutado antes fase2_montar.py. Escribe trabajo/ropa_v2_resumen.txt.

Uso:
  blender.exe --background --python scripts/ropa_v2.py
"""
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun as C  # noqa: E402

BLEND = os.path.join(C.TRABAJO, "boxeador_v2.blend")
P = "mixamorig:"

GRIS_OSCURO = (0.10, 0.10, 0.11, 1.0)
GRIS_CINTURA = (0.16, 0.16, 0.17, 1.0)
ROJO = (0.65, 0.03, 0.03, 1.0)
ROJO_OSCURO = (0.42, 0.02, 0.02, 1.0)
BLANCO = (0.85, 0.85, 0.85, 1.0)
NEGRO = (0.05, 0.05, 0.05, 1.0)

resumen = []


def r(*a):
    linea = " ".join(str(x) for x in a)
    resumen.append(linea)
    print(linea)


def material(nombre, color):
    m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = 0.7
    m.diffuse_color = color
    return m


def objeto(nombre, bm, mats):
    me = bpy.data.meshes.new(nombre)
    bm.to_mesh(me)
    for p in me.polygons:
        p.use_smooth = True
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(nombre, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


# ---------------------------------------------------------------- 0. abrir y limpiar
bpy.ops.wm.open_mainfile(filepath=BLEND)
esc = bpy.context.scene
arm = bpy.data.objects["Boxeador"]
cuerpo = bpy.data.objects["Cuerpo"]
for n in ("Pantalon", "Botas", "Guante_Left", "Guante_Right"):
    ob = bpy.data.objects.get(n)
    if ob:
        me = ob.data
        bpy.data.objects.remove(ob)
        bpy.data.meshes.remove(me)
for n in ("Pantalon", "Botas", "Guantes"):
    if n in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials[n])
arm.data.pose_position = "REST"
bpy.context.view_layer.update()

mw = cuerpo.matrix_world
CO = [mw @ v.co for v in cuerpo.data.vertices]
BVH_CUERPO = BVHTree.FromPolygons(CO, [p.vertices[:] for p in cuerpo.data.polygons])
vg_nombre = {g.index: g.name.split(":")[-1] for g in cuerpo.vertex_groups}
DOM = []
for v in cuerpo.data.vertices:
    gs = [e for e in v.groups if not vg_nombre[e.group].startswith("ocultar")]
    DOM.append(vg_nombre[max(gs, key=lambda e: e.weight).group] if gs else "")


def hueso_w(n, cola=False):
    b = arm.data.bones[P + n]
    return arm.matrix_world @ (b.tail_local if cola else b.head_local)


def rayo(origen, d, maxd=0.6):
    loc, _, _, dist = BVH_CUERPO.ray_cast(origen, d, maxd)
    return dist if loc is not None else None


def casco2d(pts):
    """Envolvente convexa 2D (cadena monótona). pts: lista de (x, y)."""
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts

    def cruz(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    inf, sup = [], []
    for p in pts:
        while len(inf) >= 2 and cruz(inf[-2], inf[-1], p) <= 0:
            inf.pop()
        inf.append(p)
    for p in reversed(pts):
        while len(sup) >= 2 and cruz(sup[-2], sup[-1], p) <= 0:
            sup.pop()
        sup.append(p)
    return inf[:-1] + sup[:-1]


def radio_poligono(c, d, poli):
    """Distancia desde c (dentro del polígono convexo) hasta su borde en la dirección d (2D)."""
    mejor = None
    n = len(poli)
    for i in range(n):
        a, b = Vector(poli[i]), Vector(poli[(i + 1) % n])
        e = b - a
        den = d.x * e.y - d.y * e.x
        if abs(den) < 1e-12:
            continue
        w = a - c
        t = (w.x * e.y - w.y * e.x) / den
        s = (w.x * d.y - w.y * d.x) / den
        if t > 0 and -1e-9 <= s <= 1 + 1e-9:
            mejor = t if mejor is None else min(mejor, t)
    return mejor


def lerp_tabla(z, tabla):
    """tabla: [(z, valor)] con z decreciente."""
    if z >= tabla[0][0]:
        return tabla[0][1]
    for (z0, v0), (z1, v1) in zip(tabla, tabla[1:]):
        if z1 <= z <= z0:
            t = (z0 - z) / (z0 - z1)
            return v0 + (v1 - v0) * t
    return tabla[-1][1]


def suavizar_circular(vals, pasos=2):
    v = np.array(vals, dtype=float)
    for _ in range(pasos):
        v = 0.25 * np.roll(v, 1) + 0.5 * v + 0.25 * np.roll(v, -1)
    return v


# ---------------------------------------------------------------- 1. pantalón
Z_TOP, Z_SPLIT, Z_HEM = 1.035, 0.875, 0.715
Z_RAJA = Z_HEM + 0.07
N = 32
HOLGURA_FUERA = [(1.035, 0.014), (0.95, 0.032), (0.86, 0.044), (0.715, 0.056)]
HOLGURA_DENTRO = [(1.035, 0.010), (0.86, 0.010), (0.715, 0.008)]
niveles = list(np.arange(Z_TOP, Z_HEM - 1e-6, -0.0125)) + [Z_HEM]
up0, up1 = hueso_w("LeftUpLeg"), hueso_w("LeftUpLeg", cola=True)


def centro_pierna(z):
    t = (up0.z - z) / (up0.z - up1.z)
    p = up0.lerp(up1, max(0.0, min(1.0, t)))
    if z > Z_SPLIT:  # en la pelvis: centro de media pelvis
        k = min(1.0, (z - Z_SPLIT) / 0.05)
        p = p.lerp(Vector((0.075, 0.015, z)), k)
    return Vector((p.x, p.y, z))


def anillo_pierna(z):
    """Radios (sin recorte) del anillo izquierdo a la altura z, con holgura."""
    c = centro_pierna(z)
    pelvis = z > Z_SPLIT
    pts2 = []
    for i in range(N):
        th = 2 * math.pi * i / N
        d = Vector((math.cos(th), math.sin(th), 0))
        dist = rayo(c, d)
        if dist is None or (pelvis and d.x < 0 and dist > c.x / max(1e-6, -d.x)):
            dist = c.x / max(1e-6, -d.x) if (pelvis and d.x < 0) else 0.08
        w = max(0.0, min(1.0, (math.cos(th) + 0.8) / 0.6))
        hol = lerp_tabla(z, HOLGURA_DENTRO) + (lerp_tabla(z, HOLGURA_FUERA) - lerp_tabla(z, HOLGURA_DENTRO)) * w
        p = c + d * (dist + hol)
        pts2.append((p.x, p.y))
    casco = casco2d(pts2)
    radios = []
    for i in range(N):
        th = 2 * math.pi * i / N
        d = Vector((math.cos(th), math.sin(th)))
        radios.append(radio_poligono(Vector((c.x, c.y)), d, casco) or 0.08)
    return c, suavizar_circular(radios, 1)


anillos = [anillo_pierna(z) for z in niveles]
R = np.array([a[1] for a in anillos])
for _ in range(2):  # suavizado vertical
    R[1:-1] = 0.25 * R[:-2] + 0.5 * R[1:-1] + 0.25 * R[2:]

bm = bmesh.new()
filas = []
for k, z in enumerate(niveles):
    c = anillos[k][0]
    pelvis = z > Z_SPLIT
    fila = []
    for i in range(N + 1):            # N+1: el primero y el último (lado de fuera) se separan en la raja
        ii = i % N
        th = 2 * math.pi * i / N
        if z < Z_RAJA and i in (0, N):
            abre = 0.05 * (Z_RAJA - z) / (Z_RAJA - Z_HEM)
            th += abre if i == 0 else -abre
        rad = R[k][ii]
        rad += 0.004 * max(0.0, min(1.0, (z - 0.94) / (Z_TOP - 0.94))) * math.sin(12 * th)  # pliegues
        d = Vector((math.cos(th), math.sin(th), 0))
        p = c + d * rad
        if d.x < 0:  # lado de dentro: no cruzar el plano medio
            if pelvis:
                p = c + d * min(rad, c.x / -d.x)
            p.x = max(p.x, 0.0 if pelvis else 0.004)
        fila.append(bm.verts.new(p))
    filas.append(fila)
for k in range(len(filas) - 1):
    for i in range(N):
        bm.faces.new((filas[k][i], filas[k][i + 1], filas[k + 1][i + 1], filas[k + 1][i]))
# lado derecho = espejo exacto
espejo = {}
for v in list(bm.verts):
    espejo[v] = bm.verts.new((-v.co.x, v.co.y, v.co.z))
for f in list(bm.faces):
    bm.faces.new([espejo[v] for v in reversed(f.verts)])
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
interior = [f for f in bm.faces if all(abs(v.co.x) < 1e-6 for v in f.verts)]
bmesh.ops.delete(bm, geom=interior, context="FACES")
bm.normal_update()
# normales hacia fuera (comprobación con el centro de cada pierna)
def centro_lado(p):
    c = centro_pierna(p.z)
    return Vector((math.copysign(c.x, p.x), c.y, c.z))


afuera = sum(1 for f in bm.faces if (f.calc_center_median() - centro_lado(f.calc_center_median())).dot(f.normal) > 0)
if afuera < len(bm.faces) / 2:
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
n_pierna = len(bm.faces)

# cinturilla: anillo completo, gruesa y lisa
NC = 64
# la parte baja más ancha: tapa el borde fruncido (pliegues) de arriba del pantalón
perfil = [(0.975, 0.018), (0.979, 0.029), (0.990, 0.032), (1.025, 0.027), (1.052, 0.022),
          (1.061, 0.016), (1.065, 0.009)]
cc = Vector((0.0, 0.012, 0))
filas_c = []
for z, hol in perfil:
    pts2 = []
    for i in range(NC):
        th = 2 * math.pi * i / NC
        d = Vector((math.cos(th), math.sin(th), 0))
        dist = rayo(Vector((cc.x, cc.y, z)), d) or 0.15
        p = Vector((cc.x, cc.y, z)) + d * (dist + hol)
        pts2.append((p.x, p.y))
    casco = casco2d(pts2)
    fila = []
    for i in range(NC):
        th = 2 * math.pi * i / NC
        d2 = Vector((math.cos(th), math.sin(th)))
        rad = radio_poligono(Vector((cc.x, cc.y)), d2, casco) or 0.15
        fila.append(bm.verts.new((cc.x + d2.x * rad, cc.y + d2.y * rad, z)))
    filas_c.append(fila)
caras_c = []
for k in range(len(filas_c) - 1):
    for i in range(NC):
        j = (i + 1) % NC
        caras_c.append(bm.faces.new((filas_c[k][i], filas_c[k + 1][i], filas_c[k + 1][j], filas_c[k][j])))
bm.normal_update()
if sum(1 for f in caras_c if (f.calc_center_median() - Vector((0, 0.012, f.calc_center_median().z))).dot(f.normal) > 0) < len(caras_c) / 2:
    bmesh.ops.reverse_faces(bm, faces=caras_c)
m_pant, m_cint = material("Pantalon", GRIS_OSCURO), material("Pantalon_cintura", GRIS_CINTURA)
for f in caras_c:
    f.material_index = 1
pantalon = objeto("Pantalon", bm, [m_pant, m_cint])
bm.free()

# ---------------------------------------------------------------- 2. botas
Z_BOTA = 0.31


def remallar(ob, voxel):
    md = ob.modifiers.new("Remesh", "REMESH")
    md.mode = "VOXEL"
    md.voxel_size = voxel
    md.adaptivity = 0.0
    with bpy.context.temp_override(object=ob, active_object=ob):
        bpy.ops.object.modifier_apply(modifier=md.name)


def bota(lado):
    s = 1 if lado == "Left" else -1
    lado_ok = [i for i in range(len(CO)) if CO[i].x * s > 0.02]
    # dos envolventes convexas (caña y pie) que el remallado une: así no se rellena el empeine
    cana = [CO[i] for i in lado_ok if DOM[i] == lado + "Leg" and 0.06 <= CO[i].z <= Z_BOTA]
    pie = [CO[i] for i in lado_ok if (DOM[i] in (lado + "Foot", lado + "ToeBase")) or
           (DOM[i] == lado + "Leg" and CO[i].z < 0.12)]
    tmp_bm = bmesh.new()
    for pts in (cana, pie):
        bm = bmesh.new()
        for p in pts:
            bm.verts.new(p)
        res = bmesh.ops.convex_hull(bm, input=bm.verts)
        sobran = {v for v in res["geom_interior"] + res["geom_unused"] if isinstance(v, bmesh.types.BMVert)}
        bmesh.ops.delete(bm, geom=list(sobran), context="VERTS")
        bm.normal_update()
        for v in bm.verts:
            v.co += v.normal * 0.010
        me_tmp = bpy.data.meshes.new("tmp")
        bm.to_mesh(me_tmp)
        bm.free()
        tmp_bm.from_mesh(me_tmp)
        bpy.data.meshes.remove(me_tmp)
    tmp = objeto("tmp_bota", tmp_bm, [])
    tmp_bm.free()
    remallar(tmp, 0.007)
    bm = bmesh.new()
    bm.from_mesh(tmp.data)
    me_tmp = tmp.data
    bpy.data.objects.remove(tmp)
    bpy.data.meshes.remove(me_tmp)
    for _ in range(8):
        bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * 0.003
        if v.co.z < -0.004:
            v.co.z = -0.008       # planta plana encima de la suela
    # abrir arriba
    corte = max(v.co.z for v in bm.verts) - 0.012
    arriba = [f for f in bm.faces if f.calc_center_median().z > corte]
    bmesh.ops.delete(bm, geom=arriba, context="FACES")
    bm.normal_update()
    caras_bota = list(bm.faces)
    # suela fina: prisma con el contorno de la planta
    planta = [(v.co.x, v.co.y) for v in bm.verts if v.co.z < 0.012]
    casco = casco2d(planta)
    cx = sum(p[0] for p in casco) / len(casco)
    cy = sum(p[1] for p in casco) / len(casco)
    abajo, encima = [], []
    for x, y in casco:
        d = Vector((x - cx, y - cy))
        d = d.normalized() * (d.length + 0.004)
        abajo.append(bm.verts.new((cx + d.x, cy + d.y, -0.018)))
        encima.append(bm.verts.new((cx + d.x, cy + d.y, -0.006)))
    caras_suela = [bm.faces.new(list(reversed(abajo))), bm.faces.new(encima)]
    for i in range(len(casco)):
        j = (i + 1) % len(casco)
        caras_suela.append(bm.faces.new((abajo[i], abajo[j], encima[j], encima[i])))
    # ribete: tubo alrededor del borde de arriba
    borde = [v for v in bm.verts if v.is_boundary]
    lc = hueso_w(lado + "Leg").lerp(hueso_w(lado + "Leg", cola=True), (hueso_w(lado + "Leg").z - Z_BOTA) /
                                    (hueso_w(lado + "Leg").z - hueso_w(lado + "Leg", cola=True).z))
    NR, NP = 32, 8
    radios = [[] for _ in range(NR)]
    zr = sum(v.co.z for v in borde) / len(borde)
    for v in borde:
        a = math.atan2(v.co.y - lc.y, v.co.x - lc.x) % (2 * math.pi)
        radios[int(a / (2 * math.pi) * NR) % NR].append(math.hypot(v.co.x - lc.x, v.co.y - lc.y))
    media = np.mean([np.mean(x) for x in radios if x])
    radios = suavizar_circular([np.mean(x) if x else media for x in radios], 2)
    anillo = []
    for i in range(NR):
        a = 2 * math.pi * i / NR
        d = Vector((math.cos(a), math.sin(a), 0))
        fila = []
        for j in range(NP):
            b = 2 * math.pi * j / NP
            p = Vector((lc.x, lc.y, zr)) + d * (radios[i] + 0.002 + 0.006 * math.cos(b)) + Vector((0, 0, 0.007 * math.sin(b)))
            fila.append(bm.verts.new(p))
        anillo.append(fila)
    caras_ribete = []
    for i in range(NR):
        for j in range(NP):
            caras_ribete.append(bm.faces.new((anillo[i][j], anillo[(i + 1) % NR][j],
                                              anillo[(i + 1) % NR][(j + 1) % NP], anillo[i][(j + 1) % NP])))
    bm.normal_update()
    if sum(1 for f in caras_ribete if (f.calc_center_median() - Vector((lc.x, lc.y, f.calc_center_median().z))).dot(f.normal) > 0) < len(caras_ribete) / 2:
        bmesh.ops.reverse_faces(bm, faces=caras_ribete)
    # cordones: cruces delante de la caña
    bvh = BVHTree.FromBMesh(bm)
    l0, l1 = hueso_w(lado + "Leg"), hueso_w(lado + "Leg", cola=True)
    ojales = []
    for z in np.arange(0.105, Z_BOTA - 0.015, 0.021):
        t = (l0.z - z) / (l0.z - l1.z)
        xc = l0.lerp(l1, t).x
        loc, nor, _, _ = bvh.ray_cast(Vector((xc, -0.5, z)), Vector((0, 1, 0)))
        if loc is None:
            continue
        lat = Vector((0, 0, 1)).cross(nor).normalized()
        base = loc + nor * 0.003
        ojales.append((base + lat * 0.012, base - lat * 0.012))
    caras_cordon = []
    for (a1, b1), (a2, b2) in zip(ojales, ojales[1:]):
        for p, q in ((a1, b2), (b1, a2)):
            eje = q - p
            cil = bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.0025, radius2=0.0025,
                                        depth=eje.length)
            rot = eje.to_track_quat("Z", "Y").to_matrix().to_4x4()
            bmesh.ops.transform(bm, verts=cil["verts"], matrix=Matrix.Translation((p + q) / 2) @ rot)
            caras_cordon += list({f for v in cil["verts"] for f in v.link_faces})
    for f in caras_suela:
        f.material_index = 1
    for f in caras_cordon:
        f.material_index = 2
    for f in caras_ribete:
        f.material_index = 3
    return bm


m_bota, m_suela = material("Botas", ROJO), material("Botas_suela", NEGRO)
m_cordon, m_ribete = material("Botas_cordones", BLANCO), material("Botas_ribete", ROJO_OSCURO)
bm = bmesh.new()
for lado in ("Left", "Right"):
    b = bota(lado)
    me_tmp = bpy.data.meshes.new("tmp")
    b.to_mesh(me_tmp)
    b.free()
    bm.from_mesh(me_tmp)
    bpy.data.meshes.remove(me_tmp)
botas = objeto("Botas", bm, [m_bota, m_suela, m_cordon, m_ribete])
bm.free()


# ---------------------------------------------------------------- 3. pesos (Data Transfer + suavizado)
def pesos(ob, iteraciones):
    for g in cuerpo.vertex_groups:
        if not g.name.startswith("ocultar"):
            ob.vertex_groups.new(name=g.name)
    dt = ob.modifiers.new("Pesos", "DATA_TRANSFER")
    dt.object = cuerpo
    dt.use_vert_data = True
    dt.data_types_verts = {"VGROUP_WEIGHTS"}
    dt.vert_mapping = "POLYINTERP_NEAREST"
    dt.layers_vgroup_select_src = "ALL"
    dt.layers_vgroup_select_dst = "NAME"
    with bpy.context.temp_override(object=ob, active_object=ob):
        bpy.ops.object.modifier_apply(modifier=dt.name)
    me = ob.data
    n, g = len(me.vertices), len(ob.vertex_groups)
    W = np.zeros((n, g))
    for v in me.vertices:
        for e in v.groups:
            W[v.index, e.group] = e.weight
    ed = np.array([e.vertices[:] for e in me.edges])
    grado = np.bincount(ed.ravel(), minlength=n).astype(float)
    grado[grado == 0] = 1
    for _ in range(iteraciones):
        S = np.zeros_like(W)
        np.add.at(S, ed[:, 0], W[ed[:, 1]])
        np.add.at(S, ed[:, 1], W[ed[:, 0]])
        W = 0.5 * W + 0.5 * S / grado[:, None]
    W[W < 0.01] = 0
    W /= np.maximum(W.sum(axis=1, keepdims=True), 1e-9)
    for gi, vg in enumerate(ob.vertex_groups):
        vg.remove(list(range(n)))
        for vi in np.nonzero(W[:, gi])[0]:
            vg.add([int(vi)], float(W[vi, gi]), "REPLACE")
    ob.parent = arm
    ob.matrix_parent_inverse = arm.matrix_world.inverted()
    am = ob.modifiers.new("Armature", "ARMATURE")
    am.object = arm
    return ob


pesos(pantalon, 25)
sub = pantalon.modifiers.new("Suavizar", "SUBSURF")
sub.levels = sub.render_levels = 1
so = pantalon.modifiers.new("Grosor", "SOLIDIFY")
so.thickness, so.offset = 0.004, 1.0
pesos(botas, 6)
so = botas.modifiers.new("Grosor", "SOLIDIFY")
so.thickness, so.offset = 0.004, -1.0

# ---------------------------------------------------------------- 4. guantes
m_guante, m_tira, m_velcro = material("Guantes", ROJO), material("Guantes_tira", ROJO_OSCURO), material("Guantes_velcro", BLANCO)


def supercuadrica(bm, centro, semi, eps, rot=None, conico=0.0, mat=0, u=36, v=24):
    """Pieza convexa: esfera deformada (exponentes < 1 = más cuadrada).
    conico: estrecha X/Z hacia y negativa (hacia la muñeca)."""
    res = bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=1.0)
    for vt in res["verts"]:
        x, y, z = vt.co.normalized()
        p = Vector((math.copysign(abs(x) ** eps[0], x) * semi[0],
                    math.copysign(abs(y) ** eps[1], y) * semi[1],
                    math.copysign(abs(z) ** eps[2], z) * semi[2]))
        if conico:
            f = 1.0 - conico * (1 - (p.y / semi[1] + 1) / 2)
            p.x *= f
            p.z *= f
        if rot:
            p = rot @ p
        vt.co = Vector(centro) + p
    for f in {f for vt in res["verts"] for f in vt.link_faces}:
        f.material_index = mat


def matriz_hueso(nombre):
    m = arm.matrix_world @ arm.data.bones[nombre].matrix_local
    return Matrix.LocRotScale(m.translation, m.to_quaternion(), None)


def guante(lado):
    """Ejes locales del hueso Hand: Y = hacia los dedos, +Z = palma, pulgar en X (- izq., + der.)."""
    t = -1 if lado == "Left" else 1
    hn = P + lado + "Hand"
    bm = bmesh.new()
    supercuadrica(bm, (0, 0.110, 0.006), (0.066, 0.092, 0.058), (0.75, 0.8, 0.75), conico=0.2)   # puño
    supercuadrica(bm, (0, 0.165, 0.040), (0.062, 0.040, 0.030), (0.8, 1.0, 1.0))                # dedos doblados
    rot = Matrix.Rotation(math.radians(-12), 3, "X") @ Matrix.Rotation(math.radians(8 * t), 3, "Z")
    supercuadrica(bm, (0.060 * t, 0.095, 0.026), (0.023, 0.048, 0.024), (1.0, 0.9, 1.0), rot=rot)  # pulgar
    supercuadrica(bm, (0, -0.025, 0), (0.053, 0.070, 0.048), (1.0, 0.25, 1.0))                  # puño muñeca
    supercuadrica(bm, (0, -0.035, 0), (0.057, 0.024, 0.052), (1.0, 0.2, 1.0), mat=1)            # tira velcro
    supercuadrica(bm, (0, -0.035, -0.056), (0.024, 0.020, 0.006), (0.3, 0.3, 0.5), mat=2, u=16, v=12)  # lengüeta
    bm.normal_update()
    vs = [v.co.x for v in bm.verts]
    ancho = max(vs) - min(vs)
    largo = max(v.co.y for v in bm.verts) - min(v.co.y for v in bm.verts)
    Mh = matriz_hueso(hn)
    bmesh.ops.transform(bm, verts=bm.verts, matrix=Mh)
    ob = objeto("Guante_" + lado, bm, [m_guante, m_tira, m_velcro])
    bm.free()
    hueso = arm.data.bones[hn]
    ob.parent = arm
    ob.parent_type = "BONE"
    ob.parent_bone = hn
    ob.matrix_parent_inverse = (arm.matrix_world @ hueso.matrix_local
                                @ Matrix.Translation((0, hueso.length, 0))).inverted()
    return ob, ancho, largo


r("=== ROPA V2 ===")
for lado in ("Left", "Right"):
    g, ancho, largo = guante(lado)
    r(f"  Guante_{lado}: {len(g.data.polygons)} caras, {ancho * 100:.1f} cm de ancho, {largo * 100:.1f} cm de largo"
      f" (6 piezas convexas), emparentado a {P}{lado}Hand, sin pesos")

# ---------------------------------------------------------------- 5. Mask: manos + pies dentro de las botas
for g in [g for g in cuerpo.vertex_groups if g.name.startswith("ocultar")]:
    cuerpo.vertex_groups.remove(g)
vg = cuerpo.vertex_groups.new(name="ocultar")
gi = {g.index: g.name.split(":")[-1] for g in cuerpo.vertex_groups}
n_pie = 0
for v in cuerpo.data.vertices:
    w = 0.0
    for e in v.groups:
        n = gi[e.group]
        if n in ("LeftHand", "RightHand"):
            w = max(w, e.weight)
    if DOM[v.index] in ("LeftFoot", "RightFoot", "LeftToeBase", "RightToeBase") or \
            (DOM[v.index] in ("LeftLeg", "RightLeg") and CO[v.index].z < Z_BOTA - 0.04):
        w = 1.0
        n_pie += 1
    if w > 0:
        vg.add([v.index], w, "REPLACE")
mk = next(m for m in cuerpo.modifiers if m.type == "MASK")
mk.vertex_group = vg.name
r(f"  Cuerpo: Mask con el grupo 'ocultar' (manos con peso > 0.5 y {n_pie} vértices de pies/tobillos dentro de las botas)")

# ---------------------------------------------------------------- 6. resumen y guardar
arm.data.pose_position = "POSE"
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
for ob in (pantalon, botas):
    me = ob.evaluated_get(dg).to_mesh()
    r(f"  {ob.name}: {len(ob.data.polygons)} caras base -> {len(me.polygons)} con modificadores"
      f" ({', '.join(m.type for m in ob.modifiers)})")
    ob.evaluated_get(dg).to_mesh_clear()
r(f"  Pantalón: bajo a z={Z_HEM} m (medio muslo), raja lateral de {(Z_RAJA - Z_HEM) * 100:.0f} cm,"
  f" holgura {HOLGURA_FUERA[0][1] * 100:.1f}-{HOLGURA_FUERA[-1][1] * 100:.1f} cm, cinturilla 7 cm; pesos suavizados x25")
r(f"  Botas: caña hasta z={Z_BOTA} m (media pantorrilla), suela 1,2 cm, ribete, cordones; pesos suavizados x6")
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
r("GUARDADO", os.path.relpath(BLEND, C.RAIZ))
with open(os.path.join(C.TRABAJO, "ropa_v2_resumen.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(resumen) + "\n")
