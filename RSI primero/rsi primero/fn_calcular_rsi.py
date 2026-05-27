# =============================================================================
#  fn_calcular_rsi.py
#  FUNCIÓN: calcular_rsi
# =============================================================================
#
#  QUÉ HACE:
#    Toma una serie de precios de cierre y calcula el RSI
#    usando el método original de J. Welles Wilder (1978).
#
#  QUÉ PUEDES MODIFICAR AQUÍ:
#    - El método de suavizado (ej. cambiar ewm por rolling para
#      un RSI "simple" en vez de RSI de Wilder)
#    - Agregar una segunda función para otro tipo de RSI (ej. RSI estocástico)
#
#  QUÉ NO DEBES MODIFICAR:
#    - El nombre de la función: calcular_rsi
#    - Los parámetros: (serie_precios, periodo)
#    - El rango de salida: siempre entre 0 y 100
#
# =============================================================================

import pandas as pd
import numpy as np


def calcular_rsi(serie_precios: pd.Series, periodo: int) -> pd.Series:
    """
    Calcula el RSI con suavizado de Wilder (método estándar).

    ¿Cómo funciona?
    ───────────────
    1. Calcula la variación diaria del precio (delta)
    2. Separa los días que subió (ganancias) de los que bajó (pérdidas)
    3. Calcula el promedio suavizado de ganancias y pérdidas
    4. Aplica la fórmula: RSI = 100 - 100 / (1 + RS)
       donde RS = promedio_ganancias / promedio_pérdidas

    El suavizado de Wilder usa ewm(com = periodo - 1):
      - Período 7  → com = 6   (más sensible, más señales)
      - Período 14 → com = 13  (estándar, balance)
      - Período 30 → com = 29  (más lento, menos señales)

    Parámetros
    ----------
    serie_precios : pd.Series  Precios de cierre diarios
    periodo       : int        Número de períodos del RSI

    Retorna
    -------
    pd.Series con valores entre 0 y 100.
    Los primeros `periodo` valores serán NaN (sin historia suficiente).
    """
    # Variación diaria: precio_hoy - precio_ayer
    delta = serie_precios.diff()

    # Días positivos (precio subió) → ganancias
    # Días negativos (precio bajó)  → pérdidas (convertidas a positivo)
    ganancias = delta.clip(lower=0)
    perdidas  = (-delta).clip(lower=0)

    # Promedio exponencial ponderado — suavizado de Wilder
    # min_periods=periodo → los primeros N valores quedan como NaN
    prom_gan = ganancias.ewm(com=periodo - 1, min_periods=periodo).mean()
    prom_per = perdidas.ewm(com=periodo - 1, min_periods=periodo).mean()

    # RS = Relative Strength (fuerza relativa)
    # replace(0, np.nan) evita división por cero cuando no hay pérdidas
    rs = prom_gan / prom_per.replace(0, np.nan)

    # Fórmula final del RSI
    rsi = 100 - (100 / (1 + rs))

    return rsi
