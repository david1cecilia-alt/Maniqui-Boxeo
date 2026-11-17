# Maniquí de boxeo 3D

Muñeco 3D de boxeo (Blender) para la app de boxeo: un esqueleto, una malla
de cuerpo y cada golpe/movimiento como una acción con nombre.

## Cuál es el bueno

| Qué | Dónde |
|---|---|
| **Muñeco con las acciones de la app** (solo las buenas, nombres limpios: `jab`, `recto`…) | `trabajo/boxeador_final.blend` |
| **Una lámina por acción** (numerada como en la app) | `trabajo/capturas/app/NN_<acción>.png` |
| Lista de acciones con su fotograma clave | `trabajo/final_resumen.txt` |
| Taller (originales de Mixamo, `_v2` e intermedias; los scripts trabajan aquí, no usar en la app) | `trabajo/boxeador.blend` |
| Modelo anterior, del que sale el taller (no tocar) | `trabajo/boxeador_v2.blend` |
| Todo lo antiguo (versiones viejas, variante C, renders y resúmenes de fases anteriores) | `archivo/` |

## Contenido

- `scripts/`: scripts de Blender en Python, que se pueden repetir.
- `trabajo/capturas/app/`: láminas de las acciones de la app (PNG).
- `trabajo/*.txt`: resúmenes y comprobaciones de las fases actuales.
- `archivo/`: lo antiguo (ver `archivo/LEEME.md`).

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
fbx/bloqueo.fbx   (es una reacción a un golpe: en el .blend se llama reaccion_golpe)
fbx/pivote.fbx (pivote de ida y vuelta)  fbx/pivote_der.fbx  fbx/pivote_izq.fbx  fbx/paso_atras.fbx
fbx/extra/futuros/esquiva_avanzando_REVISAR.fbx  fbx/extra/futuros/esquiva_retrocediendo_REVISAR.fbx
fbx/extra/BoxeoFigura.fbx  fbx/extra/guardias_saltando.fbx (sin usar)
```

El modelo de Creazilla va en `modelos/` (tampoco se sube): `boxeador_b.fbx` (malla sin
rig), `boxeador_b_rig.fbx` (la misma malla rigeada en Mixamo, 25 huesos sin dedos: el
`Animations/Idle.fbx` de la descarga) y `Boxer_texture.png`. `b_montar.py` crea
`modelos/Boxer_texture_sin_logo.png` (copia de la textura sin el logo de la marca de los guantes).

## Cómo ejecutar los scripts

Con **Blender 4.5**, en modo background y desde la raíz del repo (los scripts usan la API
de acciones de Blender 4.5, `action.fcurves`, que Blender 5.x ya no tiene). Los scripts de
Python normal (en `archivo/scripts/`) sirven con el `python.exe` que trae Blender en `4.5/python/bin/`.

### Flujo por defecto: modelo principal (B) → `trabajo/boxeador.blend`

Necesita `trabajo/boxeador_v2.blend` (de donde salen las 15 acciones; ver más abajo).

```
blender.exe --background --python scripts/b_montar.py            # monta trabajo/boxeador.blend
blender.exe --background --python scripts/b_brazo.py             # brazo (hombro-codo) un 30 % más largo
blender.exe --background --python scripts/b_mixamo_nuevas.py     # pivotes y paso atrás de Mixamo, renombres
blender.exe --background --python scripts/fase4_b.py             # guardia corregida: acciones _v2
blender.exe --background --python scripts/fase5_b.py             # acciones a mano y correcciones (después de fase4)
blender.exe --background --python scripts/final_b.py            # -> trabajo/boxeador_final.blend (lo bueno)
blender.exe --background --python scripts/final_render.py        # láminas -> trabajo/capturas/app/
blender.exe --background --python scripts/final_render.py -- jab rueda_der   # solo esas
blender.exe --background --python scripts/fase3_comprobar.py -- --sin-renders   # choques -> fase3_resumen.txt
```

Cada vez que cambia una acción: el script que la hace (`fase5_b.py`…), `final_b.py` y `final_render.py`.

## Modelo v2 (anterior) → `trabajo/boxeador_v2.blend`

```
blender.exe --background --python scripts/fase2_montar.py        # monta boxeador_v2.blend
blender.exe --background --python scripts/ropa_v2.py             # ropa v2
```

(La Fase 1, la variante C y las comparativas están en `archivo/scripts/`.)

## Modelo principal (B): qué hay en `trabajo/boxeador.blend`

- Esqueleto `Boxeador` (25 huesos de Mixamo, los mismos que la v2) y la malla del modelo
  de Creazilla separada en `Cuerpo`, `Pantalon`, `Botas` (zapatillas) y `Guante_Left` /
  `Guante_Right` (el guante va soldado al brazo: se corta bajo el puño de velcro, que tapa el
  corte). Un solo material con textura (sin el logo de la marca).
- Acciones originales (copiadas de la v2, traslación escalada por la altura de la cadera; `bloqueo` pasa a
  llamarse `reaccion_golpe`, `rueda` se sustituye, `paso_atras` -> `paso_atras_mano`, `gancho_adelantado_cuerpo`
  -> `gancho_adelantado_mixamo` y las esquivas de Mixamo -> `futuro_*`), 4 de Mixamo añadidas directamente a B
  (`b_mixamo_nuevas.py`: `pivote`, `pivote_der`, `pivote_izq`, `paso_atras`), sus `_v2` (Fase 4; sin
  `flexion_v2`) y las hechas a mano en la Fase 5. Todas con Fake User. Ver la tabla de acciones para la app.
- Pies: rotación rehecha para que giren respecto a su reposo igual que en la v2 (la copia
  directa los dejaba hasta 15° girados) y cadera corregida en cada fotograma para que la
  suela apoye en Z=0 (antes se hundían hasta 9 cm).
- Shape key `reforzado`: hombros, deltoides, brazo y antebrazo (escalado radial desde el
  eje del hueso); casi 0 en el codo. Pesos Arm/ForeArm suavizados alrededor del codo.
- Guantes un 12 % más cortos (la manopla; el puño de velcro no se toca).
- Brazo (hombro -> codo) un 30 % más largo (`b_brazo.py`): era 0,85 veces el antebrazo y ahora 1,10
  (0,205 -> 0,266 m). Se estira la malla del brazo y el antebrazo, la mano y el guante se desplazan.
  Con el brazo nuevo casi desaparecen los roces guante-cuerpo de las `_v2` (guardia 1,5 -> 0,6 cm).

### Fase 4 (acciones `_v2`), ver `trabajo/fase4_resumen.txt` (y `archivo/trabajo/fase4_propuesta.md`)

- Barbilla al pecho (Neck +6°, Head +10°) en todos los fotogramas.
- Guardia: un guante a cada lado de la cara, 13 cm por delante, con ~2,5 cm de aire,
  objetivos pegados a la cabeza; codos cerrados (polo del IK abajo y delante del pecho);
  flexión del codo limitada a 140°.
- Golpes: solo el brazo que golpea se suelta hacia la animación original (rampa de 5
  fotogramas); en el impacto el brazo es el de Mixamo. Bloqueo: se sueltan los dos brazos.
  Esquivas, flexion, paso_atras, rueda y guardias: guardia todo el tiempo.
- Si un guante se acerca a la cabeza, se aparta y se recalcula. Primer y último fotograma iguales.
- Resultado (`archivo/trabajo/fase4_choques_antes_despues.txt`): guante-cabeza 0 cm en todas las `_v2`
  (antes hasta 4,3 cm), guante-guante hasta 1,5 cm (antes 3,5).

### Acciones para la app (todas: REVISAR CON ENTRENADOR)

En `trabajo/boxeador_final.blend` (sale de `final_b.py`); lámina de cada una en
`trabajo/capturas/app/NN_<acción>.png`. "Mixamo" = animación de Mixamo con la guardia corregida
(`_v2`, Fase 4); "a mano" = creada en `fase5_b.py`. Cada acción lleva las propiedades `app`,
`origen` y `clave` (fotograma de impacto / punto máximo). 30 fot./s.

| Nº | Acción de la app | Acción final | Sale de (taller) | Fot. | Clave | Origen |
|---|---|---|---|---|---|---|
| 1 | Jab | `jab` | `jab_v2` | 53 | 16 | Mixamo |
| 2 | Recto | `recto` | `recto_v2` | 65 | 21 | Mixamo |
| 3 | Crochet adelantado | `crochet_adelantado` | `crochet_adelantado_v2` | 61 | 16 | Mixamo |
| 4 | Crochet trasero | `crochet_trasero` | `crochet_trasero_v2` | 47 | 19 | Mixamo + transición desde/hacia la guardia |
| 5 | Gancho adelantado | `gancho_adelantado` | `gancho_adelantado` | 67 | 20 | Mixamo (gancho_adelantado_mixamo_v2 tal cual) |
| 6 | Gancho trasero | `gancho_trasero` | `gancho_trasero` | 30 | 13 | a mano (de cero) |
| 7 | Jab al cuerpo | `jab_cuerpo` | `jab_cuerpo` | 53 | 16 | jab_v2 + bajada con las piernas |
| 8 | Recto al cuerpo | `recto_cuerpo` | `recto_cuerpo` | 65 | 21 | recto_v2 + bajada con las piernas |
| 9 | Crochet adelantado al cuerpo | `crochet_adelantado_cuerpo` | `crochet_adelantado_cuerpo` | 61 | 16 | crochet_adelantado_v2 + bajada |
| 10 | Crochet trasero al cuerpo | `crochet_trasero_cuerpo` | `crochet_trasero_cuerpo_v2` | 66 | 24 | Mixamo |
| 11 | Gancho adelantado al cuerpo | `gancho_adelantado_cuerpo` | `gancho_adelantado_cuerpo` | 67 | 20 | gancho_adelantado_mixamo_v2 + agachado, de abajo arriba |
| 12 | Gancho trasero al cuerpo | `gancho_trasero_cuerpo` | `gancho_trasero_cuerpo_v2` | 67 | 19 | Mixamo |
| 13 | Guardia | `guardia` | `guardia_v2` | 67 | 34 | Mixamo |
| 13 | Guardia (alternativa) | `guardia_alt` | `guardia_alt_v2` | 90 | 45 | Mixamo |
| 14 | Bloqueo cerrado | `bloqueo_cerrado` | `bloqueo_cerrado` | 28 | 14 | a mano |
| 15 | Bloqueo alto izquierdo | `bloqueo_alto_izq` | `bloqueo_alto_izq` | 28 | 14 | a mano |
| 15 | Bloqueo alto derecho | `bloqueo_alto_der` | `bloqueo_alto_der` | 28 | 14 | a mano |
| 16 | Bloqueo bajo izquierdo | `bloqueo_bajo_izq` | `bloqueo_bajo_izq` | 28 | 14 | a mano |
| 16 | Bloqueo bajo derecho | `bloqueo_bajo_der` | `bloqueo_bajo_der` | 28 | 14 | a mano |
| 17 | Parada | `parada` | `parada` | 18 | 7 | a mano |
| 18 | Esquiva lateral derecha | `esquiva_der` | `esquiva_der` | 25 | 12 | a mano |
| 18 | Esquiva lateral izquierda | `esquiva_izq` | `esquiva_izq` | 25 | 12 | a mano |
| 19 | Flexión | `flexion` | `flexion` | 31 | 16 | a mano (Fase 2, la original) |
| 20 | Rueda derecha | `rueda_der` | `rueda_der` | 37 | 19 | a mano |
| 20 | Rueda izquierda | `rueda_izq` | `rueda_izq` | 37 | 19 | a mano |
| 21 | Ballesteo | `ballesteo` | `ballesteo` | 28 | 14 | a mano |
| 22 | Paso adelante | `paso_adelante` | `paso_adelante` | 25 | 13 | a mano |
| 23 | Paso atrás | `paso_atras` | `paso_atras_v2` | 27 | 14 | Mixamo |
| 24 | Paso lateral izquierdo | `paso_lateral_izq` | `paso_lateral_izq` | 25 | 13 | a mano |
| 24 | Paso lateral derecho | `paso_lateral_der` | `paso_lateral_der` | 25 | 13 | a mano |
| 25 | Pivote (ida y vuelta) | `pivote` | `pivote_v2` | 136 | 68 | Mixamo |
| 25 | Pivote derecha | `pivote_der` | `pivote_der_v2` | 38 | 19 | Mixamo (para Aprende) |
| 25 | Pivote izquierda | `pivote_izq` | `pivote_izq_v2` | 39 | 20 | Mixamo (para Aprende) |

Solo en el taller (no van a la app): las originales de Mixamo sin corregir, `reaccion_golpe` (el antiguo
"bloqueo" de Mixamo), `paso_atras_mano_v2` y `pivote_mano` (los hechos a mano, sustituidos por los de
Mixamo) y, para más adelante, `futuro_esquiva_avanzando(_v2)` / `futuro_esquiva_retrocediendo(_v2)` (la
cadera se rompe con el pantalón; sus FBX están en `fbx/extra/futuros/`).

### Fase 5 (acciones a mano y correcciones), ver `trabajo/fase5_resumen.txt`

- **Técnica común:** desde `guardia_v2` y volviendo a ella; pies con IK fijos en el suelo (suela en
  Z=0; el pie que pivota gira sobre la punta con el talón arriba); brazos con IK analítico y
  seguridad guante-cabeza; transiciones suaves.
- **Bloqueos** (28 fot., 0,9 s), "codo primero": el codo donde tiene que tapar y el antebrazo sale de él.
  Altos: el codo sube rotando el hombro y el guante queda pegado a la sien (tapan el lateral de la
  cabeza). Bajos: codo pegado al cuerpo pero adelantado, por delante de costillas e hígado, hombro
  adelantado y abdomen contraído. Cerrado: los dos codos juntos delante de las costillas.
- **Ruedas** (37 fot.): la cabeza dibuja una U y sube en el lado del nombre; cadera y tronco giran, la
  pierna de delante se adelanta 12 cm, rodillas flexionadas (la cadera baja hasta 15 cm), abdomen
  contraído y guantes 3,5 cm más arriba.
- **Pasos** (25 fot.): sale primero el pie del lado hacia el que se va; acaban desplazados 25 cm y en
  guardia (solo la pose coincide con el primer fotograma). `paso_atras_v2` (Mixamo) acaba 48 cm atrás.
- **Golpes 7, 8, 9:** las piernas siguen los pies de la animación; la pierna de delante avanza 10 cm y la
  cadera baja hasta que el hombro queda a la altura del objetivo (mínimo 8 cm); la otra mano en la cara.
  El jab y el recto de Mixamo ya se inclinan y golpean bajo (puño a 0,92 / 1,01 m en el impacto).
- **Gancho adelantado (5):** el de Mixamo tal cual. **Al cuerpo (11):** a partir de él, 12 cm más
  agachado y el puño sube de abajo arriba hasta las costillas de un rival de su altura (1,10 m), codo a
  90° y hacia su lado (no cruza).
- **Gancho trasero (6), de cero:** carga (la mano baja junto a la barbilla, rodillas), la cadera y el
  hombro derechos giran hacia delante con el talón derecho arriba, y el puño sube casi vertical con la
  palma hacia sí, codo a 85° y 23 cm por debajo del puño. Acaba a la altura de su barbilla (la del
  rival, con la cara a su misma altura: 1,34 m; nunca por encima de su cabeza), sin cruzar el eje (puño
  +2 cm, codo +12 cm hacia su lado). Queda solo ~7 cm por delante de la cara (no 30-40): con este
  muñeco la cabeza en guardia va muy por delante de los hombros y más lejos el brazo iría estirado.
- **Esquivas laterales** (25 fot.): el tronco gira y se inclina, el hombro contrario se mete hacia delante
  y abajo, rodillas y tronco flexionados (la cabeza baja 16 cm) y la cabeza acaba sobre la rodilla de ese
  lado (se aparta 22 cm a la derecha y 15 cm a la izquierda); el pie contrario pivota sin moverse.
- **Ballesteo:** tronco bien atrás (la cabeza retrocede 35 cm) sin paso; solo el pie de atrás retrocede.
- **Parada:** la mano derecha da un toque de 16 cm hacia dentro y abajo y desvía con la PALMA del guante;
  la cabeza se aparta un poco.
- **crochet_trasero_v2:** la de Mixamo empezaba a mitad del golpe; ahora tiene 8 fotogramas de
  transición desde la guardia y de vuelta a ella.
- **Esquivas de Mixamo** (`futuro_`): pies fijos en el suelo con IK y paso real; quedan para más adelante.

## Modelo v2 (anterior): `trabajo/boxeador_v2.blend`

- Esqueleto `Boxeador`, `Cuerpo`, `Eyes`, `Eyebrows` y la ropa v2 (`ropa_v2.py`). 15 acciones de Mixamo con
  Fake User, de donde `b_montar.py` copia las del taller. La ropa v1 y la variante C están en `archivo/blend/`.

## Pendientes y defectos conocidos

- **Codo (B):** el pico del pliegue venía sobre todo de la shape key `reforzado` (empujaba la
  piel del pliegue hacia fuera) y de un salto brusco de pesos Arm/ForeArm. Arreglado en las
  acciones originales (estiramiento máx. de las aristas 1,44-1,65, casi igual que sin la shape
  key). **Queda:** en las `_v2` la guardia cerrada dobla el codo hasta 140° y la malla del pliegue
  se sigue estirando (x1,7 en guardia_v2, x1,95 en jab_v2): es la malla de poca resolución del
  modelo con sus pesos de Mixamo. Ver `archivo/trabajo/b_codo_diag.txt` y `archivo/capturas/fase4_codo_cerca.png`.
- **Guantes (B):** son los del modelo y siguen siendo grandes. En las acciones originales aún se
  meten en la cara (hasta 4,3 cm) y uno en otro (3,5 cm): por eso hay que usar las `_v2`. En las
  `_v2` el puño del guante roza el pecho/hombro (Spine2) hasta 1,5 cm en la guardia (codos
  cerrados) y guante-guante llega a 1,5 cm en el bloqueo. Guante-cuerpo en jab y recto (2-2,4 cm)
  es de la animación.
- **Logo de los guantes:** tapado con una etiqueta gris lisa. Quedan unos píxeles amarillos en el margen
  de la textura, fuera de las UV (no se ven en el modelo).
- **Todas las acciones de la app: REVISAR CON ENTRENADOR**.
- **Pivotes de Mixamo:** al girar, la pierna se deforma un poco (pesos de Mixamo de la rodilla con la malla
  de poca resolución). No se han tocado los pesos de la rodilla para no romper el resto de acciones.
- **Gancho trasero (6):** con el codo a ~90° el puño solo queda ~7 cm por delante de la cara (se pedían
  30-40 cm); los ganchos de Mixamo (5 y al cuerpo) llevan el tronco muy inclinado.
- **Esquivas de Mixamo:** la cadera se rompe con el pantalón (`futuro_*`, fuera de la app).
