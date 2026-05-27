# =============================================================================
#
#   ANÁLISIS ESTADÍSTICO DEL RSI — S&P 500
#   Versión 2.0 — Código comentado y corregido
#
#   Compatible con: Google Colab y Spyder
#
# =============================================================================
#
#   ¿QUÉ ES EL RSI?
#   ─────────────────────────────────────────────────────────────────────────
#   El RSI (Relative Strength Index) es un indicador técnico que mide la
#   "velocidad" y "magnitud" de los movimientos de precio en una escala de
#   0 a 100.
#
#   ¿Cómo se interpreta?
#     • RSI > umbral_alto  → El activo está en SOBRECOMPRA  (posible caída)
#     • RSI < umbral_bajo  → El activo está en SOBREVENTA   (posible subida)
#
#   ¿Qué estrategia usamos aquí?
#     Estrategia de REVERSIÓN A LA MEDIA (mean reversion):
#       • SEÑAL BUY  → cuando el RSI cruza HACIA ARRIBA el umbral de sobreventa
#                      Ejemplo banda 30/70: RSI pasa de <=30 a >30
#                      Interpretación: la caída exagerada terminó → esperamos subida
#
#       • SEÑAL SELL → cuando el RSI cruza HACIA ABAJO el umbral de sobrecompra
#                      Ejemplo banda 30/70: RSI pasa de >=70 a <70
#                      Interpretación: la subida exagerada terminó → esperamos caída
#
#   ¿Qué es un "cruce"?
#     Un cruce ocurre cuando el RSI TRASPASA un umbral de un día al siguiente.
#     Es importante usar cruces y no solo "RSI está en zona", porque:
#       - Evita múltiples señales seguidas en la misma zona
#       - Identifica el momento exacto de salida de la zona extrema
#
# =============================================================================
#
#   PARÁMETROS DEL ANÁLISIS:
#     • Períodos RSI:  7, 14, 20, 30, 45
#     • Bandas:        30/70 | 20/80 | 10/90
#     • Horizontes:    +1, +3, +5, +10, +30, +60, +90 días
#     • Datos:         ^GSPC (S&P 500 índice) vía yfinance — últimos 2 años
#
# =============================================================================


# ──────────────────────────────────────────────────────────────────────────────
# SECCIÓN 0: INSTALACIÓN AUTOMÁTICA DE LIBRERÍAS
# ──────────────────────────────────────────────────────────────────────────────
#
# En Google Colab, algunas librerías no vienen instaladas por defecto.
# Este bloque verifica si están disponibles y las instala si no lo están.
# En Spyder/Anaconda normalmente ya están instaladas y este bloque no hace nada.

import sys
import subprocess

def instalar_si_falta(nombre_paquete):
    """Instala un paquete de Python si no está disponible en el entorno."""
    try:
        __import__(nombre_paquete)
    except ImportError:
        print(f"  Instalando {nombre_paquete}...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", nombre_paquete, "-q"]
        )

instalar_si_falta("yfinance")
instalar_si_falta("pandas")
instalar_si_falta("numpy")
instalar_si_falta("matplotlib")


# ──────────────────────────────────────────────────────────────────────────────
# SECCIÓN 1: IMPORTACIÓN DE LIBRERÍAS
# ──────────────────────────────────────────────────────────────────────────────
#
# Cada librería tiene un propósito específico:
#   yfinance    → descargar datos históricos de precios de Yahoo Finance
#   pandas      → manipulación de tablas de datos (DataFrames)
#   numpy       → operaciones matemáticas y vectoriales eficientes
#   matplotlib  → generación de gráficas
#   warnings    → suprimir mensajes de alerta no relevantes

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec   # para controlar el tamaño de subgráficos
import matplotlib.dates as mdates        # para formatear fechas en los ejes
from matplotlib.lines import Line2D      # para crear leyendas personalizadas
import warnings
warnings.filterwarnings("ignore")        # ocultar advertencias menores de librerías


# ──────────────────────────────────────────────────────────────────────────────
# SECCIÓN 2: PARÁMETROS GLOBALES
# ──────────────────────────────────────────────────────────────────────────────
#
# Centralizamos toda la configuración aquí para que sea fácil modificarla.
# Si quieres cambiar algo (p.ej. analizar 3 años en vez de 2), solo cambia
# el valor aquí y el resto del código se adapta automáticamente.

TICKER       = "^GSPC"          # Símbolo del S&P 500 en Yahoo Finance
AÑOS_DATOS   = 2                # Ventana de tiempo del análisis en años

RSI_PERIODOS = [7, 14, 20, 30, 45]   # Períodos del RSI a analizar

# Diccionario de bandas: nombre → (umbral_sobreventa, umbral_sobrecompra)
BANDAS = {
    "30/70": (30, 70),
    "20/80": (20, 80),
    "10/90": (10, 90),
}

# Días hacia el futuro para calcular el rendimiento después de cada señal
DIAS_FUTURO = [1, 3, 5, 10, 30, 60, 90]

# ── Colores para las gráficas ──
COLOR_COMPRA    = "#00C853"   # verde brillante  → señales BUY
COLOR_VENTA     = "#D50000"   # rojo             → señales SELL
COLOR_PRECIO    = "#1565C0"   # azul oscuro      → línea de precio
COLOR_RSI       = "#6A1B9A"   # púrpura          → línea del RSI
COLOR_SOBRE_C   = "#FF6F00"   # naranja          → zona sobrecompra
COLOR_SOBRE_V   = "#00838F"   # teal             → zona sobreventa
COLOR_FONDO     = "#F8F9FA"   # gris muy claro   → fondo de gráficas
COLOR_GRILLA    = "#DEE2E6"   # gris suave       → líneas de grilla


# ──────────────────────────────────────────────────────────────────────────────
# SECCIÓN 3: DESCARGA DE DATOS
# ──────────────────────────────────────────────────────────────────────────────

print("=" * 65)
print("  ANÁLISIS ESTADÍSTICO DEL RSI — S&P 500 (^GSPC)")
print("=" * 65)

# Calculamos las fechas de inicio y fin dinámicamente
# así el análisis siempre cubre los últimos N años desde hoy
#fecha_fin    = pd.Timestamp.today()
#fecha_inicio = fecha_fin - pd.DateOffset(years=AÑOS_DATOS)
fecha_inicio = pd.Timestamp(f"{2025}-01-01")
fecha_fin    = pd.Timestamp(f"{2025}-12-31")

print(f"\n📥 Descargando datos de {TICKER}...")
print(f"   Desde: {fecha_inicio.date()}  →  Hasta: {fecha_fin.date()}")

# yf.download descarga OHLCV (Open, High, Low, Close, Volume)
# progress=False evita la barra de progreso en la consola
datos_brutos = yf.download(TICKER, start=fecha_inicio, end=fecha_fin,
                            progress=False)

# ── Limpieza de columnas ──────────────────────────────────────────────────────
# A veces yfinance devuelve columnas con múltiples niveles (MultiIndex),
# especialmente en Colab. Esto las "aplana" a un solo nivel.
if isinstance(datos_brutos.columns, pd.MultiIndex):
    datos_brutos.columns = datos_brutos.columns.get_level_values(0)

# Nos quedamos solo con las columnas que necesitamos y eliminamos filas vacías
df = datos_brutos[["Open", "High", "Low", "Close", "Volume"]].copy()
df.dropna(inplace=True)

print(f"✅ {len(df)} días de trading descargados\n")


# ──────────────────────────────────────────────────────────────────────────────
# SECCIÓN 4: CÁLCULO DEL RSI
# ──────────────────────────────────────────────────────────────────────────────
#
# Fórmula del RSI (J. Welles Wilder, 1978):
#
#   RSI = 100 - (100 / (1 + RS))
#
#   donde RS = Promedio_ganancias / Promedio_pérdidas
#
# ¿Qué es el suavizado de Wilder?
#   Wilder usó un promedio móvil exponencial (EWM) con un factor específico.
#   En pandas: ewm(com=periodo-1) equivale exactamente al suavizado de Wilder.
#   "com" es el "center of mass" — controla qué tan rápido decae el peso
#   de los datos antiguos.
#
# ¿Por qué min_periods=periodo?
#   Los primeros N valores no tienen suficiente historia para calcular el RSI,
#   por eso los dejamos como NaN (no disponibles).

def calcular_rsi(serie_precios: pd.Series, periodo: int) -> pd.Series:
    """
    Calcula el RSI usando el método de suavizado de Wilder.

    Parámetros:
        serie_precios : pd.Series con los precios de cierre
        periodo       : número de períodos (ej. 14 para el RSI estándar)

    Retorna:
        pd.Series con los valores del RSI (0 a 100)
    """
    # delta: variación de precio día a día (precio_hoy - precio_ayer)
    delta = serie_precios.diff()

    # Separamos las variaciones positivas (ganancias) de las negativas (pérdidas)
    ganancias = delta.clip(lower=0)          # días que subió el precio
    perdidas  = (-delta).clip(lower=0)       # días que bajó (convertidas a positivo)

    # Promedio exponencial ponderado (suavizado de Wilder)
    prom_ganancias = ganancias.ewm(com=periodo - 1, min_periods=periodo).mean()
    prom_perdidas  = perdidas.ewm(com=periodo - 1, min_periods=periodo).mean()

    # RS = Relative Strength (fuerza relativa)
    # replace(0, np.nan) evita división por cero cuando no hay pérdidas
    rs = prom_ganancias / prom_perdidas.replace(0, np.nan)

    # Fórmula final del RSI
    rsi = 100 - (100 / (1 + rs))

    return rsi


# ──────────────────────────────────────────────────────────────────────────────
# SECCIÓN 5: DETECCIÓN DE SEÑALES POR CRUCE
# ──────────────────────────────────────────────────────────────────────────────
#
# ¿Por qué usamos CRUCES y no niveles?
# ─────────────────────────────────────
# Si detectamos señal cada vez que RSI < 30 (nivel), obtenemos muchas señales
# seguidas mientras el RSI permanece bajo 30. Esto distorsiona el análisis.
#
# Con CRUCES, detectamos el momento exacto en que:
#   BUY  → RSI estaba <=30 ayer  Y  hoy RSI > 30   (salida de sobreventa)
#   SELL → RSI estaba >=70 ayer  Y  hoy RSI < 70   (salida de sobrecompra)
#
# El uso de .shift(1) es clave: desplaza la serie un día hacia adelante,
# de modo que en cada fila podemos comparar el valor de HOY con el de AYER.
#
# CORRECCIÓN v2: Nos aseguramos de que el RSI de HOY también sea válido (notna)
# para evitar señales fantasma al inicio de la serie donde hay NaN.

def detectar_senales(rsi: pd.Series, sobreventa: float,
                     sobrecompra: float) -> pd.Series:
    """
    Detecta señales de compra y venta usando cruces del RSI.

    Señal BUY  (+1): RSI cruza HACIA ARRIBA el umbral de sobreventa
    Señal SELL (-1): RSI cruza HACIA ABAJO el umbral de sobrecompra
    Sin señal  ( 0): ningún cruce detectado

    Parámetros:
        rsi        : pd.Series con los valores del RSI
        sobreventa : umbral inferior (ej. 30)
        sobrecompra: umbral superior (ej. 70)

    Retorna:
        pd.Series de enteros {-1, 0, +1} con el mismo índice que rsi
    """
    senales = pd.Series(0, index=rsi.index, dtype=int)

    # rsi_ayer: desplaza la serie 1 posición → en cada fila "ayer" es el valor previo
    rsi_ayer = rsi.shift(1)

    # Condición BUY:
    #   - ayer el RSI estaba EN sobreventa (<=umbral_bajo)
    #   - hoy el RSI salió de sobreventa (>umbral_bajo)
    #   - ambos valores deben existir (notna) para evitar señales con datos incompletos
   
      
    # BUY: ayer estaba EN sobreventa, hoy SALIÓ hacia arriba
    mask_buy = (
        rsi_ayer.notna() &          # ayer el RSI tenía valor válido
        rsi.notna()      &          # hoy el RSI tiene valor válido
        (rsi_ayer <= sobreventa) &  # ayer: dentro de la zona de sobreventa
        (rsi > sobreventa)          # hoy:  salió de esa zona → cruce ↑
    )

    
    mascara_buy = (
        rsi_ayer.notna() &      # ayer el RSI tenía valor
        rsi.notna()      &      # hoy el RSI tiene valor
        (rsi_ayer >= sobreventa) &   # ayer estaba en zona de sobreventa
        (rsi <= sobreventa)           # hoy salió de esa zona → cruce hacia arriba
    )
    # hoy:  salió de esa zona → cruce ↓
    # Condición SELL:
    #   - ayer el RSI estaba EN sobrecompra (>=umbral_alto)
    #   - hoy el RSI salió de sobrecompra (<umbral_alto)
    mascara_sell = (
        rsi_ayer.notna() &
        rsi.notna()      &
        (rsi_ayer <= sobrecompra) &  # ayer estaba en zona de sobrecompra
        (rsi >= sobrecompra)          # hoy salió → cruce hacia abajo
    )

    senales[mascara_buy]  =  1
    senales[mascara_sell] = -1

    return senales


# ──────────────────────────────────────────────────────────────────────────────
# SECCIÓN 6: CÁLCULO DE RENDIMIENTOS FUTUROS
# ──────────────────────────────────────────────────────────────────────────────
#
# Para cada señal detectada, calculamos cuánto habría rendido la operación
# si hubiéramos comprado (BUY) o vendido en corto (SELL) en ese momento.
#
# ¿Cómo se calcula el rendimiento?
#   retorno = (precio_futuro - precio_señal) / precio_señal × 100
#
# Para señales BUY: un retorno positivo es bueno (el precio subió).
# Para señales SELL: invertimos el signo, porque ganamos cuando baja.
#   → retorno_ajustado_sell = -retorno_bruto
#   Así, en AMBOS casos: retorno positivo = operación ganadora.
#
# ¿Por qué usamos índices numéricos y no fechas?
#   Porque al avanzar N "días" queremos N días de TRADING (hábiles),
#   no N días calendario. Trabajar con posiciones numéricas en el array
#   es más simple y preciso para esto.

def calcular_rendimientos_futuros(cierre: pd.Series, senales: pd.Series,
                                   dias_futuro: list) -> pd.DataFrame:
    """
    Para cada señal, calcula el rendimiento % a N días después.

    Parámetros:
        cierre     : pd.Series con precios de cierre
        senales    : pd.Series {-1, 0, +1} de señales
        dias_futuro: lista de horizontes temporales [1, 3, 5, ...]

    Retorna:
        pd.DataFrame con columnas:
            fecha, señal ('BUY'/'SELL'), ret_1d, ret_3d, ..., ret_Nd
    """
    registros = []

    # Convertimos a arrays de numpy para acceso más rápido por posición
    precios = cierre.values
    fechas  = cierre.index.tolist()

    # Diccionario fecha → índice numérico para búsqueda eficiente
    mapa_idx = {fecha: i for i, fecha in enumerate(fechas)}

    for fecha, senal in senales.items():
        if senal == 0:
            continue   # ignorar días sin señal

        i_entrada = mapa_idx.get(fecha)
        if i_entrada is None:
            continue   # fecha no encontrada en los precios (no debería ocurrir)

        precio_entrada = precios[i_entrada]

        # Iniciamos el registro con la información básica de la señal
        registro = {
            "fecha":  fecha,
            "signal":  "BUY" if senal == 1 else "SELL"
        }

        # Calculamos el retorno para cada horizonte temporal
        for n in dias_futuro:
            i_salida = i_entrada + n   # posición N días después

            if i_salida < len(precios):
                precio_salida = precios[i_salida]
                retorno_bruto = (precio_salida - precio_entrada) / precio_entrada * 100

                # Para BUY:  positivo si el precio subió  → mantenemos el signo
                # Para SELL: positivo si el precio bajó   → invertimos el signo
                retorno_ajustado = retorno_bruto if senal == 1 else -retorno_bruto

                registro[f"ret_{n}d"] = retorno_ajustado
            else:
                # No hay suficientes datos futuros (señal muy reciente)
                registro[f"ret_{n}d"] = np.nan

        registros.append(registro)

    # ── Construcción del DataFrame con esquema garantizado ───────────────────
    # Si no hubo ninguna señal, pd.DataFrame([]) crea un DF sin columnas, lo
    # cual rompe cualquier filtro posterior con ["signal"].
    # Solución: definir las columnas explícitamente siempre, con o sin datos.
    columnas_esquema = ["fecha", "signal"] + [f"ret_{n}d" for n in dias_futuro]

    if not registros:
        # DataFrame vacío pero CON las columnas correctas → los filtros no fallan
        return pd.DataFrame(columns=columnas_esquema)

    df_resultado = pd.DataFrame(registros, columns=columnas_esquema)
    return df_resultado


# ──────────────────────────────────────────────────────────────────────────────
# SECCIÓN 7: EJECUCIÓN DEL ANÁLISIS PRINCIPAL
# ──────────────────────────────────────────────────────────────────────────────
#
# Aquí combinamos todo lo anterior en un bucle doble:
#   - Nivel externo: cada período del RSI (7, 14, 20, 30, 45)
#   - Nivel interno: cada banda (30/70, 20/80, 10/90)
#
# Los resultados se almacenan en un diccionario anidado:
#   resultados[periodo][nombre_banda] = {
#       "rsi":     serie con los valores RSI,
#       "senales": serie con +1/-1/0,
#       "tabla_rendimientos": DataFrame con los retornos futuros
#   }

print("⚙️  Calculando RSI, señales y rendimientos futuros...\n")

resultados = {}

for periodo in RSI_PERIODOS:
    resultados[periodo] = {}

    # Calculamos el RSI una sola vez por período (se reutiliza en las 3 bandas)
    rsi_calculado = calcular_rsi(df["Close"], periodo)

    for nombre_banda, (nivel_sv, nivel_sc) in BANDAS.items():

        # Detectamos señales de cruce para esta combinación período/banda
        senales = detectar_senales(rsi_calculado, nivel_sv, nivel_sc)

        # Calculamos los rendimientos futuros de cada señal
        tabla_rend = calcular_rendimientos_futuros(df["Close"], senales, DIAS_FUTURO)

        # Guardamos todo en el diccionario de resultados
        resultados[periodo][nombre_banda] = {
            "rsi":                 rsi_calculado,
            "senales":             senales,
            "tabla_rendimientos":  tabla_rend,
        }

        # Resumen rápido para verificar que se generaron señales
        n_buy  = (senales ==  1).sum()
        n_sell = (senales == -1).sum()
        print(f"  RSI({periodo:2d}) | Banda {nombre_banda} → "
              f"{n_buy:3d} señales BUY  | {n_sell:3d} señales SELL")

print("\n✅ Cálculo completado.\n")


# ──────────────────────────────────────────────────────────────────────────────
# SECCIÓN 8: GENERACIÓN DE TABLAS ESTADÍSTICAS
# ──────────────────────────────────────────────────────────────────────────────
#
# Para cada combinación período/banda mostramos dos métricas clave:
#
#   Media% (retorno promedio):
#     El rendimiento promedio de todas las señales a N días.
#     Positivo = en promedio, la estrategia ganó dinero.
#     Negativo = en promedio, la estrategia perdió dinero.
#
#   Win Rate% (tasa de acierto):
#     Porcentaje de señales que resultaron en ganancia.
#     50% = al azar | >60% = potencialmente útil | >70% = muy bueno

print("=" * 65)
print("  TABLAS ESTADÍSTICAS DE RENDIMIENTOS FUTUROS")
print("=" * 65)

columnas_ret = [f"ret_{n}d" for n in DIAS_FUTURO]

def construir_tabla_resumen(periodo: int, nombre_banda: str) -> pd.DataFrame:
    """
    Construye una tabla con Media% y WinRate% para BUY y SELL.
    """
    tabla_rend = resultados[periodo][nombre_banda]["tabla_rendimientos"]

    # tabla_rend siempre tiene el esquema correcto (con columna "signal"),
    # pero puede estar vacío si no se generó ninguna señal para esta combinación.
    if tabla_rend.empty:
        return pd.DataFrame()

    filas = []
    for tipo_senal in ["BUY", "SELL"]:
        sub = tabla_rend[tabla_rend["signal"] == tipo_senal]
        if sub.empty:
            continue

        fila = {"Señal": tipo_senal, "N_señales": len(sub)}

        for col in columnas_ret:
            etiqueta = col.split("_")[1]   # extrae "1d", "3d", etc.
            valores  = sub[col].dropna()

            if len(valores) == 0:
                fila[f"Media_{etiqueta}"]   = np.nan
                fila[f"WinRate_{etiqueta}"] = np.nan
            else:
                fila[f"Media_{etiqueta}"]   = round(valores.mean(), 2)
                fila[f"WinRate_{etiqueta}"] = round((valores > 0).mean() * 100, 1)

        filas.append(fila)

    return pd.DataFrame(filas).set_index("Señal")

# Imprimimos las tablas de cada combinación
for periodo in RSI_PERIODOS:
    for nombre_banda in BANDAS:
        nivel_sv, nivel_sc = BANDAS[nombre_banda]
        tabla = construir_tabla_resumen(periodo, nombre_banda)

        encabezado = (f"RSI({periodo})  |  Banda {nombre_banda}  "
                      f"[Sobreventa={nivel_sv}  |  Sobrecompra={nivel_sc}]")

        print(f"\n{'─' * 65}")
        print(f"  {encabezado}")
        print(f"{'─' * 65}")

        if tabla.empty:
            print("  ⚠️  Sin señales en este período/banda.")
            continue

        # Columnas de Media%
        cols_media   = [c for c in tabla.columns if c.startswith("Media_")]
        # Columnas de WinRate%
        cols_winrate = [c for c in tabla.columns if c.startswith("WinRate_")]

        print("\n  ▸ Retorno promedio (%) — positivo = operación ganadora en promedio")
        tbl_m = tabla[["N_señales"] + cols_media].copy()
        tbl_m.columns = ["N"] + [c.replace("Media_", "+") for c in cols_media]
        print(tbl_m.to_string())

        print("\n  ▸ Win Rate (%) — porcentaje de señales ganadoras")
        tbl_w = tabla[cols_winrate].copy()
        tbl_w.columns = [c.replace("WinRate_", "+") for c in cols_winrate]
        print(tbl_w.to_string())


# ──────────────────────────────────────────────────────────────────────────────
# SECCIÓN 9: TABLA COMPARATIVA MAESTRA
# ──────────────────────────────────────────────────────────────────────────────
#
# Esta tabla resume TODAS las combinaciones en una sola vista,
# mostrando los retornos a 10d, 30d y 90d para comparar fácilmente
# cuál período y banda funcionó mejor.

print("\n\n" + "=" * 65)
print("  TABLA COMPARATIVA MAESTRA — Eficiencia por período y banda")
print("=" * 65)

filas_resumen = []
for periodo in RSI_PERIODOS:
    for nombre_banda in BANDAS:
        tabla_rend = resultados[periodo][nombre_banda]["tabla_rendimientos"]

        # Saltar si no hubo señales en esta combinación
        if tabla_rend.empty:
            continue

        for tipo_senal in ["BUY", "SELL"]:
            sub = tabla_rend[tabla_rend["signal"] == tipo_senal]
            if sub.empty:
                continue

            r10 = sub["ret_10d"].dropna()
            r30 = sub["ret_30d"].dropna()
            r90 = sub["ret_90d"].dropna()

            filas_resumen.append({
                "RSI_Período":  periodo,
                "Banda":        nombre_banda,
                "Señal":        tipo_senal,
                "N_señales":    len(sub),
                "Media_10d%":   round(r10.mean(), 2) if len(r10) else np.nan,
                "WR_10d%":      round((r10 > 0).mean() * 100, 1) if len(r10) else np.nan,
                "Media_30d%":   round(r30.mean(), 2) if len(r30) else np.nan,
                "WR_30d%":      round((r30 > 0).mean() * 100, 1) if len(r30) else np.nan,
                "Media_90d%":   round(r90.mean(), 2) if len(r90) else np.nan,
                "WR_90d%":      round((r90 > 0).mean() * 100, 1) if len(r90) else np.nan,
            })

df_resumen = pd.DataFrame(filas_resumen)
print(df_resumen.to_string(index=False))


# ──────────────────────────────────────────────────────────────────────────────
# SECCIÓN 10: GRÁFICAS PRECIO + RSI CON SEÑALES
# ──────────────────────────────────────────────────────────────────────────────
#
# Para cada combinación período/banda generamos un gráfico de 2 paneles:
#
#   Panel superior (70% del alto): Precio de cierre del S&P 500
#     • Línea azul = precio
#     • Triángulos VERDES ▲ = señales BUY (en el precio de ese día)
#     • Triángulos ROJOS  ▼ = señales SELL (en el precio de ese día)
#     • Líneas verticales semitransparentes = marcan cada señal
#
#   Panel inferior (30% del alto): Línea del RSI
#     • Línea púrpura = RSI
#     • Zona sombreada naranja = sobrecompra
#     • Zona sombreada teal    = sobreventa
#     • Los mismos triángulos en las posiciones del RSI
#
#   ¿Por qué los triángulos deben coincidir con las zonas?
#     BUY  → triángulo verde aparece justo cuando el RSI SALE de sobreventa
#             (el día que cruza el umbral hacia arriba)
#     SELL → triángulo rojo aparece justo cuando el RSI SALE de sobrecompra
#             (el día que cruza el umbral hacia abajo)

print("\n\n📊 Generando gráficas de precio + RSI con señales...")

def graficar_rsi(periodo: int, nombre_banda: str):
    """
    Genera y guarda el gráfico de precio + RSI con señales marcadas.
    """
    nivel_sv, nivel_sc = BANDAS[nombre_banda]
    datos_combo  = resultados[periodo][nombre_banda]
    rsi_serie    = datos_combo["rsi"]
    senales      = datos_combo["senales"]

    # Extraemos las fechas de cada tipo de señal
    fechas_buy  = senales[senales ==  1].index
    fechas_sell = senales[senales == -1].index

    # ── Crear la figura con dos paneles ──────────────────────────────────────
    fig = plt.figure(figsize=(16, 9), facecolor=COLOR_FONDO)
    fig.suptitle(
        f"S&P 500  |  RSI({periodo})  |  Banda {nombre_banda}  "
        f"[Sobreventa ≤{nivel_sv}  |  Sobrecompra ≥{nivel_sc}]",
        fontsize=14, fontweight="bold", y=0.98, color="#212529"
    )

    # GridSpec: define el tamaño relativo de cada panel
    # height_ratios=[2.5, 1] → el panel superior ocupa 71% del alto
    gs  = gridspec.GridSpec(2, 1, height_ratios=[2.5, 1], hspace=0.06)
    ax1 = fig.add_subplot(gs[0])    # panel superior: precio
    ax2 = fig.add_subplot(gs[1], sharex=ax1)   # panel inferior: RSI (eje x compartido)

    # ── PANEL SUPERIOR: PRECIO ────────────────────────────────────────────────

    ax1.set_facecolor(COLOR_FONDO)

    # Línea de precio
    ax1.plot(df.index, df["Close"],
             color=COLOR_PRECIO, linewidth=1.3,
             label="S&P 500 Cierre", zorder=2)

    # Señales BUY sobre el precio
    for fecha in fechas_buy:
        if fecha in df.index:
            precio_en_senal = df.loc[fecha, "Close"]
            # Línea vertical semitransparente (visual ayuda)
            ax1.axvline(fecha, color=COLOR_COMPRA, alpha=0.20,
                        linewidth=0.8, zorder=1)
            # Triángulo apuntando hacia arriba ▲
            ax1.scatter(fecha, precio_en_senal,
                        color=COLOR_COMPRA, marker="^",
                        s=70, zorder=5, edgecolors="white", linewidths=0.5)

    # Señales SELL sobre el precio
    for fecha in fechas_sell:
        if fecha in df.index:
            precio_en_senal = df.loc[fecha, "Close"]
            ax1.axvline(fecha, color=COLOR_VENTA, alpha=0.20,
                        linewidth=0.8, zorder=1)
            # Triángulo apuntando hacia abajo ▼
            ax1.scatter(fecha, precio_en_senal,
                        color=COLOR_VENTA, marker="v",
                        s=70, zorder=5, edgecolors="white", linewidths=0.5)

    ax1.set_ylabel("Precio (USD)", fontsize=10, color="#495057")
    ax1.tick_params(labelbottom=False)  # ocultamos etiquetas de fecha (las muestra ax2)
    ax1.grid(True, color=COLOR_GRILLA, linewidth=0.6, linestyle="--", zorder=0)
    ax1.spines[["top", "right"]].set_visible(False)

    # Leyenda personalizada
    elementos_leyenda = [
        Line2D([0], [0], color=COLOR_PRECIO, linewidth=1.8,
               label="Precio Cierre"),
        Line2D([0], [0], marker="^", color="w", markerfacecolor=COLOR_COMPRA,
               markersize=10, label=f"BUY — {len(fechas_buy)} señales "
                                    f"(RSI cruza >{nivel_sv})"),
        Line2D([0], [0], marker="v", color="w", markerfacecolor=COLOR_VENTA,
               markersize=10, label=f"SELL — {len(fechas_sell)} señales "
                                    f"(RSI cruza <{nivel_sc})"),
    ]
    ax1.legend(handles=elementos_leyenda, loc="upper left",
               fontsize=9, framealpha=0.88, edgecolor=COLOR_GRILLA)

    # ── PANEL INFERIOR: RSI ───────────────────────────────────────────────────

    ax2.set_facecolor(COLOR_FONDO)

    # Línea del RSI
    ax2.plot(rsi_serie.index, rsi_serie.values,
             color=COLOR_RSI, linewidth=1.0,
             label=f"RSI({periodo})", zorder=3)

    # Sombreado de zonas extremas
    ax2.axhspan(nivel_sc, 100,     alpha=0.10, color=COLOR_SOBRE_C,
                label=f"Sobrecompra ≥{nivel_sc}")
    ax2.axhspan(0,        nivel_sv, alpha=0.10, color=COLOR_SOBRE_V,
                label=f"Sobreventa ≤{nivel_sv}")

    # Líneas de umbral punteadas
    ax2.axhline(nivel_sc, color=COLOR_SOBRE_C, linewidth=1.1,
                linestyle="--", alpha=0.85)
    ax2.axhline(nivel_sv, color=COLOR_SOBRE_V, linewidth=1.1,
                linestyle="--", alpha=0.85)
    # Línea central en 50 (zona neutra del RSI)
    ax2.axhline(50, color="#ADB5BD", linewidth=0.7, linestyle=":")

    # Señales BUY en el RSI
    for fecha in fechas_buy:
        if fecha in rsi_serie.index:
            valor_rsi = rsi_serie.loc[fecha]
            if pd.notna(valor_rsi):   # solo si el RSI tiene valor en esa fecha
                ax2.scatter(fecha, valor_rsi,
                            color=COLOR_COMPRA, marker="^",
                            s=55, zorder=5, edgecolors="white", linewidths=0.5)

    # Señales SELL en el RSI
    for fecha in fechas_sell:
        if fecha in rsi_serie.index:
            valor_rsi = rsi_serie.loc[fecha]
            if pd.notna(valor_rsi):
                ax2.scatter(fecha, valor_rsi,
                            color=COLOR_VENTA, marker="v",
                            s=55, zorder=5, edgecolors="white", linewidths=0.5)

    ax2.set_ylim(0, 100)
    ax2.set_ylabel(f"RSI({periodo})", fontsize=10, color="#495057")
    ax2.set_xlabel("Fecha", fontsize=10, color="#495057")
    ax2.grid(True, color=COLOR_GRILLA, linewidth=0.6, linestyle="--", zorder=0)
    ax2.spines[["top", "right"]].set_visible(False)
    ax2.legend(loc="upper left", fontsize=8, framealpha=0.88,
               edgecolor=COLOR_GRILLA)

    # Formato del eje de fechas
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax2.xaxis.get_majorticklabels(),
             rotation=30, ha="right", fontsize=8)

    plt.tight_layout(rect=[0, 0, 1, 0.97])

    # Guardamos la imagen
    nombre_archivo = f"RSI{periodo}_{nombre_banda.replace('/', '-')}_SP500.png"
    plt.savefig(nombre_archivo, dpi=150, bbox_inches="tight",
                facecolor=COLOR_FONDO)
    plt.show()
    print(f"  ✅  Guardada: {nombre_archivo}")


# Generamos los 15 gráficos (5 períodos × 3 bandas)
total_graficos = len(RSI_PERIODOS) * len(BANDAS)
contador       = 0

for periodo in RSI_PERIODOS:
    for nombre_banda in BANDAS:
        contador += 1
        print(f"\n  [{contador}/{total_graficos}]  RSI({periodo}) — Banda {nombre_banda}")
        graficar_rsi(periodo, nombre_banda)


# ──────────────────────────────────────────────────────────────────────────────
# SECCIÓN 11: HEATMAP DE WIN RATE A 30 DÍAS
# ──────────────────────────────────────────────────────────────────────────────
#
# Un heatmap (mapa de calor) colorea cada celda según su valor:
#   Verde  = Win Rate alto (>60%) → la estrategia acertó frecuentemente
#   Rojo   = Win Rate bajo (<40%) → la estrategia erró frecuentemente
#   Amarillo = Win Rate neutro (~50%) → similar al azar
#
# Cada fila = un período del RSI
# Cada columna = una banda
# Dos tablas separadas: una para BUY y otra para SELL

print("\n\n📊 Generando heatmap de eficiencia (Win Rate a 30 días)...")

fig, ejes = plt.subplots(1, 2, figsize=(14, 6), facecolor=COLOR_FONDO)
fig.suptitle(
    "Mapa de Calor — Win Rate (%) a 30 días\n"
    "S&P 500 — Estrategia de Reversión con RSI",
    fontsize=13, fontweight="bold", color="#212529"
)

for idx_ax, tipo_senal in enumerate(["BUY", "SELL"]):
    ax = ejes[idx_ax]
    ax.set_facecolor(COLOR_FONDO)

    # Construir la matriz de Win Rates
    matriz = []
    for periodo in RSI_PERIODOS:
        fila_valores = []
        for nombre_banda in BANDAS:
            tabla_rend = resultados[periodo][nombre_banda]["tabla_rendimientos"]
            if tabla_rend.empty:
                win_rate = np.nan
            else:
                sub = tabla_rend[tabla_rend["signal"] == tipo_senal]["ret_30d"].dropna()
                win_rate = (sub > 0).mean() * 100 if len(sub) > 0 else np.nan
            fila_valores.append(win_rate)
        matriz.append(fila_valores)

    mat = np.array(matriz, dtype=float)

    # Mostrar la matriz como imagen con colores
    # vmin=30, vmax=70 → rango de colores centrado en 50% (azar)
    im = ax.imshow(mat, cmap="RdYlGn", vmin=30, vmax=70, aspect="auto")

    # Etiquetas de ejes
    ax.set_xticks(range(len(BANDAS)))
    ax.set_xticklabels(list(BANDAS.keys()), fontsize=11)
    ax.set_yticks(range(len(RSI_PERIODOS)))
    ax.set_yticklabels([f"RSI({p})" for p in RSI_PERIODOS], fontsize=11)

    color_titulo = COLOR_COMPRA if tipo_senal == "BUY" else COLOR_VENTA
    ax.set_title(f"Señales {tipo_senal}", fontsize=12,
                 fontweight="bold", color=color_titulo, pad=12)

    # Anotación del valor en cada celda
    for i in range(len(RSI_PERIODOS)):
        for j in range(len(BANDAS)):
            val = mat[i, j]
            texto = f"{val:.1f}%" if not np.isnan(val) else "N/A"
            # Color del texto: negro en zona media, blanco en extremos
            color_texto = "black" if 38 < val < 65 else "white"
            ax.text(j, i, texto, ha="center", va="center",
                    fontsize=12, fontweight="bold", color=color_texto)

    plt.colorbar(im, ax=ax, label="Win Rate (%)", shrink=0.85)

plt.tight_layout()
nombre_hm = "RSI_Heatmap_WinRate30d_SP500.png"
plt.savefig(nombre_hm, dpi=150, bbox_inches="tight", facecolor=COLOR_FONDO)
plt.show()
print(f"  ✅  Guardada: {nombre_hm}")


# ──────────────────────────────────────────────────────────────────────────────
# SECCIÓN 12: GRÁFICO DE RETORNO PROMEDIO POR HORIZONTE TEMPORAL
# ──────────────────────────────────────────────────────────────────────────────
#
# Este gráfico muestra, para cada período del RSI, cómo evoluciona el
# retorno promedio a medida que pasan los días después de la señal.
#
# ¿Cómo leerlo?
#   • Eje X: días después de la señal (1, 3, 5, 10, 30, 60, 90)
#   • Eje Y: retorno promedio en % (positivo = ganancia)
#   • Cada línea = un período del RSI
#   • Los valores son el promedio de las 3 bandas juntas
#
# ¿Qué buscamos?
#   Una línea que suba de izquierda a derecha (retorno creciente con el tiempo)
#   indica que la estrategia genera valor en ese horizonte.

print("\n📊 Generando gráfico de retorno promedio por horizonte temporal...")

fig, ejes = plt.subplots(1, 2, figsize=(16, 6),
                          facecolor=COLOR_FONDO, sharey=False)
fig.suptitle(
    "Retorno Promedio (%) por Horizonte Temporal\n"
    "S&P 500 — Señales RSI de Reversión (promedio de 3 bandas)",
    fontsize=13, fontweight="bold", color="#212529"
)

# Colores y estilos de línea distintos para cada período
colores_periodo  = ["#1565C0", "#2E7D32", "#6A1B9A", "#E65100", "#B71C1C"]
estilos_linea    = ["-", "--", "-.", ":", (0, (3, 1, 1, 1))]

for idx_ax, tipo_senal in enumerate(["BUY", "SELL"]):
    ax = ejes[idx_ax]
    ax.set_facecolor(COLOR_FONDO)

    # Línea horizontal en 0 como referencia de empate
    ax.axhline(0, color="#868E96", linewidth=1.0, linestyle="--", alpha=0.7)

    for idx_p, periodo in enumerate(RSI_PERIODOS):
        # Promediamos los retornos de las 3 bandas para ese período
        retornos_por_dia = {n: [] for n in DIAS_FUTURO}

        for nombre_banda in BANDAS:
            tabla_rend = resultados[periodo][nombre_banda]["tabla_rendimientos"]
            if tabla_rend.empty:
                continue
            sub = tabla_rend[tabla_rend["signal"] == tipo_senal]

            for n in DIAS_FUTURO:
                valores = sub[f"ret_{n}d"].dropna().tolist()
                retornos_por_dia[n].extend(valores)

        # Media de todas las observaciones para ese período y horizonte
        retornos_promedio = [
            np.mean(retornos_por_dia[n]) if retornos_por_dia[n] else np.nan
            for n in DIAS_FUTURO
        ]

        ax.plot(DIAS_FUTURO, retornos_promedio,
                color=colores_periodo[idx_p],
                linestyle=estilos_linea[idx_p],
                linewidth=2.0,
                marker="o", markersize=6,
                label=f"RSI({periodo})")

    ax.set_xlabel("Días después de la señal", fontsize=10, color="#495057")
    ax.set_ylabel("Retorno promedio (%)", fontsize=10, color="#495057")

    color_titulo = COLOR_COMPRA if tipo_senal == "BUY" else COLOR_VENTA
    ax.set_title(f"Señales {tipo_senal}", fontsize=12,
                 fontweight="bold", color=color_titulo)

    ax.set_xticks(DIAS_FUTURO)
    ax.grid(True, color=COLOR_GRILLA, linewidth=0.6, linestyle="--")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=9, framealpha=0.88, edgecolor=COLOR_GRILLA)

plt.tight_layout()
nombre_ret = "RSI_RetornoPromedio_Horizonte_SP500.png"
plt.savefig(nombre_ret, dpi=150, bbox_inches="tight", facecolor=COLOR_FONDO)
plt.show()
print(f"  ✅  Guardada: {nombre_ret}")


# ──────────────────────────────────────────────────────────────────────────────
# SECCIÓN 13: MENSAJE FINAL
# ──────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 65)
print("  ✅  ANÁLISIS COMPLETADO EXITOSAMENTE")
print("=" * 65)
print("""
ARCHIVOS GENERADOS:
  • RSI[período]_[banda]_SP500.png    → 15 gráficos de precio + RSI
  • RSI_Heatmap_WinRate30d_SP500.png  → Mapa de calor de eficiencia
  • RSI_RetornoPromedio_Horizonte...  → Retorno por horizonte temporal

CÓMO INTERPRETAR LOS RESULTADOS:
  • BUY  → entrada LARGA: ganamos si el precio SUBE después de la señal
  • SELL → entrada CORTA: ganamos si el precio BAJA después de la señal
    (los retornos ya están ajustados: positivo = operación ganadora)

  Win Rate > 55%  → la señal tuvo más aciertos que errores
  Win Rate = 50%  → equivalente a lanzar una moneda al azar
  Media% > 0      → en promedio, la operación fue rentable

NOTA SOBRE LAS SEÑALES EN LAS GRÁFICAS (v2):
  Los triángulos ahora aparecen exactamente el día del CRUCE del RSI,
  no dentro de la zona extrema. Esto garantiza coherencia visual entre
  el gráfico de precio y el del RSI.

PARA EJECUTAR:
  • Google Colab : pega el código en una celda → Shift+Enter
  • Spyder       : abre este archivo → F5
""")
