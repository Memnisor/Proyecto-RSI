# =============================================================================
#  fn_descargar.py
#  FUNCIÓN: descargar_datos
# =============================================================================
#
#  QUÉ HACE:
#    Descarga precios históricos de cualquier activo.
#    Intenta primero con yfinance (gratuito, sin límites).
#    Si yfinance no tiene datos suficientes, usa Alpha Vantage
#    automáticamente como respaldo.
#
#  FUENTES DE DATOS:
#    1. yfinance      → Yahoo Finance, gratuito, sin registro
#                       Mejor para: índices principales, ETFs, acciones USA
#    2. Alpha Vantage → API financiera, gratuita con registro
#                       Mejor para: mercados latinoamericanos no disponibles
#                       en Yahoo Finance
#                       Límite plan gratuito: 25 llamadas por día
#
#  QUÉ PUEDES MODIFICAR AQUÍ:
#    - API_KEY_ALPHA → tu clave de Alpha Vantage
#    - MIN_DIAS      → mínimo de días para considerar la descarga válida
#    - TICKERS_ALPHA → agregar más equivalencias de tickers
#
#  QUÉ NO DEBES MODIFICAR:
#    - El nombre de la función: descargar_datos
#    - Los parámetros: (ticker, anos, intervalo)
#    - Las columnas de salida: Open, High, Low, Close, Volume
#
# =============================================================================

import pandas as pd

# ── Clave de API de Alpha Vantage ─────────────────────────────────────────────
# Obtenida en: https://www.alphavantage.co/support/#api-key
# Plan gratuito: 25 llamadas por día
API_KEY_ALPHA = "SR5GAQCUZL0X73MC"

# Mínimo de días para considerar que la descarga fue exitosa.
# Si yfinance trae menos días que esto, intentamos Alpha Vantage.
MIN_DIAS = 50

# Diccionario de equivalencias: ticker yfinance → ticker Alpha Vantage
# Cuando yfinance no encuentra un índice, buscamos aquí su equivalente.
# ETF = fondo que replica el comportamiento del índice original.
TICKERS_ALPHA = {
    "^COLCAP":   "GXG",   # Colombia → ETF iShares MSCI Colombia
    "^SPBLPGPT": "EPU",   # Perú → ETF iShares MSCI Peru
    "^IGBVL":    "EPU",   # Perú (índice alternativo) → mismo ETF
    "^IBC":      "ILF",   # Venezuela → ETF América Latina como proxy
    "^ECUINDEX": "ILF",   # Ecuador → ETF América Latina como proxy
    "^BVMBG":    "EWZ",   # Bolivia → ETF Brasil como proxy regional
    "^IACR":     "ILF",   # Costa Rica → ETF América Latina como proxy
}


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN INTERNA 1: descarga desde yfinance
# ─────────────────────────────────────────────────────────────────────────────
def _desde_yfinance(ticker: str, años: int, intervalo: str) -> pd.DataFrame:
    """
    Descarga datos desde Yahoo Finance.
    Función interna — el guión bajo indica que no se llama desde afuera.
    """
    try:
        import yfinance as yf
    except ImportError:
        import subprocess, sys
        subprocess.check_call([sys.executable, "-m", "pip",
                               "install", "yfinance", "-q"])
        import yfinance as yf

    #fecha_fin    = pd.Timestamp.today()
    #fecha_inicio = fecha_fin - pd.DateOffset(years=anos)
    fecha_inicio = pd.Timestamp(f"{2025}-01-01")
    fecha_fin    = pd.Timestamp(f"{2025}-12-31")
    datos = yf.download(ticker,
                        start=fecha_inicio,
                        end=fecha_fin,
                        interval=intervalo,
                        progress=False)

    # Aplanar MultiIndex si yfinance lo genera en algunas versiones
    if isinstance(datos.columns, pd.MultiIndex):
        datos.columns = datos.columns.get_level_values(0)

    # Verificar que existe la columna Close como mínimo
    if datos.empty or "Close" not in datos.columns:
        return pd.DataFrame()

    cols = [c for c in ["Open","High","Low","Close","Volume"]
            if c in datos.columns]
    df = datos[cols].copy()
    df.dropna(inplace=True)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN INTERNA 2: descarga desde Alpha Vantage
# ─────────────────────────────────────────────────────────────────────────────
def _desde_alpha_vantage(ticker: str, años: int) -> pd.DataFrame:
    """
    Descarga datos desde Alpha Vantage como respaldo.

    ¿Cómo funciona la conversión de tickers?
    El diccionario TICKERS_ALPHA traduce el ticker de yfinance
    al equivalente en Alpha Vantage.
    Ejemplo: "^COLCAP" → "GXG" (ETF que replica el índice colombiano)

    Alpha Vantage no acepta el símbolo "^" — se elimina automáticamente.
    Ejemplo: "^BVSP" → "BVSP"
    """
    try:
        from alpha_vantage.timeseries import TimeSeries
    except ImportError:
        import subprocess, sys
        print("  Instalando alpha_vantage...")
        subprocess.check_call([sys.executable, "-m", "pip",
                               "install", "alpha_vantage", "-q"])
        from alpha_vantage.timeseries import TimeSeries

    # Buscar equivalente en el diccionario, si no existe usar el mismo ticker
    ticker_av = TICKERS_ALPHA.get(ticker, ticker)

    # Eliminar "^" — Alpha Vantage no lo acepta
    ticker_av = ticker_av.replace("^", "")

    print(f"  Ticker Alpha Vantage: {ticker_av}")

    try:
        # TimeSeries → clase para datos de precios históricos diarios
        # output_format="pandas" → retorna directamente un DataFrame
        ts = TimeSeries(key=API_KEY_ALPHA, output_format="pandas")

        # get_daily_adjusted → incluye ajuste por dividendos y splits
        # outputsize="full" → hasta 20 años de historia disponible
        datos, meta = ts.get_daily_adjusted(symbol=ticker_av,
                                             outputsize="full")

        # Alpha Vantage retorna columnas con formato "1. open", "2. high"...
        # Las renombramos a nombres estándar
        datos.columns = ["Open", "High", "Low", "Close",
                         "Adj_Close", "Volume", "Dividend", "Split"]

        # Alpha Vantage retorna del más reciente al más antiguo
        # Ordenamos igual que yfinance: de más antiguo a más reciente
        datos = datos.sort_index(ascending=True)

        # Filtrar solo los últimos N años
        fecha_inicio = pd.Timestamp.today() - pd.DateOffset(years=anos)
        datos = datos[datos.index >= fecha_inicio]

        # Retornar solo las columnas estándar (igual que yfinance)
        df = datos[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.dropna(inplace=True)
        return df

    except Exception as e:
        print(f"  Alpha Vantage falló: {e}")
        return pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL: descargar_datos
# ─────────────────────────────────────────────────────────────────────────────
def descargar_datos(ticker: str,
                    años: int = 2,
                    intervalo: str = "1d") -> pd.DataFrame:
    """
    Descarga precios históricos con fallback automático entre fuentes.

    Flujo interno:
        1. Intenta Yahoo Finance (yfinance)
        2. Si trae menos de MIN_DIAS dias → intenta Alpha Vantage
        3. Si ambas fallan → retorna DataFrame vacío

    Todo el resto del código (fn_calcular_rsi, fn_senales, fn_grafica...)
    no sabe de dónde vienen los datos — siempre recibe el mismo formato.
    Esto es lo que se llama "abstracción": ocultar la complejidad detrás
    de una interfaz simple.

    Parámetros
    ----------
    ticker   : str   Símbolo del activo. Ejemplos:
                       "^GSPC"   → S&P 500
                       "^BVSP"   → Bovespa Brasil
                       "^COLCAP" → COLCAP Colombia (puede fallar en yfinance)
                       "GXG"     → ETF Colombia (funciona en ambas fuentes)
    anos     : int   Años de historia a descargar (por defecto 2)
    intervalo: str   Temporalidad: "1d" diario, "1wk" semanal, "1mo" mensual
                     Nota: Alpha Vantage solo soporta "1d" en plan gratuito

    Retorna
    -------
    pd.DataFrame con columnas: Open, High, Low, Close, Volume
    Índice: DatetimeIndex con fechas de trading
    """

    print(f"\n{'─'*50}")
    print(f"  Descargando: {ticker}")
    print(f"{'─'*50}")

    # ── Intento 1: Yahoo Finance ──────────────────────────────────────────────
    print(f"  Fuente 1: Yahoo Finance...")
    df = _desde_yfinance(ticker, años, intervalo)

    if len(df) >= MIN_DIAS:
        print(f"  ✅ Yahoo Finance: {len(df)} días  "
              f"({df.index[0].date()} → {df.index[-1].date()})\n")
        return df

    # ── Intento 2: Alpha Vantage ──────────────────────────────────────────────
    print(f"  Yahoo Finance: solo {len(df)} días (mínimo {MIN_DIAS}).")
    print(f"  Fuente 2: Alpha Vantage...")

    # Alpha Vantage gratuito solo tiene datos diarios
    if intervalo != "1d":
        print(f"  Nota: Alpha Vantage no soporta intervalo '{intervalo}'.")
        print(f"  Usando datos diarios como alternativa.")

    df = _desde_alpha_vantage(ticker, años)

    if len(df) >= MIN_DIAS:
        print(f"  ✅ Alpha Vantage: {len(df)} días  "
              f"({df.index[0].date()} → {df.index[-1].date()})\n")
        return df

    # ── Ambas fuentes fallaron ────────────────────────────────────────────────
    print(f"  ❌ No se pudieron obtener datos para {ticker}.")
    print(f"  Verifica el ticker o usa un ETF equivalente.")
    print(f"  El bucle continuará con el siguiente activo.\n")
    return pd.DataFrame()