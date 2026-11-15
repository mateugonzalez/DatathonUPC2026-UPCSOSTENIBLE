from pathlib import Path

import pandas as pd


_FECHA = "Fecha"
_POTENCIA = "Contador - POTENCIA ACTIVA EXPORTADA (kW)"
_POTENCIA_CONSUM = "Potencia consum"


def media_horaria_contador(
    csv_entrada: str | Path,
    csv_sortida: str | Path | None = None,
) -> pd.DataFrame:
    
    """
    Devuelve la potencia de consumo horaria calculada desde la exportada.

    Las horas se obtienen de la columna de fecha; las horas sin registros no
    se inventan. Los valores vacíos se ignoran al calcular la media. A esa media
    se aplica max(0, -P). Si se indica csv_sortida, guarda el resultado.
    """
    datos = pd.read_csv(csv_entrada, usecols=[_FECHA, _POTENCIA])
    datos[_FECHA] = pd.to_datetime(datos[_FECHA], errors="raise")
    datos[_POTENCIA] = pd.to_numeric(datos[_POTENCIA], errors="raise")
    datos[_FECHA] = datos[_FECHA].dt.floor("h")

    resultado = (
        datos.groupby(_FECHA, as_index=False, sort=True)[_POTENCIA]
        .mean()
    )
    resultado[_POTENCIA] = (-resultado[_POTENCIA]).clip(lower=0)
    resultado = resultado.rename(columns={_POTENCIA: _POTENCIA_CONSUM})

    if csv_sortida is not None:
        resultado.to_csv(csv_sortida, index=False)

    return resultado