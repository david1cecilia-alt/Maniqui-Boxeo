"""Utilidades del modelo B (modelos/boxeador_b_rig.fbx): carga normalizada e islas.

- modelos/boxeador_b.fbx es la malla SIN rig (no sirve para animar).
- modelos/boxeador_b_rig.fbx es la misma malla rigeada en Mixamo (25 huesos, sin dedos).
- La textura se busca en modelos/Boxer_texture.png.
"""
import os

import bpy
import numpy as np
from mathutils import Matrix

import comun as C

FBX_RIG = os.path.join(C.RAIZ, "modelos", "boxeador_b_rig.fbx")
TEXTURA = os.path.join(C.RAIZ, "modelos", "Boxer_texture.png")


def cargar_b(nombre_arm="Boxeador_B", nombre_malla="Cuerpo_B"):
    """Importa B en la escena actual: metros, escala 1, de pie en z=0, mirando a -Y (como A),
    sin la animación Idle del FBX. Devuelve (armature, malla)."""
    antes = set(bpy.data.objects)
    acciones_antes = set(bpy.data.actions)
    bpy.ops.import_scene.fbx(filepath=FBX_RIG)
    nuevos = [o for o in bpy.data.objects if o not in antes]
    arm = next(o for o in nuevos if o.type == "ARMATURE")
    malla = next(o for o in nuevos if o.type == "MESH")
    for a in set(bpy.data.actions) - acciones_antes:
        bpy.data.actions.remove(a)
    if arm.animation_data:
        arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix()
    arm.name, arm.data.name = nombre_arm, nombre_arm
    malla.name, malla.data.name = nombre_malla, nombre_malla
    # aplicar transformaciones (escala 0.01 y rotación del FBX) a esqueleto y malla
    bpy.context.view_layer.update()
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in (arm, malla):
        o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # unidades: si mide más de 10 (cm), pasar a metros
    co = np.array([v.co[:] for v in malla.data.vertices])
    alto = co[:, 2].max() - co[:, 2].min()
    if alto > 10:
        arm.scale = (0.01, 0.01, 0.01)
        bpy.context.view_layer.update()
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # textura
    for m in malla.data.materials:
        if m and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE":
                    if os.path.exists(TEXTURA):
                        n.image = bpy.data.images.load(TEXTURA, check_existing=True)
                    if n.image:
                        n.image.pack()
            m.name = "Boxer_B"
    return arm, malla


def islas(me):
    """Índice de isla (pieza suelta) de cada vértice."""
    padre = np.arange(len(me.vertices))

    def raiz(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i
    for e in me.edges:
        a, b = raiz(e.vertices[0]), raiz(e.vertices[1])
        if a != b:
            padre[a] = b
    r = np.array([raiz(i) for i in range(len(me.vertices))])
    _, r = np.unique(r, return_inverse=True)
    return r


def dominante(ob):
    """Grupo de vértices (hueso, sin prefijo) con más peso en cada vértice."""
    nombre = {g.index: g.name.split(":")[-1] for g in ob.vertex_groups}
    res = []
    for v in ob.data.vertices:
        gs = [e for e in v.groups if e.group in nombre and not nombre[e.group].startswith(("ocultar", "engordar"))]
        res.append(nombre[max(gs, key=lambda e: e.weight).group] if gs else "")
    return np.array(res)


P = "mixamorig:"
CODIGOS = {"Cuerpo": 0, "Pantalon": 1, "Botas": 2, "Guante_Left": 3, "Guante_Right": 4}


def separar_piezas(arm, ob):
    """Separa la malla de B (transformaciones aplicadas) en Cuerpo, Pantalon, Botas,
    Guante_Left y Guante_Right. El pantalón y las zapatillas son islas sueltas; la manopla del
    guante va soldada al brazo y se corta a mitad del puño de velcro (que tapa el corte).
    Devuelve (objetos, info) con info = {'corte': {lado: (h0, d, t_inicio_puno, t_mitad)}, ...}."""
    from mathutils import Vector
    me = ob.data
    isl = islas(me)
    co = np.array([v.co[:] for v in me.vertices])
    dom = dominante(ob)
    datos = {}
    for i in range(isl.max() + 1):
        sel = isl == i
        g, c = np.unique(dom[sel], return_counts=True)
        datos[i] = (int(sel.sum()), g[c.argmax()], co[sel])
    pantalon = [i for i, (n, d, c) in datos.items() if d in ("Hips", "LeftUpLeg", "RightUpLeg")
                and c[:, 2].max() > 0.85 and c[:, 2].min() < 0.6 and n > 100]
    botas = [i for i, (n, d, c) in datos.items() if d.endswith(("Foot", "ToeBase"))]
    puno = {lado: [i for i, (n, d, c) in datos.items() if d in (lado + "ForeArm", lado + "Hand") and n < 2000]
            for lado in ("Left", "Right")}
    principal = max(datos, key=lambda i: datos[i][0])
    corte = {}
    for lado in ("Left", "Right"):
        b = arm.data.bones[P + lado + "ForeArm"]
        h0, h1 = Vector(b.head_local), Vector(b.tail_local)
        d = (h1 - h0).normalized()
        t = np.concatenate([(datos[i][2] - np.array(h0)) @ np.array(d) for i in puno[lado]])
        corte[lado] = (h0, d, float(t.min()), float((t.min() + t.max()) / 2))
    cod = np.zeros(len(me.polygons), dtype=int)
    for pl in me.polygons:
        i = isl[pl.vertices[0]]
        if i in pantalon:
            cod[pl.index] = CODIGOS["Pantalon"]
        elif i in botas:
            cod[pl.index] = CODIGOS["Botas"]
        else:
            for lado in ("Left", "Right"):
                h0, d, _, t_mitad = corte[lado]
                if i in puno[lado] or (i == principal and (Vector(pl.center) - h0).dot(d) > t_mitad
                                       and dom[pl.vertices[0]] in (lado + "ForeArm", lado + "Hand")):
                    cod[pl.index] = CODIGOS["Guante_" + lado]
    nombre_orig = ob.name
    objetos = {}
    for nombre, c in CODIGOS.items():
        if c == 0:
            continue
        for o in bpy.context.selected_objects:
            o.select_set(False)
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
        bpy.context.tool_settings.mesh_select_mode = (False, False, True)
        me.vertices.foreach_set("select", np.zeros(len(me.vertices), dtype=bool))
        me.edges.foreach_set("select", np.zeros(len(me.edges), dtype=bool))
        me.polygons.foreach_set("select", cod == c)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.separate(type="SELECTED")
        bpy.ops.object.mode_set(mode="OBJECT")
        nuevo = next(o for o in bpy.context.selected_objects if o != ob)
        nuevo.name = nuevo.data.name = nombre
        objetos[nombre] = nuevo
        cod = cod[cod != c]          # las caras separadas desaparecen de ob (se conserva el orden)
    objetos["Cuerpo"] = ob
    ob.name = ob.data.name = nombre_orig
    return objetos, {"corte": corte, "pantalon": pantalon, "botas": botas, "puno": puno, "principal": principal}


def color_textura(ob):
    """Color medio de la textura por vértice (muestreo en las UV)."""
    me = ob.data
    img = next((n.image for m in me.materials if m and m.use_nodes for n in m.node_tree.nodes
                if n.type == "TEX_IMAGE" and n.image and n.image.size[0] > 0), None)
    if img is None or not me.uv_layers:
        return None
    W, H = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)
    uv = np.zeros(len(me.loops) * 2)
    me.uv_layers.active.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    vi = np.zeros(len(me.loops), dtype=int)
    me.loops.foreach_get("vertex_index", vi)
    x = np.clip((uv[:, 0] % 1.0) * (W - 1), 0, W - 1).astype(int)
    y = np.clip((uv[:, 1] % 1.0) * (H - 1), 0, H - 1).astype(int)
    col = px[y, x, :3]
    suma = np.zeros((len(me.vertices), 3))
    np.add.at(suma, vi, col)
    cnt = np.bincount(vi, minlength=len(me.vertices))[:, None]
    return suma / np.maximum(cnt, 1)
