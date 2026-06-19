# Config-Driven SEIR Epidemic Simulation Dashboard with Multi-Run Uncertainty Bands and Scenario Comparison

A config-driven SEIR epidemic simulator featuring stochastic modeling and multi-run uncertainty visualization. Test lockdowns and vaccination campaigns instantly using a high-performance FastAPI backend and React dashboard.

Built for the [2026 CIIT conference](https://ciit.finki.ukim.mk/).

---

## Features

### SEIR Model
- Susceptible → Exposed → Infected → Recovered
- Daily timestep simulation
- Configurable population and disease parameters

### Intervention Scenarios
- Baseline (No interventions)
- Lockdown
- Vaccination
- Lockdown + Vaccination

### Multi-Run Simulation
Run multiple stochastic simulations using different random seeds.

Outputs:
- Mean infected curve
- Low uncertainty band
- High uncertainty band

### Scenario Comparison
Compare two intervention strategies side-by-side.

Examples:
- Vaccination vs Baseline
- Lockdown vs Baseline
- Lockdown + Vaccination vs Lockdown

### Interactive Dashboard
Built with React and Recharts.

Includes:
- Parameter controls
- Scenario presets
- Uncertainty bands
- Export charts as PNG
- Export data as CSV

### FastAPI Backend
REST API endpoints for:
- Single simulation
- Multi-run aggregation
- Scenario comparison

---

## Project Structure

```text
epidemic-sim/
│
├── backend/
│   ├── app.py
│   ├── routes.py
│   ├── simulate/
│   │     └── compare.py
│   ├── engine/
│   │     ├── model.py
│   │     ├── runner.py
│   │     ├── state.py
│   │     └── config.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │     ├── App.jsx
│   │     ├── App.css
│   │     └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── experiments/
├── results/
├── README.md
└── .gitignore
```

---

## Architecture

```text
        React Dashboard
              │
              ▼
         FastAPI Backend
              │
              ▼
        SEIR Simulation Engine
              │
              ▼
      Multi-run Aggregation
              │
              ▼
        Charts and Results
```

---

## Simulation Parameters

| Parameter | Description |
|------------|-------------|
| Population | Total population size |
| Days | Simulation duration |
| Initial Infected | Number of infected people at day 0 |
| Beta | Infection transmission rate |
| Incubation Days | Days before exposed become infectious |
| Infectious Days | Duration of infectious period |
| Mortality Rate | Probability of death |
| Seed | Random seed for reproducibility |

---

## Multi-Run Settings

| Parameter | Description |
|------------|-------------|
| Runs | Number of simulations |
| Band Low (q) | Lower quantile |
| Band High (q) | Upper quantile |

The dashboard displays:

- Mean infected curve
- Low band
- High band

These bands represent uncertainty between multiple stochastic runs.

---

## Scenario Presets

## Baseline
No interventions.

## Lockdown
Reduces disease transmission.

## Vaccination
Moves part of susceptible population to recovered.

## Lockdown + Vaccination
Combines both interventions.

---

## Backend Installation

```bash
cd backend

pip install -r requirements.txt
```

Start FastAPI:

```bash
uvicorn app:app --reload --port 8000
```

Server:

```
http://127.0.0.1:8000
```

Swagger API:

```
http://127.0.0.1:8000/docs
```

---

# Frontend Installation

```bash
cd frontend

npm install
```

Install chart library:

```bash
npm install recharts
```

Run:

```bash
npm run dev
```

Frontend:

```
http://localhost:5173
```

---

## API Endpoints

### Health Check

```http
GET /api/health
```

---

### Single Simulation

```http
POST /api/simulate/run
```

Returns one trajectory.

---

### Multi-Run Simulation

```http
POST /api/simulate/multi
```

Returns:

- Mean infected curve
- Low band
- High band

---

### Scenario Comparison

```http
POST /api/simulate/compare
```

Compares two intervention strategies.

---

## Example Workflow

1. Start backend

```bash
uvicorn app:app --reload --port 8000
```

2. Start frontend

```bash
npm run dev
```

3. Open:

```
http://localhost:5173
```

4. Choose a scenario.

5. Adjust parameters.

6. Run multiple simulations.

7. Analyze uncertainty bands.

8. Compare intervention policies.

---

## Technologies

### Backend
- Python
- FastAPI
- NumPy
- Pandas
- Uvicorn

### Frontend
- React
- Vite
- Recharts
- CSS

---

## Authors

**Konstantin Pandilovski**  
**Ivo Sardzoski Teovski**  
Computer Science Student  
University American College Skopje (UACS)

CIIT 2026 Project

---

## License

MIT License
