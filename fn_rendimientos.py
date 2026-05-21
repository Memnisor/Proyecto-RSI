# =============================================================================
#  fn_rendimientos.py
#  FUNCIÓN: calcular_rendimientos_futuros
# =============================================================================
#
#  QUÉ HACE:
#    Para cada señal detectada (BUY o SELL), calcula cuánto habría
#    rendido la operación si se hubiera mantenido N días.
#
#  QUÉ PUEDES MODIFICAR AQUÍ:
#    - La fórmula del retorno (ej. usar log-retornos en vez de %)
#    - Agregar columnas extra (ej. retorno máximo, retorno mínimo,
#      máximo drawdown dentro del período)
#    - Cambiar "días de trading" por "días calendario"
#
#  QUÉ NO DEBES MODIFICAR:
#    - El nombre de la función: calcular_rendimientos_futuros
#    - Los parámetros: (cierre, senales, dias_futuro)
#    - Las columnas de salida: fecha, signal, ret_Nd
#    - La convención de signos (positivo = ganador para ambos BUY y SELL)
#
# =============================================================================

import pandas as pd
import numpy as np


def calcular_rendimientos_futuros(cierre: pd.Series,
                                   senales: pd.Series,
                                   dias_futuro: list) -> pd.DataFrame:
    """
    Calcula el rendimiento % a N días después de cada señal.

    Convención de retornos (MUY IMPORTANTE):
    ─────────────────────────────────────────
    Para poder comparar BUY y SELL en la misma tabla,
    ajustamos el signo para que SIEMPRE positivo = ganador:

        BUY  → compramos → ganamos si el precio SUBE
                retorno = (precio_futuro - precio_entrada) / precio_entrada × 100
                positivo si sube ✅

        SELL → vendemos en corto → ganamos si el precio BAJA
                retorno = -(precio_futuro - precio_entrada) / precio_entrada × 100
                positivo si baja ✅ (invertimos el signo)

    ¿Por qué días de trading y no días calendario?
    ────────────────────────────────────────────────
    Usamos posiciones numéricas en el array (i + N) en vez de sumar
    N días a la fecha. Así "+10 días" significa 10 sesiones bursátiles,
    no 10 días de calendario (que incluirían fines de semana y feriados).

    Parámetros
    ----------
    cierre      : pd.Series  Precios de cierre diarios
    senales     : pd.Series  Serie {-1, 0, +1} — salida de detectar_senales
    dias_futuro : list       Horizontes a evaluar, ej. [1, 3, 5, 10, 30, 60, 90]

    Retorna
    -------
    pd.DataFrame con columnas: fecha, signal, ret_1d, ret_3d, ..., ret_Nd
    Siempre retorna con las columnas correctas aunque no haya señales.
    """
    registros = []

    # Convertimos a arrays para acceso eficiente por posición numérica
    precios  = cierre.values
    fechas   = cierre.index.tolist()

    # Diccionario: fecha → índice numérico (posición en el array)
    # Permite encontrar la posición de una fecha en O(1)
    mapa_idx = {f: i for i, f in enumerate(fechas)}

    for fecha, senal in senales.items():
        if senal == 0:
            continue   # ignorar días sin señal

        i_entrada = mapa_idx.get(fecha)
        if i_entrada is None:
            continue

        precio_entrada = precios[i_entrada]

        registro = {
            "fecha":  fecha,
            "signal": "BUY" if senal == 1 else "SELL"
        }

        for n in dias_futuro:
            i_salida = i_entrada + n   # N sesiones bursátiles después

            if i_salida < len(precios):
                ret_bruto = (precios[i_salida] - precio_entrada) / precio_entrada * 100

                # BUY  → mantenemos el signo   (positivo si el precio subió)
                # SELL → invertimos el signo   (positivo si el precio bajó)
                registro[f"ret_{n}d"] = ret_bruto if senal == 1 else -ret_bruto
            else:
                # La señal es muy reciente — no hay datos futuros suficientes
                registro[f"ret_{n}d"] = np.nan

        registros.append(registro)

    # Esquema de columnas garantizado aunque no haya ninguna señal.
    # Sin esto, un DataFrame vacío no tendría columnas y los filtros
    # posteriores con ["signal"] lanzarían KeyError.
    cols = ["fecha", "signal"] + [f"ret_{n}d" for n in dias_futuro]

    if not registros:
        return pd.DataFrame(columns=cols)

    return pd.DataFrame(registros, columns=cols)
