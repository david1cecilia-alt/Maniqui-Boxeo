# Propuesta Fase 4 – corregir la guardia en todas las acciones

**Estado:** propuesta, NO aplicada. Datos de `trabajo/fase3_resumen.txt`.

## Objetivo (decidido con el entrenador)

- Guantes **separados, a los lados de la cara**, sin cruzarse ni tocarse.
- **Barbilla al pecho.**

## Punto de partida (guardia, fotograma 1)

Posición del centro de cada guante respecto al centro de la cabeza:

| guante | lateral | delante | altura |
|---|---|---|---|
| izquierdo (adelantado) | +12,3 cm | 34,3 cm | −7,5 cm |
| derecho (trasero) | +0,2 cm (en el centro de la cara) | 28,4 cm | −10,7 cm |

- Los guantes no están cruzados de lado a lado, pero el derecho queda delante de la boca y detrás del
  izquierdo: **se meten uno en el otro hasta 9 cm en los 67 fotogramas.**
- Los dos están demasiado lejos de la cara (28-34 cm por delante) y bajos.
- Objetivo orientativo: ±11 cm a cada lado, unos 15 cm por delante y a la altura de los pómulos
  (−3 cm). Hay que mover el **izquierdo unos 20 cm** (sobre todo hacia atrás) y el
  **derecho unos 19 cm** (11 cm hacia su lado, 13 cm hacia atrás y 8 cm hacia arriba).
- Barbilla al pecho: unos 15-20° más de flexión entre Neck y Head (el grado exacto lo fija el
  entrenador). La cabeza baja y avanza unos 3-5 cm.

## Cómo lo haría

Tres capas por encima de cada acción de Mixamo, sin tocar las acciones originales:

1. **Cuello y cabeza: capa aditiva NLA.**
   - Una acción `corr_cuello` con la rotación extra en Neck y Head, en una pista NLA en modo
     **Combine** (no Add: con cuaterniones, Add suma componentes y deforma la rotación).
   - Peso 1 en todos los fotogramas de todas las acciones: la barbilla va recogida también al golpear.
2. **Brazos: una capa por brazo** (`corr_brazo_L`, `corr_brazo_R`), sobre LeftShoulder,
   LeftArm, LeftForeArm y LeftHand, y lo mismo en el lado derecho. Son dos pistas porque la
   influencia de una pista NLA es una sola para todos sus huesos, y cada brazo necesita su propia
   curva.
   - **Brazo de guardia** (el que no golpea): peso 1 todo el tiempo.
   - **Brazo que golpea:** peso 1 en guardia, bajada suave a 0 entre el arranque y el
     impacto − 2 fotogramas, 0 en el impacto y vuelta a 1 cuando la mano regresa.
     Ventanas medidas:

     | golpe | brazo | arranque | impacto | vuelta |
     |---|---|---|---|---|
     | jab | izq. | 7 | 15 | 36 |
     | recto | der. | 14 | 21 | 42 |
     | crochet_adelantado | izq. | 9 | 16 | 37 |
     | crochet_trasero | der. | 3 | 11 | 28 |
     | gancho_adelantado | izq. | 12 | 20 | 54 |
     | gancho_trasero | der. | 12 | 19 | 44 |
     | crochet_trasero_cuerpo | der. | 13 | 25 | 44 |

3. **Cómo se calcula la corrección de los brazos.** Recomiendo **no** usar una rotación fija sacada
   de la guardia: las acciones no empiezan en la misma postura (el fotograma 1 se separa de la
   guardia entre 5 y 31 cm según la acción), y una rotación copiada dejaría los guantes en un sitio
   distinto en cada acción. Mejor:
   - Para cada acción, IK temporal en los brazos con objetivos **pegados a la cabeza** (los
     puntos ±11 cm de la tabla), con la misma curva de peso del punto 2.
   - Se hornea a una acción nueva (`jab_v2`, …), como se hizo con flexion y rueda. Los originales
     se quedan.
   - Así los guantes acaban siempre a los lados de la cara, aunque la cabeza se mueva o baje.

   Si se prefiere la capa aditiva pura en los brazos (más sencilla y editable en el NLA), se puede
   hacer igual, pero aceptando que la guardia quede algo distinta en cada acción.
4. **Comprobación:** volver a pasar `fase3_comprobar.py` sobre las acciones v2 y repetir los
   renders.

## Cuánto cambia el impacto

- **Mano que golpea, en el fotograma de impacto: 0 cm**, porque ahí su peso es 0. Además, la capa del
  cuello no mueve los brazos.
- **Antes del impacto:** la trayectoria de esa mano cambia de forma progresiva, hasta unos 20 cm al
  principio del arranque y nada 2 fotogramas antes del impacto.
- **La otra mano** queda en la guardia nueva durante el golpe y se mueve unos 19-20 cm respecto a
  como está ahora:

| golpe | impacto | mano que golpea | cambio en el impacto | la otra mano ahora se mueve (resp. cabeza) | la otra mano tras corregir |
|---|---|---|---|---|---|
| jab | fot. 15 | izq. | 0 cm | 14 cm | fija en guardia nueva |
| recto | fot. 21 | der. | 0 cm | 23 cm | fija en guardia nueva |
| crochet_adelantado | fot. 16 | izq. | 0 cm | 10 cm | fija en guardia nueva |
| crochet_trasero | fot. 11 | der. | 0 cm | 36 cm | fija en guardia nueva |
| gancho_adelantado | fot. 20 | izq. | 0 cm | 22 cm | fija en guardia nueva |
| gancho_trasero | fot. 19 | der. | 0 cm | 21 cm | fija en guardia nueva |
| crochet_trasero_cuerpo | fot. 25 | der. | 0 cm | 34 cm | fija en guardia nueva |

En crochet_trasero y crochet_trasero_cuerpo la mano de guardia se mueve mucho en el original
(34-36 cm). Fijarla puede quitarle naturalidad: lo tiene que ver el entrenador.

## Riesgos

1. **Choques nuevos.** Mover los guantes unos 20 cm cambia la posición de los codos. Hoy hay
   guante-pecho de 6-7 cm en jab y recto: puede mejorar o empeorar. Con la barbilla al pecho, la
   cabeza se acerca a los guantes: hay que volver a medir guante-cabeza.
2. **Tamaño de los guantes.** Miden unos 20 cm de ancho, más que un guante real (unos 15 cm). Con
   dos guantes a los lados de una cara de unos 15 cm de ancho cuesta que no se toquen. **Propuesta
   previa y barata:** reducirlos un 15-20 % y volver a medir. Reduce todos los choques de guantes.
3. **Rotación aditiva en posturas distintas:** ver el punto 3 de «Cómo lo haría». Por eso recomiendo
   IK con objetivos en la cabeza y horneado.
4. **Saltos en la transición** al subir o bajar la influencia, si la rampa es corta. Usar al menos
   4-6 fotogramas con curva suave.
5. **Inicio y final de las acciones.** No empiezan en la misma guardia (diferencias de 5 a 31 cm). La
   corrección las acerca a la guardia nueva, pero conviene igualar también el primer y el último
   fotograma, para que en la app se encadenen sin saltos.
6. **Exportación a la app:** las capas NLA hay que hornearlas antes de exportar. El plan ya genera
   acciones v2 horneadas.
7. **Ganchos:** los de Mixamo golpean a la altura del abdomen (−61 y −66 cm respecto a la cabeza).
   Si el entrenador quiere ganchos a la barbilla, hay que cambiar la animación, no solo la guardia.

## Otros arreglos que no son de la guardia (Fase 4 o posterior)

- **Botas:** 4 vértices de la suela tienen la normal invertida y el Displace los mete hacia dentro
  (0,8 cm, no se ve). Se arregla recalculando normales antes del Displace.
- **Pantalón:** el cuerpo asoma hasta 0,5 cm en muslos y rodillas cuando se doblan. Se arregla
  subiendo el Displace a unos 8 mm.
- **Guantes contra el cuerpo durante el movimiento** (esquivas, gancho_trasero contra el muslo,
  crochet_trasero_cuerpo): son de la animación de Mixamo, pensada para manos sin guantes.
