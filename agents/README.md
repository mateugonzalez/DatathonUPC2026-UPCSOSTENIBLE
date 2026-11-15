# Battery Control Agents (`agents/`)

This directory contains our self-contained control agents developed for the **UPC Sostenible Campus Battery Challenge (Datathon 2026)**.

## Files

| File | Test Score | Description |
| :--- | :---: | :--- |
| [`agent.py`](agent.py) | **23.43** | **Final competition submission** (fully typed with Python type annotations and documented in English). Combines causal residual forecasting, public holiday & evaluation-boundary logic, $k$-NN conditional error quantiles, a 3-family GBDT quantile ensemble (CatBoost + LightGBM + XGBoost), a night persistence expert, and a continuous-state convex dynamic programming controller. |
| [`agent_v1.py`](agent_v1.py) | **23.35** | **Previous milestone submission** prior to the GBDT quantile ensemble, night persistence expert, and Pareto controller stages. Preserved for ablation and version history comparison. |

---

## Architecture of `agent.py` (Score: 23.43)

During evaluation, `BatteryAgent.act(obs)` operates strictly sequentially with **zero file I/O** and **zero external dependencies beyond `numpy`**. All offline-trained parameters, lookup tables, and gradient-boosted decision trees are embedded directly as NumPy arrays.

The agent is structured as a 10-stage inheritance pipeline where each stage refines either the multi-horizon causal forecast, the uncertainty distribution, or the receding-horizon control policy:

1. **Base Causal Forecaster & Convex DP Planner (`_OriginalSubmittedAgent`)**:
   - Combines harmonic calendar features (`calendar_features`) with empirical monthly/weekday/hourly campus profiles (`HISTORICAL_PROFILES`) and horizon-specific linear causal residual models (`PROFILE_RESIDUAL_COEFFICIENTS`).
   - Uses a dedicated cold-start market regressor (`COLD_MARKET_COEFFICIENTS`) during the first 48 hours and a local saturating linear trend correction for grid $\text{CO}_2$ intensity (`_carbon_forecast`).
   - Applies three sequential harmonic bias calibrations across lead times and adapts PCA error-mode scaling based on recent standardized prediction errors.
   - Solves the multi-stage stochastic control problem via exact **continuous-state piecewise-linear convex dynamic programming** (`_single_path_future_value`) across 5 correlated future demand trajectories (1 central + 4 PCA error modes) and 3 per-hour Gaussian quadrature noise points, selecting the immediate action over 21 current-hour net demand error quantiles (`_choose_action`).
2. **Evaluation-Week Boundary Handler (`_BeforeHolidayAgent`)**:
   - Detects the end of each published 7-day monthly evaluation window (`_boundary_tail`) and splices the baseline profile of the next evaluation week's start while keeping battery SoC and causal memory continuous.
3. **Public Holiday & Low-Occupancy Calendar (`_BeforeConditionalErrors`)**:
   - Blends weekday consumption baselines toward weekend profiles (`_low_activity`) on official Catalonia and Barcelona public holidays (2025–2026) and during the UPC Christmas low-occupancy closure (Dec 25 – Jan 6).
4. **Metric-Calibrated Conditional $k$-NN Error Distribution (`_BeforeMetricCalibration` & `_PreviousCandidateAgent`)**:
   - Replaces static current-hour error quantiles with a feature-weighted $k$-nearest-neighbor empirical error distribution (`CONDITIONAL_FEATURES`, `CONDITIONAL_ERRORS`) conditioned on net demand level, diurnal phase, solar generation, recent load ramps, and weekend/holiday regime.
5. **Horizon & Noise Calibration (`_BeforeDemandModel`)**:
   - Configures an 18-hour receding planning horizon (`HORIZON = 18`) and a `0.9` terminal energy valuation factor (`TERMINAL_FACTOR = 0.9`).
6. **Short-Horizon CatBoost Multi-Quantile Demand Model (`_BeforeNightExpert`)**:
   - Predicts 9 conditional quantiles of net demand up to 7 hours ahead (`NET_MODEL`) over 82 causal lag/rolling/market features (`demand_features`) using a pure-NumPy oblivious-tree evaluator (`cat_demand_predict`) to calibrate horizon-specific uncertainty (`net_sigma`).
7. **Night Persistence Expert (`_BeforeParetoControl`)**:
   - Overrides current-hour scenario distributions and future uncertainty during night hours (23:00–05:00) using empirical persistence error quantiles (`NIGHT_ERROR_QUANTILES`).
8. **Pareto-Gated Receding-Horizon Controller (`_BeforeScoreCurrent`)**:
   - Supports separate price vs. carbon value-function evaluation, cycle penalties, and correlated PCA scenario scaling (`CTRL_CORRELATED_SCALE = 0.5`).
9. **Focused Daytime Current-Demand CatBoost (`_BeforeGBDTEnsemble`)**:
   - Refines current-hour daytime net demand quantiles using a specialized 100-feature CatBoost model (`SCORE_CURRENT_MODEL`) over expanded causal contrast and ramp features (`focus_expand`).
10. **Three-Family GBDT Quantile Ensemble (`BatteryAgent`)**:
    - Combines CatBoost (`cat_demand_predict`), LightGBM (`lgb_predict`), and XGBoost (`xgb_quantile_predict`) quantile forecasts (`ENSEMBLE_MODELS`) with weights `[0.6, 0.2, 0.2]` to refine future uncertainty (`net_sigma`) feeding the convex DP planner.

---

## Local Validation

Run the official submission verifier from the repository root:

```bash
python starter_kit/check_submission.py agents/agent.py
```
