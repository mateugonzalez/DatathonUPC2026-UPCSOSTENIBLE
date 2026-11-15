"""Hourly aggregation of photovoltaic inverter active power telemetry."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

_FECHA = "Fecha"
_INV_1 = "Inversor 1 - POTENCIA ACTIVA (kW)"
_INV_2 = "Inversor 2 - POTENCIA ACTIVA (kW)"
_INV_3 = "Inversor 3 - POTENCIA ACTIVA (kW)"
_POTENCIA_ACTIVA = "Potencia activa"


def potencia_solar(inversor: str | Path) -> pd.DataFrame:
    """Compute hourly total solar PV active power (kW) across all three inverters.

    Parameters
    ----------
    inversor : str | Path
        Path to the 5-minute inverter telemetry CSV (`inversor.csv`).

    Returns
    -------
    pd.DataFrame
        DataFrame with columns `['Fecha', 'Potencia activa']`, where `Fecha` is
        floored to the start of each hour (`datetime64[ns]`) and `Potencia activa`
        is the sum of the three inverters' hourly mean active power in kW.
    """
    df_inversor = pd.read_csv(inversor)
    reduit = df_inversor[[_FECHA, _INV_1, _INV_2, _INV_3]]

    # Aggregate every 12 five-minute records (1 hour)
    df_mitjana = reduit.groupby(reduit.index // 12).mean(numeric_only=True)

    # Preserve the timestamp of the first record in each 12-row block and floor to hour
    df_mitjana[_FECHA] = reduit[_FECHA].iloc[::12].values
    df_mitjana[_FECHA] = pd.to_datetime(df_mitjana[_FECHA]).dt.floor("h")

    df_mitjana[_POTENCIA_ACTIVA] = (
        df_mitjana[_INV_1] + df_mitjana[_INV_2] + df_mitjana[_INV_3]
    )
    df_mitjana = df_mitjana.drop(columns=[_INV_1, _INV_2, _INV_3])

    return df_mitjana
