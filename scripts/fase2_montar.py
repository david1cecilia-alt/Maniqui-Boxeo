"""Fase 2 – monta trabajo/boxeador.blend a partir de los FBX de Mixamo.

- Un esqueleto, una malla de cuerpo (+ Eyes y Eyebrows); se borra Cube.
- Cada FBX -> una acción con Fake User, con nombre limpio.
- Esquivas en el sitio: se quita el desplazamiento horizontal (X/Y) de la cadera.
- Pantalón y botas sacados de la malla del cuerpo (Displace + Solidify,
  pesos con Data Transfer, Armature).
- Guantes: malla aparte emparentada al hueso Hand; las manos se ocultan con Mask.
- Animaciones nuevas (flexion, paso_atras, rueda) con IK temporal en las
  piernas, horneadas a fotogramas Bezier.
Escribe trabajo/fase2_resumen.txt.

Uso:
  blender.exe --background --python scripts/fase2_montar.py
"""
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun as C  # noqa: E402

BLEND = os.path.join(C.TRABAJO, "boxeador.blend")
P = "mixamorig:"

# nombre lógico del FBX (comun.FBX) -> nombre de la acción en el .blend
ACCIONES = {
    "guardia": "guardia",
    "guardia_alt": "guardia_alt",
    "jab": "jab",
    "recto": "recto",
    "crochet_adelantado": "crochet_adelantado",
    "crochet_trasero": "crochet_trasero",
    "gancho_adelantado_cuerpo": "gancho_adelantado_cuerpo",
    "gancho_trasero_cuerpo": "gancho_trasero_cuerpo",
    "crochet_cuerpo": "crochet_trasero_cuerpo",
    "bloqueo": "bloqueo",
    "esquiva_avanzando": "esquiva_avanzando",
    "esquiva_retrocediendo": "esquiva_retrocediendo",
}
ESQUIVAS = ["esquiva_avanzando", "esquiva_retrocediendo"]

GRIS_OSCURO = (0.10, 0.10, 0.11, 1.0)
ROJO = (0.65, 0.03, 0.03, 1.0)
PIEL = (0.75, 0.62, 0.5, 1.0)

resumen = []


def r(*a):
    linea = " ".join(str(x) for x in a)
    resumen.append(linea)
    print(linea)


def fmt(v):
    return "(" + ", ".join(f"{x:+.3f}" for x in v) + ")"


def activar(obj):
    vl = bpy.context.view_layer
    for o in vl.objects:
        o.select_set(False)
    obj.select_set(True)
    vl.objects.active = obj


def asignar_accion(arm, act):
    arm.animation_data.action = act
    if arm.animation_data.action_slot is None and len(act.slots):
        arm.animation_data.action_slot = act.slots[0]


def material(nombre, color):
    m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = 0.6
    m.diffuse_color = color  # color en el visor / Workbench
    return m


# ---------------------------------------------------------------- 1. base
arm, mallas = C.importar("guardia")
esc = bpy.context.scene
for o in list(bpy.data.objects):   # fuera Cube (vacío) y la cámara/luz del FBX
    if o.name.startswith("Cube") or o.type in ("CAMERA", "LIGHT"):
        bpy.data.objects.remove(o)
cuerpo = next(o for o in bpy.data.objects if o.name.startswith("SuperHero"))
arm.name = "Boxeador"
arm.data.name = "Boxeador"
cuerpo.name = "Cuerpo"

act = arm.animation_data.action
act.name = "guardia"
act.use_fake_user = True

# ---------------------------------------------------------------- 2. acciones
for clave, nombre in ACCIONES.items():
    if clave == "guardia":
        continue
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=C.FBX[clave])
    nuevos = [o for o in bpy.data.objects if o not in antes]
    arm2 = next(o for o in nuevos if o.type == "ARMATURE")
    assert [b.name for b in arm2.data.bones] == [b.name for b in arm.data.bones], clave
    a = arm2.animation_data.action
    a.name = nombre
    a.use_fake_user = True
    for o in nuevos:
        datos = o.data
        bpy.data.objects.remove(o)
        if isinstance(datos, bpy.types.Mesh) and datos.users == 0:
            bpy.data.meshes.remove(datos)
        elif isinstance(datos, bpy.types.Armature) and datos.users == 0:
            bpy.data.armatures.remove(datos)
bpy.data.orphans_purge(do_recursive=True)

r("=== 1. ACCIONES EN boxeador.blend ===")
for a in sorted(bpy.data.actions, key=lambda a: a.name):
    r(f"  {a.name:24} fot. {int(a.frame_range[0])}-{int(a.frame_range[1])}  fake_user={a.use_fake_user}")
r("Objetos:", sorted(o.name for o in bpy.data.objects))

# ---------------------------------------------------------------- 3. esquivas en el sitio
hips = arm.pose.bones[P + "Hips"]
M_hips = arm.matrix_world @ arm.data.bones[P + "Hips"].matrix_local
A = M_hips.to_3x3()          # loc local de Hips -> desplazamiento en el mundo
b0 = M_hips.translation


def loc_a_mundo(loc):
    return A @ Vector(loc) + b0


def mundo_a_loc(p):
    return A.inverted() @ (Vector(p) - b0)


r("\n=== 2. ESQUIVAS EN EL SITIO (cadera, mundo) ===")
ruta = f'pose.bones["{P}Hips"].location'
for nombre in ESQUIVAS:
    a = bpy.data.actions[nombre]
    fcs = [a.fcurves.find(ruta, index=i) for i in range(3)]
    fotos = sorted({round(k.co.x) for fc in fcs for k in fc.keyframe_points})
    w = {f: loc_a_mundo([fc.evaluate(f) for fc in fcs]) for f in fotos}
    x0, y0 = w[fotos[0]].x, w[fotos[0]].y
    antes = (min(p.x for p in w.values()), max(p.x for p in w.values()),
             min(p.y for p in w.values()), max(p.y for p in w.values()))
    nuevo = {f: mundo_a_loc(Vector((x0, y0, p.z))) for f, p in w.items()}
    for i, fc in enumerate(fcs):
        for k in fc.keyframe_points:
            v = nuevo[round(k.co.x)][i]
            d = v - k.co.y
            k.co.y = v
            k.handle_left.y += d
            k.handle_right.y += d
        fc.update()
    w2 = [loc_a_mundo([fc.evaluate(f) for fc in fcs]) for f in fotos]
    r(f"  {nombre}: antes X[{antes[0]:+.3f},{antes[1]:+.3f}] Y[{antes[2]:+.3f},{antes[3]:+.3f}]"
      f" -> después X[{min(p.x for p in w2):+.3f},{max(p.x for p in w2):+.3f}]"
      f" Y[{min(p.y for p in w2):+.3f},{max(p.y for p in w2):+.3f}]"
      f" | Z[{min(p.z for p in w2):.3f},{max(p.z for p in w2):.3f}] (sin cambios)")

# ---------------------------------------------------------------- 4. ropa
asignar_accion(arm, bpy.data.actions["guardia"])
arm.data.pose_position = "REST"
bpy.context.view_layer.update()

cuerpo.data.materials[0].diffuse_color = PIEL
for o in bpy.data.objects:
    if o.name.startswith("Eyebrows"):
        o.data.materials[0].diffuse_color = (0.08, 0.05, 0.03, 1.0)


def prenda(nombre, zmin, zmax, despl, grosor, mat):
    ob = cuerpo.copy()
    ob.data = cuerpo.data.copy()
    ob.name = ob.data.name = nombre
    esc.collection.objects.link(ob)
    ob.modifiers.clear()
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    mw = cuerpo.matrix_world
    fuera = [f for f in bm.faces if not all(zmin <= (mw @ v.co).z <= zmax for v in f.verts)]
    bmesh.ops.delete(bm, geom=fuera, context="FACES")
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    # pesos: Data Transfer desde el cuerpo (en reposo) y se aplica
    dt = ob.modifiers.new("Pesos", "DATA_TRANSFER")
    dt.object = cuerpo
    dt.use_vert_data = True
    dt.data_types_verts = {"VGROUP_WEIGHTS"}
    dt.vert_mapping = "POLYINTERP_NEAREST"
    dt.layers_vgroup_select_src = "ALL"
    dt.layers_vgroup_select_dst = "NAME"
    with bpy.context.temp_override(object=ob, active_object=ob):
        bpy.ops.object.modifier_apply(modifier=dt.name)
    d = ob.modifiers.new("Holgura", "DISPLACE")
    d.direction = "NORMAL"
    d.mid_level = 0.0
    d.strength = despl
    s = ob.modifiers.new("Grosor", "SOLIDIFY")
    s.thickness = grosor
    s.offset = 1.0
    s.use_even_offset = False  # con True salen pinchos en las esquinas de la suela
    am = ob.modifiers.new("Armature", "ARMATURE")
    am.object = arm
    for p in ob.data.polygons:
        p.use_smooth = True
    r(f"  {nombre}: {len(ob.data.vertices)} vért, z en [{zmin}, {zmax}] m, Displace {despl} m, Solidify {grosor} m")
    return ob


r("\n=== 3. ROPA Y GUANTES ===")
pantalon = prenda("Pantalon", 0.24, 1.05, 0.006, 0.004, material("Pantalon", GRIS_OSCURO))
botas = prenda("Botas", -1.0, 0.27, 0.012, 0.006, material("Botas", ROJO))

# ---------------------------------------------------------------- 5. guantes + Mask
mat_guante = material("Guantes", ROJO)
mw = cuerpo.matrix_world


def matriz_hueso(nombre):
    """Matriz mundo del hueso en reposo, sin escala (metros)."""
    m = arm.matrix_world @ arm.data.bones[nombre].matrix_local
    return Matrix.LocRotScale(m.translation, m.to_quaternion(), None)


def guante(lado):
    hn = P + lado + "Hand"
    Mh = matriz_hueso(hn)
    inv = Mh.inverted()
    g = cuerpo.vertex_groups[hn].index
    pts = [inv @ (mw @ v.co) for v in cuerpo.data.vertices
           for e in v.groups if e.group == g and e.weight > 0.5]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c = (mn + mx) / 2
    rad = (mx - mn) / 2
    bm = bmesh.new()
    # puño: elipsoide algo mayor que la mano
    esf = bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=20, radius=1.0)
    rx, ry, rz = rad.x * 1.30 + 0.015, rad.y * 1.05 + 0.02, rad.z * 1.30 + 0.015
    bmesh.ops.transform(bm, verts=esf["verts"],
                        matrix=Matrix.Translation(c + Vector((0, 0.01, 0)))
                        @ Matrix.Diagonal((rx, ry, rz, 1)))
    # puño del guante: cilindro que pasa la muñeca (y<0 = antebrazo)
    y_ini, y_fin = -0.08, c.y
    rc = max(rad.x, rad.z) * 0.95
    cil = bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=rc, radius2=rc * 1.05,
                                depth=y_fin - y_ini)
    bmesh.ops.transform(bm, verts=cil["verts"],
                        matrix=Matrix.Translation((0, (y_ini + y_fin) / 2, 0)) @ Matrix.Rotation(-1.5708, 4, "X"))
    bmesh.ops.transform(bm, verts=bm.verts, matrix=Mh)  # a coordenadas mundo (reposo)
    me = bpy.data.meshes.new("Guante_" + lado)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat_guante)
    ob = bpy.data.objects.new("Guante_" + lado, me)
    esc.collection.objects.link(ob)
    hueso = arm.data.bones[hn]
    ob.parent = arm
    ob.parent_type = "BONE"
    ob.parent_bone = hn
    ob.matrix_parent_inverse = (arm.matrix_world @ hueso.matrix_local
                                @ Matrix.Translation((0, hueso.length, 0))).inverted()
    r(f"  Guante_{lado}: hueso {hn}, mano {2*rad.x:.3f}x{2*rad.y:.3f}x{2*rad.z:.3f} m,"
      f" cubre desde {-y_ini:.2f} m antes de la muñeca, sin pesos")
    return ob


guante_L = guante("Left")
guante_R = guante("Right")

# Mask: oculta las manos del cuerpo (lo de dentro del guante)
vg = cuerpo.vertex_groups.new(name="ocultar_manos")
gi = {cuerpo.vertex_groups[P + "LeftHand"].index, cuerpo.vertex_groups[P + "RightHand"].index}
for v in cuerpo.data.vertices:
    w = max((e.weight for e in v.groups if e.group in gi), default=0.0)
    if w > 0:
        vg.add([v.index], w, "REPLACE")
mk = cuerpo.modifiers.new("Ocultar manos", "MASK")
mk.mode = "VERTEX_GROUP"
mk.vertex_group = vg.name
mk.invert_vertex_group = True
mk.threshold = 0.5
while cuerpo.modifiers[0] != mk:
    with bpy.context.temp_override(object=cuerpo):
        bpy.ops.object.modifier_move_up(modifier=mk.name)
r("  Cuerpo: Mask 'Ocultar manos' (peso Hand > 0.5), modificadores:", [m.type for m in cuerpo.modifiers])

arm.data.pose_position = "POSE"
bpy.context.view_layer.update()

# ---------------------------------------------------------------- 6. ¿guantes uno dentro del otro?


def bvh(ob):
    m = ob.matrix_world
    me = ob.data
    return BVHTree.FromPolygons([m @ v.co for v in me.vertices], [p.vertices[:] for p in me.polygons])


def penetracion(a, b):
    """Profundidad máxima (m) de vértices de a dentro de b."""
    tb = bvh(b)
    m = a.matrix_world
    peor = 0.0
    for v in a.data.vertices:
        p = m @ v.co
        loc, nor, _, dist = tb.find_nearest(p)
        if loc is not None and (p - loc).dot(nor) < 0:
            peor = max(peor, dist)
    return peor


r("\n=== 4. GUANTES EN LA GUARDIA: ¿SE METEN UNO EN EL OTRO? ===")
choques = {}
for nombre in ("guardia", "guardia_alt"):
    a = bpy.data.actions[nombre]
    asignar_accion(arm, a)
    f0, f1 = int(a.frame_range[0]), int(a.frame_range[1])
    fot, peor, peor_f = [], 0.0, None
    for f in range(f0, f1 + 1):
        esc.frame_set(f)
        if bvh(guante_L).overlap(bvh(guante_R)):
            fot.append(f)
            d = max(penetracion(guante_L, guante_R), penetracion(guante_R, guante_L))
            if d > peor:
                peor, peor_f = d, f
    esc.frame_set(1)
    dist = (guante_L.matrix_world.translation - guante_R.matrix_world.translation).length
    if fot:
        r(f"  {nombre}: SÍ se tocan/cruzan en {len(fot)} de {f1 - f0 + 1} fotogramas"
          f" ({fot[0]}-{fot[-1]}); penetración máx. {peor * 100:.1f} cm en el fot. {peor_f}")
    else:
        r(f"  {nombre}: NO se cruzan en ningún fotograma ({f1 - f0 + 1} fot.)")
    choques[nombre] = (fot, peor, peor_f)
r("  (Postura de guardia SIN corregir, como se pidió.)")

# ---------------------------------------------------------------- 7. animaciones nuevas con IK
asignar_accion(arm, bpy.data.actions["guardia"])
esc.frame_set(1)
base = {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy(), pb.scale.copy()) for pb in arm.pose.bones}
ref_f1 = {n: arm.matrix_world @ arm.pose.bones[P + n].head
          for n in ("Hips", "LeftHand", "RightHand", "LeftLeg", "RightLeg", "LeftToeBase", "RightToeBase")}
DELANTE = Vector((0, -1, 0))     # el muñeco mira hacia -Y
ATRAS = -DELANTE
SU_DERECHA = Vector((-1, 0, 0))  # su izquierda es +X


def signed_angle(u, v, normal):
    ang = u.angle(v)
    if u.cross(v).angle(normal) < 1:
        ang = -ang
    return ang


def pole_angle(base_b, ik_b, pole_loc):
    pole_normal = (ik_b.tail - base_b.head).cross(pole_loc - base_b.head)
    proj = pole_normal.cross(base_b.tail - base_b.head)
    return signed_angle(base_b.x_axis, proj, base_b.tail - base_b.head)


def pose_base():
    for pb in arm.pose.bones:
        l, q, s = base[pb.name]
        pb.location, pb.rotation_quaternion, pb.scale = l, q, s


def crear_animacion(nombre, n_fot, cadera, pie_L, pie_R):
    """cadera/pie_*: {fotograma: desplazamiento en el mundo (m)} respecto al fot. 1 de guardia."""
    tmp = bpy.data.actions.new("tmp_" + nombre)
    arm.animation_data.action = tmp
    arm.animation_data.action_slot = None
    pose_base()
    for pb in arm.pose.bones:
        for ruta_k in ("location", "rotation_quaternion", "scale"):
            pb.keyframe_insert(ruta_k, frame=1)
    if arm.animation_data.action_slot is None and len(tmp.slots):
        arm.animation_data.action_slot = tmp.slots[0]
    esc.frame_set(1)
    # cadera
    hp = arm.pose.bones[P + "Hips"]
    for f, d in cadera.items():
        hp.location = base[hp.name][0] + A.inverted() @ Vector(d)
        hp.keyframe_insert("location", frame=f)
    hp.location = base[hp.name][0]
    esc.frame_set(1)
    # IK temporal: empties en los tobillos, polos delante de las rodillas
    temporales = []
    inv_arm = arm.matrix_world.inverted()
    for lado, mov in (("Left", pie_L), ("Right", pie_R)):
        up = arm.pose.bones[P + lado + "UpLeg"]
        leg = arm.pose.bones[P + lado + "Leg"]
        foot = arm.pose.bones[P + lado + "Foot"]
        cad_w, rod_w, tob_w = (arm.matrix_world @ up.head, arm.matrix_world @ leg.head,
                               arm.matrix_world @ leg.tail)
        flex = (rod_w - (cad_w + tob_w) / 2)
        flex = flex.normalized() if flex.length > 1e-4 else DELANTE
        obj = bpy.data.objects.new(f"ik_{lado}", None)
        esc.collection.objects.link(obj)
        rot_pie = (arm.matrix_world @ foot.matrix).to_quaternion()
        obj.matrix_world = Matrix.LocRotScale(tob_w, rot_pie, None)
        for f, d in mov.items():
            obj.location = tob_w + Vector(d)
            obj.keyframe_insert("location", frame=f)
        polo = bpy.data.objects.new(f"polo_{lado}", None)
        esc.collection.objects.link(polo)
        for f, d in mov.items():  # el polo acompaña al pie
            polo.location = rod_w + flex * 0.6 + Vector(d) * Vector((1, 1, 0))
            polo.keyframe_insert("location", frame=f)
        polo.location = rod_w + flex * 0.6
        temporales += [obj, polo]
        bpy.context.view_layer.update()
        c = leg.constraints.new("IK")
        c.target = obj
        c.pole_target = polo
        c.pole_angle = pole_angle(up, leg, inv_arm @ polo.location)
        c.chain_count = 2
        cr = foot.constraints.new("COPY_ROTATION")
        cr.target = obj
        cr.target_space = cr.owner_space = "WORLD"
    # comprobación antes de hornear: rodilla en fot. 1 igual que sin IK
    esc.frame_set(1)
    # hornear
    activar(arm)
    bpy.ops.object.mode_set(mode="POSE")
    for pb in arm.pose.bones:
        pb.bone.select = True
    bpy.ops.nla.bake(frame_start=1, frame_end=n_fot, step=1, only_selected=True, visual_keying=True,
                     clear_constraints=True, use_current_action=False, bake_types={"POSE"})
    bpy.ops.object.mode_set(mode="OBJECT")
    nueva = arm.animation_data.action
    nueva.name = nombre
    nueva.use_fake_user = True
    for fc in nueva.fcurves:
        for k in fc.keyframe_points:
            k.interpolation = "BEZIER"
            k.handle_left_type = k.handle_right_type = "AUTO_CLAMPED"
        fc.update()
    # comprobaciones con la acción horneada (sin IK)
    obj_L, obj_R = temporales[0], temporales[2]
    desliz, rod_max, z_min, z_f = 0.0, 0.0, 9.0, 1
    for f in range(1, n_fot + 1):
        esc.frame_set(f)
        for lado, ob in (("Left", obj_L), ("Right", obj_R)):
            leg = arm.pose.bones[P + lado + "Leg"]
            up = arm.pose.bones[P + lado + "UpLeg"]
            desliz = max(desliz, ((arm.matrix_world @ leg.tail) - ob.matrix_world.translation).length)
            ang = 180 - (up.tail - up.head).angle(leg.tail - leg.head) * 57.2958
            rod_max = max(rod_max, ang)
        z = (arm.matrix_world @ arm.pose.bones[P + "Hips"].head).z
        if z < z_min:
            z_min, z_f = z, f
    # inicio / fin frente a guardia fot. 1 (rodillas incluidas: el IK no debe girarlas)
    esc.frame_set(1)
    NOMBRES = ("Hips", "LeftHand", "RightHand", "LeftLeg", "RightLeg", "LeftToeBase", "RightToeBase")
    ini = {n: arm.matrix_world @ arm.pose.bones[P + n].head for n in NOMBRES}
    rodillas_f1 = max((ini[n] - ref_f1[n]).length for n in NOMBRES)
    esc.frame_set(n_fot)
    fin = {n: arm.matrix_world @ arm.pose.bones[P + n].head for n in NOMBRES}
    for ob in temporales:
        bpy.data.objects.remove(ob)
    bpy.data.actions.remove(tmp)
    desp = fin["Hips"] - ini["Hips"]
    final = max(((fin[n] - ini[n]) - desp).length for n in NOMBRES)
    r(f"  {nombre}: {n_fot} fot. ({(n_fot - 1) / 30:.2f} s), punto bajo fot. {z_f} (cadera {z_min:.3f} m)\n"
      f"     desplazamiento final {fmt(desp)} | fot. 1 vs guardia fot. 1: {rodillas_f1 * 1000:.1f} mm"
      f" | pose final vs inicial (quitando desplazamiento): {final * 1000:.1f} mm\n"
      f"     pies vs objetivo IK tras hornear: {desliz * 1000:.1f} mm máx."
      f" | rodilla más estirada: {rod_max:.0f}° (180° = recta)  -> REVISAR CON ENTRENADOR")
    return nueva, z_f


r("\n=== 5. ANIMACIONES NUEVAS (IK temporal en piernas, horneadas a Bezier) ===")
Z = Vector((0, 0, 1))
fijo = {1: (0, 0, 0)}
puntos_bajos = {}

# flexion ~1 s: baja recto, espalda recta, manos arriba
_, puntos_bajos["flexion"] = crear_animacion(
    "flexion", 31,
    cadera={1: (0, 0, 0), 16: tuple(Z * -0.18), 31: (0, 0, 0)},
    pie_L=fijo, pie_R=fijo)

# paso_atras ~0,8 s: primero el pie trasero (derecho), luego el delantero
D = 0.28
_, puntos_bajos["paso_atras"] = crear_animacion(
    "paso_atras", 25,
    cadera={1: (0, 0, 0), 11: tuple(ATRAS * 0.15 - Z * 0.03), 21: tuple(ATRAS * D), 25: tuple(ATRAS * D)},
    pie_R={1: (0, 0, 0), 6: tuple(ATRAS * D / 2 + Z * 0.04), 11: tuple(ATRAS * D), 25: tuple(ATRAS * D)},
    pie_L={1: (0, 0, 0), 11: (0, 0, 0), 16: tuple(ATRAS * D / 2 + Z * 0.03), 21: tuple(ATRAS * D),
           25: tuple(ATRAS * D)})

# rueda ~1,2 s: como flexion, pero la cadera dibuja una "U" de lado a lado
L = 0.15
_, puntos_bajos["rueda"] = crear_animacion(
    "rueda", 37,
    cadera={1: (0, 0, 0), 7: tuple(-SU_DERECHA * L - Z * 0.02), 19: tuple(Z * -0.20),
            31: tuple(SU_DERECHA * L - Z * 0.02), 37: (0, 0, 0)},
    pie_L=fijo, pie_R=fijo)

# ---------------------------------------------------------------- 8. guardar
asignar_accion(arm, bpy.data.actions["guardia"])
esc.frame_start, esc.frame_end = 1, 67
esc.frame_set(1)
bpy.data.orphans_purge(do_recursive=True)
r("\nAcciones finales:", sorted(a.name for a in bpy.data.actions))
r("Puntos bajos:", puntos_bajos)
r("Objetos finales:", sorted(f"{o.name}({o.type})" for o in bpy.data.objects))
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
r("GUARDADO", os.path.relpath(BLEND, C.RAIZ))
with open(os.path.join(C.TRABAJO, "fase2_resumen.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(resumen) + "\n")
