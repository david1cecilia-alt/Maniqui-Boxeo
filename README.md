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

## Pendiente

- **Guardia: REVISAR CON ENTRENADOR.** Las manos no llegan a la barbilla, la
  barbilla está poco recogida y la base es bastante cuadrada. Se corregirá más
  adelante, para todas las acciones a la vez.
- Esquivas, flexión, paso atrás y rueda: REVISAR CON ENTRENADOR.
