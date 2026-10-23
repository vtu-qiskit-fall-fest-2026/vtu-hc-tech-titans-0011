# QuantumGreen – AI-Powered Smart Energy Optimization for a Sustainable Future

[![Hackathon Domain: Quantum Applications for Climate Change & Sustainability](https://img.shields.io/badge/Domain-Quantum_Applications_for_Climate_Change-10B981.svg)](#)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3B82F6.svg)](#)
[![Framework: Flask](https://img.shields.io/badge/Framework-Flask_3.1-06B6D4.svg)](#)
[![Quantum: Qiskit 2.6](https://img.shields.io/badge/Quantum-Qiskit_2.6-8B5CF6.svg)](#)
[![AI/ML: Scikit--Learn](https://img.shields.io/badge/ML-Scikit--Learn_1.9-F59E0B.svg)](#)

> **Tagline:** *“Smarter Energy, Greener Tomorrow.”*

**QuantumGreen** is a modern, responsive, and end-to-end interactive energy optimization platform designed for colleges, hostels, research laboratories, and public office complexes. It monitors electricity consumption, predicts future energy demand using machine learning, recommends actionable energy-saving measures, estimates carbon footprints, optimizes equipment operating schedules using classical algorithms, and demonstrates how quantum optimization (QAOA with Qiskit) can tackle future grid combinatorial dispatch.

---

## 🌟 Key Features & Website Modules

### 1. Home Portal
- Interactive welcoming dashboard with quick CTAs: **Explore Dashboard**, **Analyze Energy**, **Run AI Prediction**, and **Learn About Quantum**.
- Pre-loaded with **4 verified facility presets**:
  1. *Greenwood Engineering College* (Academic blocks, computer labs, libraries, CNC workshops, borewell pumps).
  2. *TechHub Student Hostels & Mess* (Water geysers, laundromat machines, induction kitchen, corridor lighting).
  3. *BioSci Advanced Research Labs* (Cleanroom HVAC, ultra-low -80°C freezers, autoclaves, centrifuges).
  4. *Metro Central Public Office Complex* (Central chiller plants, high-rise elevator banks, server UPS).

### 2. Energy Dashboard
- Total electricity consumption (kWh) across peak and off-peak hours.
- Time-of-Use (ToU) electricity cost accounting.
- Scope 2 carbon emissions estimation (kg CO₂e) with configurable grid emission factors.
- **Environmental Impact Equivalencies**: Mature trees needed for 1-year sequestration, passenger vehicle kilometers avoided, and smartphone charges equivalent.
- Interactive Chart.js visualizations:
  - 24-hour diurnal consumption curve (Baseline vs Potential Optimized).
  - 30-day historical consumption trend.
  - Equipment category energy share donut chart.

### 3. Energy Data Input & Setup
- Facility profile configuration: Base tariff, Peak tariff, Peak time window (e.g., 18:00 - 22:00), Emission factor slider with international grid presets (India 0.82, Global 0.48, US 0.39, Renewables 0.18).
- **Interactive Equipment Inventory Manager**: Add, edit, review, and delete appliances with power ratings (Watts), operating hours, priority levels (Critical, Medium, Flexible), and preferred run windows.
- **CSV Smart Meter Log Ingestion**: Upload custom hourly energy data with schema validation and sample CSV template downloads.
- Stored persistently in a local SQLite database (`quantumgreen.db`).

### 4. AI-Based Energy Prediction
- Real **Scikit-Learn Machine Learning Pipeline** (Random Forest Regressor with 100 estimators).
- Engineered features: Cyclical hour sine/cosine, cyclical day-of-week, temperature proxy, autoregressive lag features (lag-1, lag-24), and rolling 24-hour moving averages.
- Evaluates real metrics: $R^2$ Score (>0.95), Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), and Forecast Accuracy %.
- Visualizes:
  - Hold-out test set **Actual vs Predicted** validation curve.
  - Next 24-hour forward demand forecast with shaded **90% confidence bands**.
  - 7-day daily forecast table with automatic **Peak Demand Risk Alerts**.

### 5. Smart Energy Recommendations
- Heuristic and tariff-driven recommendation engine:
  - Shifting flexible high-draw appliances to off-peak valley hours.
  - Intelligent HVAC thermostat setpoint optimization (21°C to 24°C).
  - Automated smart contactor cutoff for phantom/standby loads (23:00 - 06:00).
  - Microwave occupancy sensor retrofits for transit corridors and restrooms.
  - Rooftop solar generation self-consumption alignment.
- Each recommendation quantifies: Monthly financial savings, kWh saved, CO₂ reduction, priority badge, and explicit mathematical assumptions.

### 6. Smart Energy Optimization (Classical Scheduler)
- Formulates a 24-hour constrained load-shifting and peak-shaving problem.
- Prioritizes critical appliances while moving flexible high-power loads to low-cost hours without exceeding grid transformer peak limits.
- Outputs:
  - Peak demand shaved ($kW$ and % shaved).
  - Electricity cost and carbon emissions before vs after optimization.
  - 24-hour stacked power load curve comparison.
  - Appliance-by-appliance schedule breakdown with `SHIFTED` status tags.

### 7. Quantum Optimization Lab (Qiskit QAOA)
- Real **Qiskit 2.6 Quantum Simulation** demonstrating quantum optimization on energy scheduling.
- **Mathematical Mapping**: Translates combinatorial load dispatch into a Quadratic Unconstrained Binary Optimization (QUBO) / Ising Spin Glass Hamiltonian:
  $$\hat{H}_C = \sum_i h_i \hat{Z}_i + \sum_{i < j} J_{ij} \hat{Z}_i \hat{Z}_j$$
- Compiles a parameterized **Quantum Approximate Optimization Algorithm (QAOA)** circuit with Cost and Mixer unitaries ($p=1$ or $p=2$ layers).
- Uses classical COBYLA variational optimization over statevectors to maximize measurement probability for the optimal ground state.
- **Benchmark Comparison**: Compares the Quantum solution side-by-side with Classical Exact Exhaustive Search and Classical Greedy heuristics (Energy cost, runtime in ms, optimality gap).
- **Educational Commentary**: Explains the difference between a classical statevector simulator and physical NISQ quantum hardware (decoherence, gate infidelity, error mitigation).

### 8. Results & Official Reports
- Executive summary with key performance indicators.
- **One-Click CSV Export**: Complete hourly schedule and appliance allocation.
- **One-Click PDF Report Generation**: Professional PDF audit generated on-the-fly using Python's `reportlab` library.

### 9. Educational Section ("About Quantum Sustainability")
- Explains quantum principles (superposition, entanglement, qubits vs classical bits) in accessible language.
- AI/ML vs Quantum Optimization comparison matrix.
- Interactive FAQ addressing peaker plants, climate impact, and quantum advantage.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.10+, Flask 3.1, SQLite3 |
| **Machine Learning** | Scikit-Learn (Random Forest Regressor), NumPy, Pandas |
| **Classical Optimization** | SciPy, Constrained Greedy Load-Shifter |
| **Quantum Simulation** | Qiskit 2.6 (`qiskit.circuit.library.QAOAAnsatz`, `SparsePauliOp`, `Statevector`) |
| **Report Generation** | ReportLab 5.1 (PDF Generation), Python CSV engine |
| **Frontend UI** | HTML5, Modern CSS (Glassmorphism, Dark Blue & Emerald Green theme), Bootstrap 5.3, Bootstrap Icons |
| **Data Visualization** | Chart.js 4.4, Canvas Confetti |

---

## 🚀 Quick Setup & Running Locally

### 1. Prerequisites
Ensure Python 3.10 or higher is installed on your system.

### 2. Install Dependencies
Clone or open the project folder in your terminal and run:
```bash
pip install -r requirements.txt
```

### 3. Run the QuantumGreen Server
```bash
python app.py
```

### 4. Open in Your Browser
Visit:
```
http://127.0.0.1:5000
```
The application will automatically initialize the SQLite database with realistic sample datasets so you can immediately explore and demonstrate all features.

---

## 📡 REST API Endpoints

- `GET /` — Main single-page application.
- `GET /api/buildings` — List all facility profiles.
- `POST /api/buildings` — Create a new facility profile.
- `PUT /api/building/<id>` — Update tariffs and emissions factors.
- `GET /api/summary/<id>` — Aggregate metrics, diurnal charts, and recommendations.
- `GET /api/equipment/<id>` — List equipment inventory.
- `POST /api/equipment` — Add new equipment item.
- `DELETE /api/equipment/<id>` — Delete equipment item.
- `POST /api/upload-csv/<id>` — Ingest and validate hourly CSV energy logs.
- `GET /api/sample-csv` — Download sample CSV format.
- `GET /api/predict/<id>` — Train and evaluate Scikit-Learn AI demand forecast.
- `GET /api/recommendations/<id>` — Generate actionable energy-saving recommendations.
- `GET /api/optimize/<id>` — Run classical 24-hour constrained load-shifting scheduler.
- `POST /api/quantum-run` — Run Qiskit QAOA simulation with configurable qubits and layers.
- `GET /api/report/csv/<id>` — Download comprehensive CSV energy audit report.
- `GET /api/report/pdf/<id>` — Download official PDF audit document.

---

## 🌿 Environmental Impact Methodology

1. **Carbon Accounting**:
   $$\text{Emissions } (\text{kg CO}_2\text{e}) = \text{Consumption } (\text{kWh}) \times \text{Emission Factor } (\text{kg CO}_2\text{e/kWh})$$
2. **Peaker Plant Avoidance**:
   Marginal grid emission factor during peak hours (18:00 - 22:00) is modeled at ~0.95 kg CO₂e/kWh due to inefficient thermal peaker plants. Off-peak energy draws cleaner base-load power (~0.76 kg CO₂e/kWh).
3. **Tree Sequestration Equivalent**:
   One mature urban tree absorbs approximately 21.77 kg of CO₂ per year (IPCC standard).
   $$\text{Trees Equivalent} = \frac{\text{Annual Carbon Saved (kg)}}{21.77}$$

---

## 🏆 Hackathon Presentation Highlights
- **Live Interactive Demo**: Switch seamlessly between colleges, hostels, research labs, and office complexes.
- **Genuine AI & Quantum Implementation**: Real Scikit-learn regressors ($R^2 > 0.95$) and real Qiskit QAOA quantum circuits (no fake hardcoded numbers).
- **Professional PDF/CSV Export**: Ready to present to institutional facility managers and hackathon judges.
