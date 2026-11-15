# Data Preprocessing Pipeline (`preprocessing/`)

This package contains the data engineering scripts used to clean, filter, and aggregate the raw 5-minute campus telemetry sensors (`contador.csv`, `inversor.csv`, `meteo.csv`) into hourly time series aligned with the electricity market prices (`precio_pvpc.csv`) and grid carbon intensity (`co2_red.csv`).

## Modules

| Module | Main Function | Description |
| :--- | :--- | :--- |
| [`procesamiento_contador.py`](procesamiento_contador.py) | `media_horaria_contador(csv_entrada, csv_sortida=None)` | Reads `Fecha` and `Contador - POTENCIA ACTIVA EXPORTADA (kW)` from `contador.csv`, computes hourly averages, and applies $\max(0, -P)$ to obtain positive hourly campus load (`Potencia consum`). |
| [`procesamiento_meteo.py`](procesamiento_meteo.py) | `media_horaria_meteo(csv_entrada, csv_sortida=None)` | Reads irradiance, panel temperature, ambient temperature, and wind speed from `meteo.csv`, discarding rows where `ATERSAMET ERROR IRRADIANCIA` or `ATERSAMET ALARMA` is active before computing hourly means. |
| [`inversor.py`](inversor.py) | `potencia_solar(inversor)` | Aggregates the 5-minute active power readings across all 3 solar PV inverters (`Inversor 1..3 - POTENCIA ACTIVA (kW)`) into hourly total solar generation (`Potencia activa`). |
| [`juntar.py`](juntar.py) | `juntar_csv(co2_red_csv, contador_csv, meteo_csv, precio_pvpc_csv, inversor_csv)` | Runs all three sensor aggregations and inner-joins them on `Fecha` with `precio_pvpc.csv` and `co2_red.csv` to produce a single unified hourly training `DataFrame`. |

---

## Usage

### Run the full merging pipeline from the command line

```bash
python preprocessing/juntar.py
```

### Import individual preprocessing functions in Python

```python
from preprocessing import (
    juntar_csv,
    media_horaria_contador,
    media_horaria_meteo,
    potencia_solar,
)

# 1. Generate hourly campus consumption CSV
df_contador = media_horaria_contador(
    "data/train/contador.csv",
    "data/train/contador_horario.csv",
)

# 2. Generate quality-filtered hourly weather CSV
df_meteo = media_horaria_meteo(
    "data/train/meteo.csv",
    "data/train/meteo_horario.csv",
)

# 3. Compute hourly solar PV generation
df_solar = potencia_solar("data/train/inversor.csv")

# 4. Build the complete merged hourly dataset
df_train = juntar_csv(
    co2_red_csv="data/train/co2_red.csv",
    contador_csv="data/train/contador.csv",
    meteo_csv="data/train/meteo.csv",
    precio_pvpc_csv="data/train/precio_pvpc.csv",
    inversor_csv="data/train/inversor.csv",
)
```
