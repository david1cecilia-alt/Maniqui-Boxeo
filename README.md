# Maniquí de boxeo 3D

Muñeco 3D de boxeo (Blender) para la app de boxeo: un esqueleto, una malla
de cuerpo y cada golpe/movimiento como una acción con nombre.

## Contenido

- `scripts/`: scripts de Blender en Python, que se pueden repetir.
- `trabajo/capturas/`: renders de comprobación (PNG).
- `trabajo/diagnostico_resumen.txt`: resultado del diagnóstico de la Fase 1.

## Créditos y licencias

- **Modelo:** "Superhero Male" de **Quaternius**, licencia **CC0**.
- **Animaciones y rig:** **Mixamo**, no incluidas (ver abajo).

## Animaciones (no incluidas)

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

## Cómo ejecutar los scripts

Con Blender 4.5, en modo background y desde la raíz del repo:

```
blender.exe --background --python scripts/fase1_extraer_datos.py
python scripts/fase1_analizar.py
blender.exe --background --python scripts/fase1_render.py
```

`fase1_analizar.py` es Python 3 normal. Sirve el `python.exe` que trae
Blender en `4.5/python/bin/`.

Fase 2 (monta `trabajo/boxeador.blend` y hace los renders):

```
blender.exe --background --python scripts/fase2_montar.py
blender.exe --background --python scripts/fase2_render.py
```

Ropa v2 (sustituye la ropa de la Fase 2 en `boxeador.blend`) y comparativas con
las referencias (carpeta `referencias/`, no incluida: renders de un modelo con
licencia CC BY de Meshy):

```
blender.exe --background --python scripts/ropa_v2.py
blender.exe --background --python scripts/ropa_v2_render.py
```

Fase 3 (comprobación; lee `boxeador.blend` sin guardarlo): resultados en
`trabajo/fase3_resumen.txt` y propuesta de la Fase 4 en `trabajo/fase4_propuesta.md`.
`comparar_choques.py` compara con los choques de la ropa v1.

```
blender.exe --background --python scripts/fase3_comprobar.py
python scripts/comparar_choques.py
```

Orden completo: fase2_montar → ropa_v2 → ropa_v2_render / fase3_comprobar.

Los scripts usan la API de acciones de Blender 4.5 (`action.fcurves`), que
Blender 5.x ya no tiene: hay que usar la 4.5.

## Fase 2: qué hay en `boxeador.blend`

- Un esqueleto (`Boxeador`), una malla de cuerpo (`Cuerpo`), `Eyes` y `Eyebrows`.
- 15 acciones con Fake User: guardia, guardia_alt, jab, recto,
  crochet_adelantado, crochet_trasero, gancho_adelantado_cuerpo (nº 11),
  gancho_trasero_cuerpo (nº 12), crochet_trasero_cuerpo, bloqueo,
  esquiva_avanzando, esquiva_retrocediendo, flexion, paso_atras y rueda.
  Los ganchos de Mixamo son ganchos AL CUERPO (golpean a la altura del abdomen).
- Esquivas en el sitio: sin desplazamiento horizontal de la cadera (se
  mantienen la bajada y los giros).
- Ropa v2 (`ropa_v2.py`, mallas nuevas, no caras del cuerpo):
  - `Pantalon`: corto de boxeo ancho hasta medio muslo, pliegues en la
    cintura, raja lateral y cinturilla gruesa. Pesos del cuerpo (Data
    Transfer) suavizados, Armature + Subdivision + Solidify.
  - `Botas`: caña hasta media pantorrilla, puntera lisa, suela fina, ribete y
    cordones. Pesos suavizados; el pie del cuerpo se oculta con el Mask.
  - `Guante_Left` / `Guante_Right`: ~15 cm de ancho, puño, pulgar, puño de la
    muñeca y tira de velcro; piezas convexas emparentadas al hueso Hand, sin
    pesos; las manos del cuerpo se ocultan con el Mask.
  - Copia de la versión anterior (ropa v1): `trabajo/boxeador_v1.blend`.
- flexion, paso_atras y rueda: hechas con IK temporal en las piernas y
  horneadas a fotogramas Bezier; empiezan (y acaban) en el fotograma 1 de la
  guardia. paso_atras acaba 28 cm más atrás.

Resultados y comprobaciones: `trabajo/fase2_resumen.txt`.

## Variantes B y C (modelo nuevo)

Modelo B: "Boxer" de **Creazilla** (licencia Creazilla Open-Source; al redistribuir hay que
citar a Creazilla.com), en `modelos/` (no se sube; licencia por confirmar):
`boxeador_b.fbx` (malla sin rig), `boxeador_b_rig.fbx` (la misma malla rigeada en Mixamo,
25 huesos sin dedos: el `Animations/Idle.fbx` de la descarga) y `Boxer_texture.png`.

```
blender.exe --background --python scripts/b_analizar.py     # trabajo/b_analisis.txt
blender.exe --background --python scripts/b_montar.py       # trabajo/boxeador_b.blend
blender.exe --background --python scripts/c_montar.py       # trabajo/boxeador_c.blend
blender.exe --background --python scripts/comparativa_render.py
blender.exe --background --python scripts/fase3_comprobar.py -- b --sin-renders
blender.exe --background --python scripts/fase3_comprobar.py -- c --sin-renders
python scripts/comparar_choques.py                          # trabajo/choques_v2_b_c.txt
```

- **B**: malla y esqueleto de B (mismos 25 huesos que la v2) con las 15 acciones copiadas
  (traslación escalada por la altura de la cadera). Separada en Cuerpo / Pantalon / Botas /
  Guante_* (el guante va soldado al brazo y se corta bajo el puño de velcro). Shape key
  `reforzado`: hombros, deltoides, brazo y antebrazo (escalado radial desde el eje del hueso).
- **C**: cuerpo y botas rojas de la v2 + pantalón y guantes de B. Guantes rígidos en el hueso
  Hand; pantalón ajustado con Shrinkwrap, pesos del cuerpo y la piel de debajo oculta con el Mask.
- Comparativas: `trabajo/capturas/comparativa_v2_b_c.png` y `comparativa_impacto_*_v2_b_c.png`.

## Pendiente

- **Guardia: REVISAR CON ENTRENADOR.** Las manos no llegan a la barbilla, la
  barbilla está poco recogida y la base es bastante cuadrada. Se corregirá más
  adelante, para todas las acciones a la vez.
- **Guantes cruzados en la guardia:** con la postura actual los guantes se
  meten uno dentro del otro en todos los fotogramas (hasta 7 cm); en
  guardia_alt, en 16 de 90 (hasta 2 cm). Se arreglará al corregir la guardia.
- Esquivas, flexión, paso atrás y rueda: REVISAR CON ENTRENADOR.
- **Ganchos a la cara (nº 5 y 6):** pendientes de buscar en Mixamo; los que hay
  son ganchos al cuerpo (11 y 12).
