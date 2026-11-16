# Datathon 2026 — Repte UPC Sostenible: Campus Battery Optimization

This repository contains our solution and data engineering pipeline for the **UPC Sostenible Challenge ("Carrega la Bateria!")** at **Datathon 2026**.

## Problem Overview

The challenge consists of designing a sequential, real-time control algorithm (`BatteryAgent`) to schedule the hourly charging and discharging power setpoint ($P_t$ in kW) of an industrial lithium-ion battery storage system connected to a university campus microgrid with local solar photovoltaic (PV) generation.

At each hour $t$, the net grid import is:

$$P_{\text{grid}, t} = \max\big(0,\; P_{\text{load}, t} - P_{\text{solar}, t} + P_{\text{battery}, t}\big)$$

The official evaluation metric combines two strategic decarbonization and economic efficiency objectives over 12 hidden test weeks (the last 7 days of each calendar month), penalized by any physical power or State-of-Charge (SoC) constraint violations:

$$\text{Score} = \max\Big(0,\; 0.70 \cdot \Delta\text{CO}_2(\%) + 0.30 \cdot \Delta\text{Cost}(\%) - \text{Penalties}\Big)$$

* **70% Weight — Carbon Footprint Reduction ($\Delta\text{CO}_2$):** Shift grid imports away from hours with high marginal carbon intensity on the Iberian electricity grid.
* **30% Weight — Economic Cost Reduction ($\Delta\text{Cost}$):** Exploit low-price hours in the regulated electricity tariff (PVPC) and surplus solar generation.
* **Hard Mode Setting:** Battery capacity of **6,000 kWh (6 MWh)**, maximum inverter power of **1,500 kW (1.5 MW)**, round-trip efficiency $\eta = 90\%$ ($\eta_c = \eta_d = \sqrt{0.90} \approx 94.87\%$), and a restricted **3-hour lookahead window** for known market prices and $\text{CO}_2$ intensity.

---

## Repository Structure

```text
Datathon26MIUB/
├── agents/                        # Competition battery control agents
|   |-- comparacion_agents.ipynb.  # Comparision of the two following agents
│   ├── agent.py                   # Final submission (Score: 23.43)
│   ├── agent_v1.py                # Previous milestone submission (Score: 23.35)
│   └── README.md                  # Detailed explanation of the 10-stage agent architecture
├── preprocessing/                 # Data cleaning and hourly aggregation pipeline
│   ├── __init__.py                # Package exports
│   ├── procesamiento_contador.py  # 5-min fiscal meter -> hourly campus consumption (kW)
│   ├── procesamiento_meteo.py     # 5-min weather station (alarm-filtered) -> hourly averages
│   ├── inversor.py                # 5-min 3-inverter telemetry -> hourly solar PV generation (kW)
│   ├── juntar.py                  # Merges all hourly sensor & market series into one DataFrame
│   └── README.md                  # Preprocessing pipeline documentation and examples
├── starter_kit/                   # Official simulator, validator, and baseline notebook
│   ├── environment.py             # Sequential simulator (CampusBatteryEnv) and scoring engine
│   ├── check_submission.py        # Official AST security, syntax, and latency verifier
│   ├── battery_spec.json          # Default physical battery parameters
│   ├── agent.py                   # Official rule-based template agent
│   ├── tutorial.ipynb             # Exploratory analysis and baseline modeling notebook
│   ├── model_solar_exemple.pkl    # Example serialized solar regression model
│   └── README.md                  # Official starter kit instructions
├── docs/                          # Official competition documentation
│   ├── ENUNCIAT.md                # Problem statement, physical equations, and rules
│   ├── GUIA_VARIABLES.md          # Sensor telemetry and market variable reference guide
│   └── enunciat_participants_latex.md
├── data/
│   └── train/                     # Training dataset (Sep 2025 – Sep 2026, excluding last 7 days/month)
│       ├── contador.csv           # 5-min campus fiscal meter telemetry
│       ├── contador_horario.csv   # Precomputed hourly campus load
│       ├── inversor.csv           # 5-min telemetry for inverters 1, 2, and 3
│       ├── meteo.csv              # 5-min rooftop weather station measurements
│       ├── meteo_horario.csv      # Precomputed quality-filtered hourly weather
│       ├── entradas_salidas.csv   # 5-min digital relay status signals
│       ├── precio_pvpc.csv        # Hourly PVPC electricity price (EUR/kWh)
│       └── co2_red.csv            # Hourly grid carbon intensity (kg CO2/kWh)
└── README.md                      # Project overview and quickstart guide
```

---

## Solution Highlights ([`agents/agent.py`](agents/agent.py) — Score: 23.43)

Our final agent in [`agents/agent.py`](agents/agent.py) is completely self-contained (zero runtime file reads, zero external dependencies beyond `numpy`, ~4 ms inference latency per step) and combines **multi-model probabilistic forecasting** with **exact continuous-state convex dynamic programming**:

1. **Hybrid Causal Forecasting**:
   - Combines harmonic seasonal/diurnal baselines (`calendar_features`) with empirical monthly/weekday/hourly campus profiles (`HISTORICAL_PROFILES`) and horizon-specific linear causal residual models (`PROFILE_RESIDUAL_COEFFICIENTS`).
   - Includes a dedicated cold-start market regressor (`COLD_MARKET_COEFFICIENTS`) for the first 48 hours, an exponentially-saturating local trend model for $\text{CO}_2$ intensity (`_carbon_forecast`), evaluation-week boundary splicing (`_boundary_tail`), and official Catalonia/Barcelona public holiday and UPC Christmas low-occupancy adjustments (`_low_activity`).
2. **Multi-Family GBDT Quantile Ensemble & Regime Experts**:
   - **Metric-Calibrated Conditional $k$-NN (`CONDITIONAL_FEATURES`)**: Estimates the 21-quantile current-hour net demand error distribution from the 48 nearest historical states in a weighted 6D context space.
   - **Short-Horizon CatBoost Multi-Quantile Forecaster (`NET_MODEL`)**: Predicts 9 conditional quantiles of net demand up to 7 hours ahead over 82 lag, rolling, weather, and market features (`demand_features`).
   - **Focused Daytime CatBoost (`SCORE_CURRENT_MODEL`)**: Refines current-hour daytime net demand scenarios using 100 features including 18 causal contrasts and load-ramp interactions (`focus_expand`).
   - **Night Persistence Expert (`NIGHT_ERROR_QUANTILES`)**: Replaces daytime models between 23:00 and 05:00 with empirical persistence error quantiles.
   - **Three-Family GBDT Ensemble (`ENSEMBLE_MODELS`)**: Blends CatBoost (`cat_demand_predict`), LightGBM (`lgb_predict`), and XGBoost (`xgb_quantile_predict`) quantile forests (weights `0.6 / 0.2 / 0.2`) using pure-NumPy tree evaluators to calibrate multi-step uncertainty (`net_sigma`).
3. **Continuous-State Stochastic Dynamic Programming Controller**:
   - Evaluates the piecewise-linear convex cost-to-go function (`_single_path_future_value`) backward over an 18-hour receding horizon without discretizing battery State of Charge (SoC).
   - Averages the value function across **5 correlated future demand trajectories** (1 central forecast + 4 PCA error-mode perturbations scaled by `CTRL_CORRELATED_SCALE`) and **3 Gaussian quadrature noise points** per hour (`_future_value`).
   - Selects the optimal current-hour charging/discharging power over all value-function breakpoints and **21 current-hour net demand scenarios**, strictly enforcing physical inverter power and SoC bounds (`0` physical infractions).

---

## Quickstart

### 1. Validate the Final Agent Submission

Run the official verification script to check AST security rules, initialization speed, and 24-step inference latency:

```bash
python starter_kit/check_submission.py agents/agent.py
```

### 2. Run the Data Preprocessing Pipeline

To aggregate the 5-minute sensor CSVs (`contador.csv`, `inversor.csv`, `meteo.csv`) into hourly series and merge them with `precio_pvpc.csv` and `co2_red.csv`:

```bash
python preprocessing/juntar.py
```

Or import the preprocessing functions directly in Python:

```python
from preprocessing import (
    juntar_csv,
    media_horaria_contador,
    media_horaria_meteo,
    potencia_solar,
)

df_hourly = juntar_csv(
    co2_red_csv="data/train/co2_red.csv",
    contador_csv="data/train/contador.csv",
    meteo_csv="data/train/meteo.csv",
    precio_pvpc_csv="data/train/precio_pvpc.csv",
    inversor_csv="data/train/inversor.csv",
)
```
