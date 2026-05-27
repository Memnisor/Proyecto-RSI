# =============================================================================
#  fn_senales.py
#  FUNCIÓN: detectar_senales
# =============================================================================
#
#  QUÉ HACE:
#    Recorre la serie del RSI y detecta los momentos exactos en que
#    el RSI CRUZA un umbral — eso es una señal de compra o venta.
#
#  QUÉ PUEDES MODIFICAR AQUÍ:
#    - La lógica de cruce (ej. exigir que el cruce sea fuerte,
#      que el RSI haya estado N días en la zona antes de cruzar)
#    - Agregar filtros adicionales (ej. solo BUY si precio > media móvil)
#    - Cambiar la codificación de salida (ej. usar "BUY"/"SELL" en vez de +1/-1)
#
#  QUÉ NO DEBES MODIFICAR:
#    - El nombre de la función: detectar_senales
#    - Los parámetros: (rsi, sobreventa, sobrecompra)
#    - La codificación de salida: +1 = BUY, -1 = SELL, 0 = nada
#
# =============================================================================

import pandas as pd


def detectar_senales(rsi: pd.Series,
                     sobreventa: float,
                     sobrecompra: float) -> pd.Series:
    """
    Detecta señales de compra/venta usando CRUCES del RSI.

    ¿Por qué cruces y no niveles?
    ─────────────────────────────
    Si detectamos señal cada vez que RSI < umbral (nivel), obtenemos
    muchas señales seguidas mientras el RSI permanece en la zona.
    Ejemplo: RSI baja a 25 y se queda ahí 5 días → 5 señales BUY
    seguidas, lo cual distorsiona el análisis estadístico.

    Con CRUCES solo se activa el día exacto en que el RSI SALE
    de la zona extrema → una sola señal limpia por episodio.

    Ejemplo banda 40/60:
      BUY  → ayer RSI estaba en 38 (≤40)  y hoy está en 42 (>40)
      SELL → ayer RSI estaba en 63 (≥60)  y hoy está en 57 (<60)

    ¿Cómo funciona .shift(1)?
    ─────────────────────────
    rsi.shift(1) desplaza la serie un día hacia adelante.
    Así en cada fila podemos comparar el valor de HOY con el de AYER
    sin necesidad de bucles.

    Parámetros
    ----------
    rsi         : pd.Series  Valores del RSI (salida de calcular_rsi)
    sobreventa  : float      Umbral inferior — ej. 30, 40
    sobrecompra : float      Umbral superior — ej. 60, 70

    Retorna
    -------
    pd.Series de enteros con el mismo índice que rsi:
        +1  → señal BUY  (RSI cruzó hacia arriba el umbral de sobreventa)
        -1  → señal SELL (RSI cruzó hacia abajo el umbral de sobrecompra)
         0  → sin señal
    """
    senales  = pd.Series(0, index=rsi.index, dtype=int)
    rsi_ayer = rsi.shift(1)   # valor del RSI el día anterior

    # BUY: RSI entra a zona de SOBREVENTA (precio cayó demasiado → comprar)
    mask_buy = (
        rsi_ayer.notna() &               # ayer el RSI tenía valor válido
        rsi.notna()      &               # hoy el RSI tiene valor válido
        (rsi_ayer >= sobreventa) &       # ayer: estaba FUERA de sobreventa (encima del umbral)
        (rsi <= sobreventa)              # hoy:  ENTRÓ a sobreventa → cruce hacia abajo ↓
    )

    # SELL: RSI entra a zona de SOBRECOMPRA (precio subió demasiado → vender)
    mask_sell = (
        rsi_ayer.notna() &               # ayer el RSI tenía valor válido
        rsi.notna()      &               # hoy el RSI tiene valor válido
        (rsi_ayer <= sobrecompra) &      # ayer: estaba FUERA de sobrecompra (debajo del umbral)
        (rsi >= sobrecompra)             # hoy:  ENTRÓ a sobrecompra → cruce hacia arriba ↑
    )
    
    senales[mask_buy]  =  1
    senales[mask_sell] = -1

    return senales
