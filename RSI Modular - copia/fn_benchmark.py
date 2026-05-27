# =============================================================================
#  fn_benchmark.py
#  FUNCIÓN: calcular_benchmark
# =============================================================================
#
#  QUÉ HACE:
#    Calcula el rendimiento de la estrategia "Buy and Hold" (BnH)
#    como punto de referencia para comparar con nuestras señales RSI.
#
#  ¿QUÉ ES BUY AND HOLD?
#  ─────────────────────────────────────────────────────────────────────────
#  Es la estrategia más simple posible: comprar el activo al inicio
#  del período y no hacer nada — solo mantener.
#
#  Es el BENCHMARK (referencia) estándar en finanzas porque:
#    • Si nuestra estrategia RSI no supera al Buy & Hold,
#      no tiene sentido usarla (más trabajo, mismo o peor resultado)
#    • El S&P 500 históricamente sube ~10% anual — difícil de superar
#
#  MÉTRICAS QUE CALCULA:
#  ─────────────────────────────────────────────────────────────────────────
#    Retorno anual %  → rendimiento promedio anualizado del activo
#    Volatilidad %    → riesgo anual del activo
#    Sharpe Ratio     → rendimiento ajustado por riesgo del activo
#    Retorno total %  → cuánto ganó el activo en todo el período
#
#  QUÉ PUEDES MODIFICAR AQUÍ:
#    - Cambiar el factor de anualización (252 para acciones, 365 para cripto)
#    - Agregar el cálculo del máximo drawdown del período
#    - Agregar retorno por mes o por trimestre
#
#  QUÉ NO DEBES MODIFICAR:
#    - El nombre de la función: calcular_benchmark
#    - Los parámetros: (df)
#    - Las claves del diccionario de salida (otros archivos las usan)
#
# =============================================================================

import pandas as pd
import numpy as np


def calcular_benchmark(df: pd.DataFrame) -> dict:
    """
    Calcula métricas de Buy & Hold para el período completo del DataFrame.

    Parámetros
    ----------
    df : pd.DataFrame
        Datos OHLCV. Debe tener columna 'Close' con precios de cierre
        y un índice de fechas (DatetimeIndex).

    Retorna
    -------
    dict con las siguientes claves:
        "retorno_total_%"  → ganancia total del período en %
        "retorno_anual_%"  → retorno diario promedio × 252 (anualizado)
        "volatilidad_%"    → desv. estándar diaria × √252 (anualizada)
        "sharpe"           → Sharpe Ratio anualizado (sin tasa libre de riesgo)
        "dias"             → número de días de trading en el período
        "fecha_inicio"     → primera fecha del período
        "fecha_fin"        → última fecha del período
    """

    # ── Retorno diario ────────────────────────────────────────────────────────
    # pct_change() calcula la variación porcentual día a día:
    # ret_dia = (precio_hoy - precio_ayer) / precio_ayer
    retornos_diarios = df["Close"].pct_change().dropna()

    # ── Retorno total del período ─────────────────────────────────────────────
    # Comparamos el precio del último día con el del primero
    precio_inicio = df["Close"].iloc[0]   # primer precio disponible
    precio_fin    = df["Close"].iloc[-1]  # último precio disponible
    retorno_total = (precio_fin - precio_inicio) / precio_inicio * 100

    # ── Métricas anualizadas ──────────────────────────────────────────────────
    # 252 = días de trading en un año (estándar en finanzas para acciones)
    # Multiplicar por 252 convierte el promedio diario al equivalente anual
    retorno_anual  = retornos_diarios.mean() * 252 * 100   # en %
    volatilidad    = retornos_diarios.std() * np.sqrt(252) * 100  # en %

    # ── Sharpe Ratio del Buy & Hold ───────────────────────────────────────────
    # Usamos retorno/volatilidad sin restar tasa libre de riesgo (simplificado)
    # En la práctica se resta la tasa del bono del tesoro a 3 meses (~5% en 2024)
    if volatilidad != 0:
        sharpe = retorno_anual / volatilidad
    else:
        sharpe = np.nan

    # ── Resultado ─────────────────────────────────────────────────────────────
    resultado = {
        "retorno_total_%":  round(retorno_total, 2),
        "retorno_anual_%":  round(retorno_anual, 2),
        "volatilidad_%":    round(volatilidad, 2),
        "sharpe":           round(sharpe, 2),
        "dias":             len(df),
        "fecha_inicio":     df.index[0].date(),
        "fecha_fin":        df.index[-1].date(),
    }

    return resultado


def imprimir_benchmark(bnh: dict, ticker: str = "") -> None:
    """
    Imprime el benchmark de Buy & Hold en formato legible.

    Parámetros
    ----------
    bnh    : dict    Salida de calcular_benchmark
    ticker : str     Nombre del activo (para el título)
    """
    titulo = f"BENCHMARK: Buy & Hold — {ticker}" if ticker else "BENCHMARK: Buy & Hold"

    print("\n" + "=" * 55)
    print(f"  {titulo}")
    print("=" * 55)
    print(f"  Período    : {bnh['fecha_inicio']}  →  {bnh['fecha_fin']}")
    print(f"  Días       : {bnh['dias']} sesiones de trading")
    print(f"  ─────────────────────────────────────────")
    print(f"  Retorno total   : {bnh['retorno_total_%']:>8.2f} %")
    print(f"  Retorno anual   : {bnh['retorno_anual_%']:>8.2f} %")
    print(f"  Volatilidad año : {bnh['volatilidad_%']:>8.2f} %")
    print(f"  Sharpe Ratio    : {bnh['sharpe']:>8.2f}")
    print("=" * 55)
    print("  → Nuestra estrategia RSI debe superar este Sharpe")
    print("    para justificar la complejidad adicional.\n")
