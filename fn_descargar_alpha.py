# fn_descargar_alpha.py
# Descarga datos desde Alpha Vantage
# Usar cuando yfinance no tiene el índice o activo

from alpha_vantage.timeseries import TimeSeries
import pandas as pd

API_KEY = "SR5GAQCUZL0X73MC"   # ← pega aquí tu clave

def descargar_datos_alpha(ticker: str,
                           años: int = 2,
                           outputsize: str = "full") -> pd.DataFrame:
    """
    Descarga precios históricos desde Alpha Vantage.

    Diferencias con yfinance:
      - Necesita API key (gratuita en alphavantage.co)
      - Límite de 25 llamadas por día en plan gratuito
      - Mejor cobertura de mercados latinoamericanos
      - outputsize: "compact" = últimos 100 días
                    "full"    = hasta 20 años de historia

    Tickers latinoamericanos en Alpha Vantage:
      Colombia → COLCAP.BOG  o  GXG (ETF)
      Perú     → SPBLPGPT.LIM
      Venezuela → no disponible
      Brasil   → BVSP.SAO
    """
    print(f"📥 Descargando {ticker} desde Alpha Vantage...")

    # TimeSeries es la clase para datos de precios diarios
    ts = TimeSeries(key=API_KEY, output_format="pandas")

    # get_daily_adjusted incluye ajuste por dividendos y splits
    datos, meta = ts.get_daily_adjusted(symbol=ticker,
                                         outputsize=outputsize)

    # Alpha Vantage retorna columnas con números — las renombramos
    datos.columns = ["Open", "High", "Low", "Close",
                     "Adj_Close", "Volume", "Dividend", "Split"]

    # Ordenamos de más antiguo a más reciente (Alpha Vantage viene al revés)
    datos = datos.sort_index(ascending=True)

    # Filtramos los últimos N años
    fecha_inicio = pd.Timestamp.today() - pd.DateOffset(years=anos)
    datos = datos[datos.index >= fecha_inicio]

    datos.dropna(inplace=True)
    print(f"✅ {len(datos)} días descargados.\n")
    return datos