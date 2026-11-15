"""Pipeline to merge hourly solar PV, campus load, weather, PVPC price, and grid CO2 series."""
from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import inversor  # type: ignore[import-not-found]
    import procesamiento_contador  # type: ignore[import-not-found]
    import procesamiento_meteo  # type: ignore[import-not-found]
else:
    from . import inversor, procesamiento_contador, procesamiento_meteo


def juntar_csv(
    co2_red_csv: str | Path,
    contador_csv: str | Path,
    meteo_csv: str | Path,
    precio_pvpc_csv: str | Path,
    inversor_csv: str | Path,
) -> pd.DataFrame:
    """Aggregate 5-minute sensor CSVs to hourly resolution and merge with market series.

    Parameters
    ----------
    co2_red_csv : str | Path
        Path to hourly grid carbon intensity CSV (`co2_red.csv`).
    contador_csv : str | Path
        Path to 5-minute fiscal meter CSV (`contador.csv`).
    meteo_csv : str | Path
        Path to 5-minute weather station CSV (`meteo.csv`).
    precio_pvpc_csv : str | Path
        Path to hourly regulated electricity price CSV (`precio_pvpc.csv`).
    inversor_csv : str | Path
        Path to 5-minute solar inverter telemetry CSV (`inversor.csv`).

    Returns
    -------
    pd.DataFrame
        Inner-joined hourly DataFrame aligned on `Fecha`.
    """
    potencia_foto = inversor.potencia_solar(inversor_csv)
    contador_resumit = procesamiento_contador.media_horaria_contador(contador_csv)
    meteo_resumit = procesamiento_meteo.media_horaria_meteo(meteo_csv)

    co2_red = pd.read_csv(co2_red_csv)
    co2_red["Fecha"] = pd.to_datetime(co2_red["Fecha"])

    precio_pvpc = pd.read_csv(precio_pvpc_csv)[["Fecha", "precio_eur_per_kwh"]]
    precio_pvpc["Fecha"] = pd.to_datetime(precio_pvpc["Fecha"])

    df_final = pd.merge(potencia_foto, contador_resumit, on="Fecha", how="inner")
    df_final = pd.merge(df_final, meteo_resumit, on="Fecha", how="inner")
    df_final = pd.merge(df_final, precio_pvpc, on="Fecha", how="inner")
    df_final = pd.merge(df_final, co2_red, on="Fecha", how="inner")

    return df_final


if __name__ == "__main__":
    data_dir = Path(__file__).resolve().parent.parent / "data" / "train"
    df_merged = juntar_csv(
        co2_red_csv=data_dir / "co2_red.csv",
        contador_csv=data_dir / "contador.csv",
        meteo_csv=data_dir / "meteo.csv",
        precio_pvpc_csv=data_dir / "precio_pvpc.csv",
        inversor_csv=data_dir / "inversor.csv",
    )
    print(df_merged.head())
