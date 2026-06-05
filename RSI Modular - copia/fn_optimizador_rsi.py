# =============================================================================
#  fn_optimizador_rsi.py
#  FUNCIÓN: optimizar_rsi_random
# =============================================================================
#
#  QUÉ HACE:
#    Búsqueda aleatoria de los mejores parámetros RSI para un mercado.
#    Optimiza: período RSI, banda de sobreventa, banda de sobrecompra.
#
#  PARÁMETROS A OPTIMIZAR:
#    periodo_rsi ∈ [3, 50]     → días del RSI
#    sobreventa  ∈ [10, 45]    → umbral inferior
#    sobrecompra ∈ [55, 90]    → umbral superior
#    (siempre sobreventa < sobrecompra - 5)
#
#  REUTILIZA:
#    fn_calcular_rsi.py  → calcular_rsi()
#    fn_senales.py       → detectar_senales()
#    fn_rendimientos.py  → calcular_rendimientos_futuros()
#
# =============================================================================

import random
import pandas as pd
import numpy as np
from fn_calcular_rsi import calcular_rsi
from fn_senales     import detectar_senales
from fn_rendimientos import calcular_rendimientos_futuros


def optimizar_rsi_random(df: pd.DataFrame,
                         dias_futuro: list = None,
                         n_intentos: int = 300,
                         horizonte_objetivo: int = 30,
                         min_señales: int = 10,
                         semilla: int = None) -> tuple:
    """
    Busca la mejor combinación de parámetros RSI usando Random Search.

    Parámetros
    ----------
    df                 : pd.DataFrame  Datos OHLCV con columna 'Close'
    dias_futuro        : list          Horizontes (default: [1,3,5,10,30,60,90])
    n_intentos         : int           Combinaciones aleatorias a probar (200-500)
    horizonte_objetivo : int           Horizonte para medir efectividad (30)
    min_señales        : int           Mínimo de señales BUY y SELL requeridas
                                       (evita sobreoptimización con pocas señales)
    semilla            : int           Para reproducibilidad

    Retorna
    -------
    tuple (mejor_dict, mejor_score, historial):
        mejor_dict : dict  {"periodo": int, "sobreventa": int,
                            "sobrecompra": int, "tipo_señal": str,
                            "retorno_%": float, "winrate_%": float,
                            "n_señales": int}
        mejor_score : float  Sharpe Ratio de la mejor combinación
        historial   : pd.DataFrame  Todos los intentos
    """
    if dias_futuro is None:
        dias_futuro = [1, 3, 5, 10, 30, 60, 90]

    if semilla is not None:
        random.seed(semilla)
        np.random.seed(semilla)

    # ── Rangos de búsqueda para RSI ──────────────────────────────────────────
    RANGOS = {
        "periodo":     (3, 50),    # Períodos del RSI
        "sobreventa":  (10, 45),   # Umbral inferior
        "sobrecompra": (55, 90),   # Umbral superior
    }

    col_objetivo = f"ret_{horizonte_objetivo}d"

    mejor_score = -np.inf
    mejor_dict  = None
    historial   = []

    print(f"\n  🎯 Optimizando RSI para {df.index[0].date()} → {df.index[-1].date()}")
    print(f"  📊 Intentos: {n_intentos}  |  Horizonte objetivo: {horizonte_objetivo}d")
    print(f"  🔍 Rangos: periodo∈[{RANGOS['periodo'][0]},{RANGOS['periodo'][1]}], "
          f"sobreventa∈[{RANGOS['sobreventa'][0]},{RANGOS['sobreventa'][1]}], "
          f"sobrecompra∈[{RANGOS['sobrecompra'][0]},{RANGOS['sobrecompra'][1]}]")
    print(f"  🛡️  Mínimo de señales requeridas: {min_señales}")
    print("-" * 60)

    for intento in range(1, n_intentos + 1):

        # PASO 1: Generar parámetros aleatorios
        periodo     = random.randint(RANGOS["periodo"][0],     RANGOS["periodo"][1])
        sobreventa  = random.randint(RANGOS["sobreventa"][0],  RANGOS["sobreventa"][1])
        sobrecompra = random.randint(RANGOS["sobrecompra"][0], RANGOS["sobrecompra"][1])

        # Validación: sobrecompra debe ser mayor que sobreventa
        if sobrecompra <= sobreventa + 5:
            sobrecompra = sobreventa + random.randint(5, 20)

        # PASO 2: Calcular RSI
        rsi = calcular_rsi(df["Close"], periodo)

        # PASO 3: Detectar señales
        senales = detectar_senales(rsi, sobreventa, sobrecompra)

        n_buy  = (senales ==  1).sum()
        n_sell = (senales == -1).sum()

        # Validación: mínimo de señales requeridas
        if n_buy < min_señales or n_sell < min_señales:
            continue

        # PASO 4: Calcular rendimientos futuros
        df_rend = calcular_rendimientos_futuros(
            df["Close"], senales, dias_futuro
        )

        if df_rend.empty or "signal" not in df_rend.columns:
            continue

        # PASO 5: Evaluar BUY y SELL por separado
        for tipo in ["BUY", "SELL"]:
            sub = df_rend[df_rend["signal"] == tipo]

            if len(sub) < min_señales:
                continue

            vals = sub[col_objetivo].dropna()
            if len(vals) < min_señales:
                continue

            retorno = vals.mean()
            volat   = vals.std()
            winrate = (vals > 0).mean() * 100

            if volat > 0.001:
                sharpe = (retorno / volat) * np.sqrt(252 / horizonte_objetivo)
            else:
                sharpe = 0.0

            banda_str = f"{sobreventa}/{sobrecompra}"

            registro = {
                "intento":      intento,
                "periodo_rsi":  periodo,
                "sobreventa":   sobreventa,
                "sobrecompra":  sobrecompra,
                "banda":        banda_str,
                "tipo_señal":   tipo,
                "n_señales":    len(sub),
                "retorno_%":    round(retorno, 2),
                "volatilidad":  round(volat, 2),
                "winrate_%":    round(winrate, 1),
                "sharpe":       round(sharpe, 3),
            }
            historial.append(registro)

            if sharpe > mejor_score:
                mejor_score = sharpe
                mejor_dict  = registro.copy()

                print(f"  ✅ Intento {intento:4d}: "
                      f"RSI({periodo:2d}) [{sobreventa:2d}/{sobrecompra:2d}] "
                      f"| {tipo:4s} | "
                      f"Sharpe={sharpe:6.3f} | "
                      f"Ret={retorno:6.2f}% | WR={winrate:5.1f}% | "
                      f"N={len(sub)}")

    print("-" * 60)

    if mejor_dict is None:
        print("  ❌ No se encontró ninguna combinación válida.")
        return None, None, pd.DataFrame(historial)

    print(f"\n  🏆 MEJOR COMBINACIÓN RSI ENCONTRADA:")
    print(f"     RSI({mejor_dict['periodo_rsi']}) "
          f"banda [{mejor_dict['sobreventa']}/{mejor_dict['sobrecompra']}]")
    print(f"     Señal:  {mejor_dict['tipo_señal']}")
    print(f"     Sharpe: {mejor_dict['sharpe']:.3f}")
    print(f"     Retorno a {horizonte_objetivo}d: {mejor_dict['retorno_%']:.2f}%")
    print(f"     Win Rate: {mejor_dict['winrate_%']:.1f}%")
    print(f"     N señales: {mejor_dict['n_señales']}")

    return mejor_dict, mejor_score, pd.DataFrame(historial)