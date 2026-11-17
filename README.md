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
fbx/5_gancho_adelantado.fbx  fbx/6_gancho_trasero.fbx
fbx/10_crochet_cuerpo.fbx  fbx/bloqueo.fbx
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

Los scripts usan la API de acciones de Blender 4.5 (`action.fcurves`), que
Blender 5.x ya no tiene: hay que usar la 4.5.

## Fase 2: qué hay en `boxeador.blend`

- Un esqueleto (`Boxeador`), una malla de cuerpo (`Cuerpo`), `Eyes` y `Eyebrows`.
- 15 acciones con Fake User: guardia, guardia_alt, jab, recto,
  crochet_adelantado, crochet_trasero, gancho_adelantado, gancho_trasero,
  crochet_trasero_cuerpo, bloqueo, esquiva_avanzando, esquiva_retrocediendo,
  flexion, paso_atras y rueda.
- Esquivas en el sitio: sin desplazamiento horizontal de la cadera (se
  mantienen la bajada y los giros).
- Ropa: `Pantalon` (gris oscuro) y `Botas` (rojas), sacadas de la malla del
  cuerpo con Displace + Solidify, pesos copiados con Data Transfer y Armature.
- `Guante_Left` y `Guante_Right` (rojos): mallas emparentadas al hueso Hand,
  sin pesos; las manos del cuerpo se ocultan con un Mask.
- flexion, paso_atras y rueda: hechas con IK temporal en las piernas y
  horneadas a fotogramas Bezier; empiezan (y acaban) en el fotograma 1 de la
  guardia. paso_atras acaba 28 cm más atrás.

Resultados y comprobaciones: `trabajo/fase2_resumen.txt`.

## Pendiente

- **Guardia: REVISAR CON ENTRENADOR.** Las manos no llegan a la barbilla, la
  barbilla está poco recogida y la base es bastante cuadrada. Se corregirá más
  adelante, para todas las acciones a la vez.
- **Guantes cruzados en la guardia:** con la postura actual los guantes se
  meten uno dentro del otro en todos los fotogramas (hasta 7 cm); en
  guardia_alt, en 16 de 90 (hasta 2 cm). Se arreglará al corregir la guardia.
- Esquivas, flexión, paso atrás y rueda: REVISAR CON ENTRENADOR.
