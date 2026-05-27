# =============================================================================
#  fn_descargar.py
#  FUNCIÓN: descargar_datos
# =============================================================================
#
#  QUÉ HACE:
#    Conecta a Yahoo Finance y descarga los precios históricos
#    de cualquier activo (S&P 500, acciones, ETFs, etc.)
#
#  QUÉ PUEDES MODIFICAR AQUÍ:
#    - El mensaje que imprime en consola
#    - Las columnas que retorna (ej. agregar "Adj Close")
#    - El manejo de errores si no hay internet
#
#  QUÉ NO DEBES MODIFICAR:
#    - El nombre de la función: descargar_datos
#    - Los parámetros que recibe: (ticker, años)
#    - Las columnas que retorna: Open, High, Low, Close, Volume
#    (si los cambias, los otros archivos dejarán de funcionar)
#
# =============================================================================

import pandas as pd


def descargar_datos(ticker: str, años: int = 2) -> pd.DataFrame:
    """
    Descarga precios históricos de Yahoo Finance.

    Parámetros
    ----------
    ticker : str   Símbolo del activo. Ejemplos:
                     "^GSPC" → S&P 500
                     "SPY"   → ETF del S&P 500
                     "AAPL"  → Apple
    años   : int   Cuántos años hacia atrás descargar (por defecto 2)

    Retorna
    -------
    pd.DataFrame con columnas: Open, High, Low, Close, Volume
    El índice es la fecha (DatetimeIndex).
    """
    # Instalación automática si yfinance no está disponible
    try:
        import yfinance as yf
    except ImportError:
        import subprocess, sys
        print("  Instalando yfinance...")
        subprocess.check_call([sys.executable, "-m", "pip", "install",
                               "yfinance", "-q"])
        import yfinance as yf

    # Calculamos las fechas dinámicamente
    # → siempre cubre los últimos N años desde hoy
    fecha_fin    = pd.Timestamp.today()
    fecha_inicio = fecha_fin - pd.DateOffset(years=años)

    print(f"📥 Descargando {ticker}...")
    print(f"   Desde: {fecha_inicio.date()}  →  Hasta: {fecha_fin.date()}")

    datos = yf.download(ticker,
                        start=fecha_inicio,
                        end=fecha_fin,
                        progress=False)

    # yfinance a veces retorna columnas con múltiples niveles (MultiIndex)
    # Esto las aplana a un solo nivel para que funcionen normalmente
    if isinstance(datos.columns, pd.MultiIndex):
        datos.columns = datos.columns.get_level_values(0)

    # Nos quedamos solo con las columnas necesarias
    df = datos[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.dropna(inplace=True)   # eliminamos filas con datos faltantes

    print(f"✅ {len(df)} días de trading descargados.\n")
    return df
