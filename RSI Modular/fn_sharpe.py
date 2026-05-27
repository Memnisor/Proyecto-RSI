# =============================================================================
#  fn_sharpe.py
#  FUNCIÓN: calcular_sharpe
# =============================================================================
#
#  QUÉ HACE:
#    Calcula el Sharpe Ratio y la volatilidad para cada grupo de señales.
#
#  ¿QUÉ ES EL SHARPE RATIO?
#  ─────────────────────────────────────────────────────────────────────────
#  Es la métrica más usada en finanzas para evaluar estrategias.
#  Responde la pregunta: ¿cuánto rendimiento obtengo POR CADA UNIDAD
#  de riesgo que asumo?
#
#  Fórmula:
#      Sharpe = (Retorno_promedio / Desviación_estándar) × Factor_anual
#
#  Donde:
#      Retorno_promedio   = media de todos los retornos de las señales
#      Desviación_estándar = dispersión de esos retornos (el "riesgo")
#      Factor_anual       = √(252 / N_días) para anualizarlo
#                           252 = días de trading en un año
#
#  ¿Cómo interpretar el Sharpe?
#      < 0.0  → estrategia destructora de valor ❌
#      0 a 1  → retorno existe pero el riesgo es alto
#      1 a 2  → buena estrategia ✅
#      > 2.0  → estrategia excelente ✅✅ (raro en la práctica)
#
#  ¿QUÉ ES LA VOLATILIDAD?
#  ─────────────────────────────────────────────────────────────────────────
#  Es la desviación estándar de los retornos — mide qué tan dispersos
#  son los resultados. Alta volatilidad = resultados muy impredecibles.
#
#  QUÉ PUEDES MODIFICAR AQUÍ:
#    - Agregar el Sortino Ratio (variante que solo penaliza pérdidas)
#    - Cambiar el factor de anualización (ej. 365 para cripto)
#    - Agregar el Calmar Ratio (retorno / máximo drawdown)
#
#  QUÉ NO DEBES MODIFICAR:
#    - El nombre de la función: calcular_sharpe
#    - Los parámetros: (df_rend, dias_futuro)
#    - La estructura de salida: DataFrame con índice BUY/SELL
#
# =============================================================================

import pandas as pd
import numpy as np


def calcular_sharpe(df_rend: pd.DataFrame,
                    dias_futuro: list) -> pd.DataFrame:
    """
    Calcula Sharpe Ratio y Volatilidad para señales BUY y SELL.

    El Sharpe se anualiza usando el factor √(252/N_días), que convierte
    el Sharpe de un horizonte de N días al equivalente anual.

    Ejemplo:
        Sharpe a 10 días × √(252/10) = Sharpe anualizado

    Parámetros
    ----------
    df_rend     : pd.DataFrame  Salida de calcular_rendimientos_futuros
                                Debe tener columnas: signal, ret_1d, ret_3d...
    dias_futuro : list          Lista de horizontes, ej. [1, 3, 5, 10, 30, 60, 90]

    Retorna
    -------
    pd.DataFrame con filas BUY/SELL y columnas:
        N              → número de señales
        Sharpe_Nd      → Sharpe Ratio anualizado a N días
        Volatil_Nd%    → Volatilidad (desv. estándar) a N días en %
    """
    # Verificación defensiva: si no hay datos o falta la columna "signal"
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

            if len(vals) < 3:
                # Con menos de 3 datos no tiene sentido calcular estadísticas
                fila[f"Sharpe_{n}d"]   = np.nan
                fila[f"Volatil_{n}d%"] = np.nan
                continue

            ret_mean = vals.mean()    # retorno promedio
            ret_std  = vals.std()     # desviación estándar = volatilidad

            # Factor para anualizar el Sharpe
            # √(252/n) convierte el Sharpe de N días a equivalente anual
            factor_anual = np.sqrt(252 / n)

            # Sharpe Ratio: retorno por unidad de riesgo, anualizado
            # Si ret_std es 0 (imposible en la práctica), evitamos división por cero
            if ret_std != 0:
                sharpe = (ret_mean / ret_std) * factor_anual
            else:
                sharpe = np.nan

            fila[f"Sharpe_{n}d"]   = round(sharpe, 2)
            fila[f"Volatil_{n}d%"] = round(ret_std, 2)

        filas.append(fila)

    return pd.DataFrame(filas).set_index("Señal")
