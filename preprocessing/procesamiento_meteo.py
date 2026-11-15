from pathlib import Path

import pandas as pd


_FECHA = "Fecha"
_IRRADIANCIA = "Atersa - IRRADIANCIA (W/m2)"
_TEMPERATURA_PANEL = "Atersa - TEMPERATURA PANEL (SENSOR 1) (ºC)"
_TEMPERATURA_AMBIENTE = "Atersa - TEMPERATURA AMBIENTE (SENSOR 1) (ºC)"
_VIENTO = "Atersa - VELOCIDAD VIENTO (SENSOR 1) (m/s)"
_ERROR_IRRADIANCIA = "Atersa - ATERSAMET ERROR IRRADIANCIA"
_ALARMA = "Atersa - ATERSAMET ALARMA"
_MEDIDAS = [_IRRADIANCIA, _TEMPERATURA_PANEL, _TEMPERATURA_AMBIENTE, _VIENTO]


def media_horaria_meteo(
    csv_entrada: str | Path,
    csv_sortida: str | Path | None = None,
) -> pd.DataFrame:
    """
    Calcula las medias horarias de las medidas meteorológicas válidas.
    """

    columnas = [_FECHA, *_MEDIDAS, _ERROR_IRRADIANCIA, _ALARMA]
    datos = pd.read_csv(csv_entrada, usecols=columnas)
    datos[_FECHA] = pd.to_datetime(datos[_FECHA], errors="raise")

    flags = datos[[_ERROR_IRRADIANCIA, _ALARMA]].apply(
        pd.to_numeric, errors="raise"
    )
    datos = datos.loc[flags.fillna(0).eq(0).all(axis=1)].copy()
    datos[_MEDIDAS] = datos[_MEDIDAS].apply(pd.to_numeric, errors="raise")
    datos = datos.dropna(subset=_MEDIDAS, how="all")
    datos[_FECHA] = datos[_FECHA].dt.floor("h")

    resultado = (
        datos.groupby(_FECHA, as_index=False, sort=True)[_MEDIDAS]
        .mean()
    )

    if csv_sortida is not None:
        resultado.to_csv(csv_sortida, index=False)

    return resultado
