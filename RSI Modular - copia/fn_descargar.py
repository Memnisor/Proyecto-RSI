# =============================================================================
#  fn_descargar.py
#  FUNCIÓN: descargar_datos
# =============================================================================
#
#  FIX APLICADO:
#    Las fechas estaban hardcodeadas a 2025-01-01 / 2025-12-31,
#    ignorando el parámetro `años`. Ahora se calculan dinámicamente:
#
#      fecha_fin    = hoy
#      fecha_inicio = hoy - años
#
#    Con AÑOS = 5 descargará ~1250 días de historia en lugar de ~249.
#
# =============================================================================

import pandas as pd

API_KEY_ALPHA = "SR5GAQCUZL0X73MC"
MIN_DIAS      = 50

TICKERS_ALPHA = {
    "^COLCAP":   "GXG",
    "^SPBLPGPT": "EPU",
    "^IGBVL":    "EPU",
    "^IBC":      "ILF",
    "^ECUINDEX": "ILF",
    "^BVMBG":    "EWZ",
    "^IACR":     "ILF",
}


def _desde_yfinance(ticker: str, años: int, intervalo: str) -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError:
        import subprocess, sys
        subprocess.check_call([sys.executable, "-m", "pip",
                               "install", "yfinance", "-q"])
        import yfinance as yf

    # ── CORRECCIÓN: fechas dinámicas usando el parámetro años ────────────────
    # BUG ORIGINAL: las fechas estaban hardcodeadas a 2025, ignorando 'años'.
    # SOLUCIÓN: calcular desde hoy hacia atrás N años.
    fecha_fin    = pd.Timestamp.today()
    fecha_inicio = fecha_fin - pd.DateOffset(years=años)

    datos = yf.download(ticker,
                        start=fecha_inicio,
                        end=fecha_fin,
                        interval=intervalo,
                        progress=False)

    if isinstance(datos.columns, pd.MultiIndex):
        datos.columns = datos.columns.get_level_values(0)

    if datos.empty or "Close" not in datos.columns:
        return pd.DataFrame()

    cols = [c for c in ["Open","High","Low","Close","Volume"]
            if c in datos.columns]
    df = datos[cols].copy()
    df.dropna(inplace=True)
    return df


def _desde_alpha_vantage(ticker: str, años: int) -> pd.DataFrame:
    try:
        from alpha_vantage.timeseries import TimeSeries
    except ImportError:
        import subprocess, sys
        print("  Instalando alpha_vantage...")
        subprocess.check_call([sys.executable, "-m", "pip",
                               "install", "alpha_vantage", "-q"])
        from alpha_vantage.timeseries import TimeSeries

    ticker_av = TICKERS_ALPHA.get(ticker, ticker)
    ticker_av = ticker_av.replace("^", "")
    print(f"  Ticker Alpha Vantage: {ticker_av}")

    try:
        ts    = TimeSeries(key=API_KEY_ALPHA, output_format="pandas")
        datos, meta = ts.get_daily_adjusted(symbol=ticker_av,
                                             outputsize="full")
        datos.columns = ["Open", "High", "Low", "Close",
                         "Adj_Close", "Volume", "Dividend", "Split"]
        datos = datos.sort_index(ascending=True)

        fecha_inicio = pd.Timestamp.today() - pd.DateOffset(years=años)
        datos = datos[datos.index >= fecha_inicio]

        df = datos[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.dropna(inplace=True)
        return df

    except Exception as e:
        print(f"  Alpha Vantage falló: {e}")
        return pd.DataFrame()


def descargar_datos(ticker: str,
                    años: int = 2,
                    intervalo: str = "1d") -> pd.DataFrame:
    """
    Descarga precios históricos con fallback automático entre fuentes.

    Parámetros
    ----------
    ticker   : str   Símbolo del activo ("^GSPC", "^BVSP", "GXG", etc.)
    años     : int   Años de historia a descargar — ahora funciona correctamente
    intervalo: str   "1d" diario, "1wk" semanal, "1mo" mensual
    """
    print(f"\n{'─'*50}")
    print(f"  Descargando: {ticker}  ({años} años)")
    print(f"{'─'*50}")

    print(f"  Fuente 1: Yahoo Finance...")
    df = _desde_yfinance(ticker, años, intervalo)

    if len(df) >= MIN_DIAS:
        print(f"  ✅ Yahoo Finance: {len(df)} días  "
              f"({df.index[0].date()} → {df.index[-1].date()})\n")
        return df

    print(f"  Yahoo Finance: solo {len(df)} días (mínimo {MIN_DIAS}).")
    print(f"  Fuente 2: Alpha Vantage...")

    if intervalo != "1d":
        print(f"  Nota: Alpha Vantage no soporta intervalo '{intervalo}'.")

    df = _desde_alpha_vantage(ticker, años)

    if len(df) >= MIN_DIAS:
        print(f"  ✅ Alpha Vantage: {len(df)} días  "
              f"({df.index[0].date()} → {df.index[-1].date()})\n")
        return df

    print(f"  ❌ No se pudieron obtener datos para {ticker}.")
    print(f"  Verifica el ticker o usa un ETF equivalente.")
    print(f"  El bucle continuará con el siguiente activo.\n")
    return pd.DataFrame()