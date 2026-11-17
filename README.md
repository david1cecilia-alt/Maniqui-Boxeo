# Maniquí de boxeo 3D

Muñeco 3D de boxeo (Blender) para la app de boxeo: un esqueleto, una malla
de cuerpo y cada golpe/movimiento como una acción con nombre.

## Contenido

- `scripts/`: scripts de Blender en Python, que se pueden repetir.
- `trabajo/capturas/`: renders de comprobación (PNG).
- `trabajo/*.txt`: resúmenes y comprobaciones de cada fase.

## Créditos y licencias

- **Modelo:** Creazilla.com (Creazilla Open-Source License). Modelo principal ("Boxer",
  <https://creazilla.com>); los renders de este modelo están en `trabajo/capturas/`.
- **Modelo anterior (v2):** "Superhero Male" de **Quaternius**, licencia **CC0**.
- **Animaciones y rig:** **Mixamo**, no incluidas (ver abajo).

## Animaciones y modelos (no incluidos)

Las animaciones y el rig son de **Mixamo** y **no se incluyen en este
repositorio** (ni los `.fbx` ni los `.blend`, que las llevan dentro).
Para ejecutar los scripts, descarga los FBX desde Mixamo y colócalos en `fbx/`:

```
fbx/guardia.fbx  fbx/guardia_alt.fbx  fbx/1_jab.fbx  fbx/2_recto.fbx
fbx/3_crochet_adelantado.fbx  fbx/4_crochet_trasero.fbx
fbx/10_crochet_cuerpo.fbx
fbx/11_gancho_adelantado_cuerpo.fbx  fbx/12_gancho_trasero_cuerpo.fbx
fbx/bloqueo.fbx
fbx/esquiva_avanzando_REVISAR.fbx  fbx/esquiva_retrocediendo_REVISAR.fbx
fbx/extra/BoxeoFigura.fbx
```

El modelo de Creazilla va en `modelos/` (tampoco se sube): `boxeador_b.fbx` (malla sin
rig), `boxeador_b_rig.fbx` (la misma malla rigeada en Mixamo, 25 huesos sin dedos: el
`Animations/Idle.fbx` de la descarga) y `Boxer_texture.png`. `b_montar.py` crea
`modelos/Boxer_texture_sin_logo.png` (copia de la textura sin el logo de la marca de los guantes).

## Cómo ejecutar los scripts

Con **Blender 4.5**, en modo background y desde la raíz del repo (los scripts usan la API
de acciones de Blender 4.5, `action.fcurves`, que Blender 5.x ya no tiene). Los scripts de
Python normal (`fase1_analizar.py`, `comparar_choques.py`) sirven con el `python.exe` que
trae Blender en `4.5/python/bin/`.

### Flujo por defecto: modelo principal (B) → `trabajo/boxeador.blend`

Necesita `trabajo/boxeador_v2.blend` (de donde salen las 15 acciones; ver más abajo).

```
blender.exe --background --python scripts/b_montar.py            # monta trabajo/boxeador.blend
blender.exe --background --python scripts/fase4_b.py             # guardia corregida: acciones _v2
blender.exe --background --python scripts/fase3_comprobar.py -- --sin-renders   # choques -> fase3_resumen.txt
blender.exe --background --python scripts/b_codo_diag.py         # codo -> b_codo_diag.txt
blender.exe --background --python scripts/fase4_render.py        # renders de la Fase 4
python scripts/comparar_choques.py                               # tablas de choques
```

### Modelo v2 (anterior) → `trabajo/boxeador_v2.blend`

```
blender.exe --background --python scripts/fase1_extraer_datos.py
python scripts/fase1_analizar.py
blender.exe --background --python scripts/fase1_render.py
blender.exe --background --python scripts/fase2_montar.py        # monta boxeador_v2.blend
blender.exe --background --python scripts/fase2_render.py
blender.exe --background --python scripts/ropa_v2.py             # ropa v2
blender.exe --background --python scripts/ropa_v2_render.py      # comparativas con referencias/ (no incluida)
blender.exe --background --python scripts/fase3_comprobar.py -- v2   # -> fase3_resumen_v2.txt
```

### Variante C y comparativa de modelos

```
blender.exe --background --python scripts/b_analizar.py          # análisis del modelo de Creazilla
blender.exe --background --python scripts/c_montar.py            # trabajo/boxeador_c.blend
blender.exe --background --python scripts/fase3_comprobar.py -- c --sin-renders
blender.exe --background --python scripts/comparativa_render.py  # comparativa_v2_b_c.png e impactos
```

## Modelo principal (B): qué hay en `trabajo/boxeador.blend`

- Esqueleto `Boxeador` (25 huesos de Mixamo, los mismos que la v2) y la malla del modelo
  de Creazilla separada en `Cuerpo`, `Pantalon`, `Botas` (zapatillas) y `Guante_Left` /
  `Guante_Right` (el guante va soldado al brazo: se corta bajo el puño de velcro, que tapa el
  corte). Un solo material con textura (sin el logo de la marca).
- 15 acciones originales (copiadas de la v2, traslación escalada por la altura de la cadera)
  y sus 15 versiones `_v2` de la Fase 4. Todas con Fake User.
- Pies: rotación rehecha para que giren respecto a su reposo igual que en la v2 (la copia
  directa los dejaba hasta 15° girados) y cadera corregida en cada fotograma para que la
  suela apoye en Z=0 (antes se hundían hasta 9 cm).
- Shape key `reforzado`: hombros, deltoides, brazo y antebrazo (escalado radial desde el
  eje del hueso); casi 0 en el codo. Pesos Arm/ForeArm suavizados alrededor del codo.
- Guantes un 12 % más cortos (la manopla; el puño de velcro no se toca).

### Fase 4 (acciones `_v2`), ver `trabajo/fase4_propuesta.md` y `trabajo/fase4_resumen.txt`

- Barbilla al pecho (Neck +6°, Head +10°) en todos los fotogramas.
- Guardia: un guante a cada lado de la cara, 13 cm por delante, con ~2,5 cm de aire,
  objetivos pegados a la cabeza; codos cerrados (polo del IK abajo y delante del pecho);
  flexión del codo limitada a 140°.
- Golpes: solo el brazo que golpea se suelta hacia la animación original (rampa de 5
  fotogramas); en el impacto el brazo es el de Mixamo. Bloqueo: se sueltan los dos brazos.
  Esquivas, flexion, paso_atras, rueda y guardias: guardia todo el tiempo.
- Si un guante se acerca a la cabeza, se aparta y se recalcula. Primer y último fotograma iguales.
- Resultado (`trabajo/fase4_choques_antes_despues.txt`): guante-cabeza 0 cm en todas las `_v2`
  (antes hasta 4,3 cm), guante-guante hasta 1,5 cm (antes 3,5).
- Renders: `trabajo/capturas/fase4_guardia_v2.png`, `fase4_impacto_<golpe>.png`, `fase4_codo_cerca.png`.

## Modelo v2 (anterior): `trabajo/boxeador_v2.blend`

- Esqueleto `Boxeador`, `Cuerpo`, `Eyes`, `Eyebrows` y la ropa v2 (`ropa_v2.py`): `Pantalon`,
  `Botas` y `Guante_*` (piezas convexas en el hueso Hand; manos y pies ocultos con el Mask).
- 15 acciones con Fake User: guardia, guardia_alt, jab, recto, crochet_adelantado,
  crochet_trasero, gancho_adelantado_cuerpo (nº 11), gancho_trasero_cuerpo (nº 12),
  crochet_trasero_cuerpo, bloqueo, esquiva_avanzando, esquiva_retrocediendo, flexion,
  paso_atras y rueda. Los ganchos de Mixamo son ganchos AL CUERPO.
- Copia de la ropa v1: `trabajo/boxeador_v1.blend`. Resultados en `trabajo/fase2_resumen.txt`.

## Variante C: `trabajo/boxeador_c.blend`

Cuerpo y botas rojas de la v2 + pantalón y guantes del modelo de Creazilla (guantes rígidos en
el hueso Hand; pantalón con Shrinkwrap, pesos del cuerpo y la piel de debajo oculta con el Mask).

## Pendientes y defectos conocidos

- **Codo (B):** el pico del pliegue venía sobre todo de la shape key `reforzado` (empujaba la
  piel del pliegue hacia fuera) y de un salto brusco de pesos Arm/ForeArm. Arreglado en las
  acciones originales (estiramiento máx. de las aristas 1,44-1,65, casi igual que sin la shape
  key). **Queda:** en las `_v2` la guardia cerrada dobla el codo hasta 140° y la malla del pliegue
  se sigue estirando (x1,7 en guardia_v2, x1,95 en jab_v2): es la malla de poca resolución del
  modelo con sus pesos de Mixamo. Ver `trabajo/b_codo_diag.txt` y `fase4_codo_cerca.png`.
- **Guantes (B):** son los del modelo y siguen siendo grandes. En las acciones originales aún se
  meten en la cara (hasta 4,3 cm) y uno en otro (3,5 cm): por eso hay que usar las `_v2`. En las
  `_v2` el puño del guante roza el pecho/hombro (Spine2) hasta 1,5 cm en la guardia (codos
  cerrados) y guante-guante llega a 1,5 cm en el bloqueo. Guante-cuerpo en jab y recto (2-2,4 cm)
  es de la animación.
- **Logo de los guantes:** tapado con una etiqueta gris lisa (`b_textura_logo.py` lo rehace en los
  `.blend` sin volver a montarlos). Quedan unos píxeles amarillos en el margen de la textura, fuera
  de las UV (no se ven en el modelo). Los renders de `trabajo/capturas/` se hicieron con una
  primera versión que dejaba un trazo amarillo pequeño en el puño.
- **Guardia, esquivas, flexión, paso atrás y rueda: REVISAR CON ENTRENADOR** (ahora sobre las `_v2`).
- **Ganchos a la cara (nº 5 y 6):** pendientes de buscar en Mixamo; los que hay son al cuerpo.
- **C:** el pantalón hace un pico en el bajo trasero en el jab; la medida del pantalón de C da un
  falso positivo fijo (4,3 cm) en la franja visible sobre el bajo.
