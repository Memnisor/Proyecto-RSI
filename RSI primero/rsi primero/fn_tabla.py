# =============================================================================
#  fn_tabla.py
#  FUNCIÓN: tabla_estadisticas
# =============================================================================
#
#  QUÉ HACE:
#    Toma la tabla de rendimientos futuros y calcula dos métricas
#    clave para evaluar si una estrategia funciona:
#      • Retorno promedio (Media%)
#      • Tasa de acierto   (Win Rate%)
#
#  QUÉ PUEDES MODIFICAR AQUÍ:
#    - Agregar más métricas: mediana, desviación estándar,
#      Sharpe ratio, peor pérdida, mejor ganancia
#    - Cambiar el formato de la tabla (decimales, nombres de columnas)
#    - Agregar colores con la librería "rich" o "tabulate"
#
#  QUÉ NO DEBES MODIFICAR:
#    - El nombre de la función: tabla_estadisticas
#    - Los parámetros: (df_rend, dias_futuro)
#    - La estructura de salida: DataFrame con índice BUY/SELL
#
# =============================================================================

import pandas as pd
import numpy as np


def tabla_estadisticas(df_rend: pd.DataFrame,
                        dias_futuro: list) -> pd.DataFrame:
    """
    Calcula retorno promedio y Win Rate para señales BUY y SELL.

    ¿Qué es el Win Rate?
    ─────────────────────
    Porcentaje de operaciones que terminaron con ganancia.
        100% → todas ganadoras (imposible en práctica)
         70% → 7 de cada 10 operaciones fueron ganadoras ✅
         50% → igual que lanzar una moneda al azar
         30% → la mayoría perdedoras ❌

    ¿Qué es la Media%?
    ───────────────────
    Promedio de todos los retornos (positivos y negativos).
    Una estrategia puede tener Win Rate del 60% pero Media% negativa
    si las pérdidas son mucho mayores que las ganancias.
    Por eso hay que mirar AMBAS métricas juntas.

    Parámetros
    ----------
    df_rend     : pd.DataFrame  Salida de calcular_rendimientos_futuros
    dias_futuro : list          Misma lista usada al calcular rendimientos

    Retorna
    -------
    pd.DataFrame con filas BUY/SELL y columnas:
        N             → número de señales
        Media_Nd%     → retorno promedio a N días
        WinRate_Nd%   → % de señales ganadoras a N días
    """
    # Verificación defensiva: si no hay datos o no tiene la columna "signal"
    if df_rend.empty or "signal" not in df_rend.columns:
        return pd.DataFrame()

    filas = []

    for tipo in ["BUY", "SELL"]:
        sub = df_rend[df_rend["signal"] == tipo]

        if sub.empty:
            continue

        fila = {"Señal": tipo, "N": len(sub)}

        for n in dias_futuro:
            col  = f"ret_{n}d"
            vals = sub[col].dropna()

            if len(vals) == 0:
                fila[f"Media_{n}d%"]   = np.nan
                fila[f"WinRate_{n}d%"] = np.nan
            else:
                # Retorno promedio redondeado a 2 decimales
                fila[f"Media_{n}d%"]   = round(vals.mean(), 2)
                # Win Rate: fracción de retornos positivos × 100
                fila[f"WinRate_{n}d%"] = round((vals > 0).mean() * 100, 1)

        filas.append(fila)

    return pd.DataFrame(filas).set_index("Señal")
