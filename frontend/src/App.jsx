import React, { useMemo, useRef, useState } from "react"
import "./App.css"
import { toPng } from "html-to-image"
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts"

const API_BASE = "http://127.0.0.1:8000/api"

function num(v, fallback) {
  const n = Number(v)
  return Number.isFinite(n) ? n : fallback
}

const PRESETS = {
  baseline: {
    name: "Baseline (No interventions)",
    overrides: { interventions: [] },
  },
  lockdown: {
    name: "Lockdown",
    overrides: {
      interventions: [{ type: "lockdown", start_day: 20, end_day: 70, beta_multiplier: 0.55 }],
    },
  },
  vaccination: {
    name: "Vaccination",
    overrides: {
      interventions: [{ type: "vaccination", start_day: 20, daily_rate: 0.004 }],
    },
  },
  lockdown_vaccination: {
    name: "Lockdown + Vaccination",
    overrides: {
      interventions: [
        { type: "lockdown", start_day: 20, end_day: 70, beta_multiplier: 0.55 },
        { type: "vaccination", start_day: 20, daily_rate: 0.004 },
      ],
    },
  },
}

function pickConfig(base, overrides) {
  const o = overrides && typeof overrides === "object" ? overrides : {}
  const safeInterventions = Array.isArray(o.interventions) ? o.interventions : base.interventions

  return {
    ...base,
    population: num(o.population, base.population),
    days: num(o.days, base.days),
    initial_infected: num(o.initial_infected, base.initial_infected),
    beta: num(o.beta, base.beta),
    incubation_days: num(o.incubation_days, base.incubation_days),
    infectious_days: num(o.infectious_days, base.infectious_days),
    mortality_rate: num(o.mortality_rate, base.mortality_rate),
    seed: num(o.seed, base.seed),
    interventions: safeInterventions,
  }
}

async function postJSON(url, payload) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
  const txt = await res.text()
  let data = null
  try {
    data = txt ? JSON.parse(txt) : null
  } catch {
    data = { raw: txt }
  }
  if (!res.ok) {
    const msg = data?.detail || data?.message || `HTTP ${res.status}`
    throw new Error(msg)
  }
  return data
}

function buildXY(series) {
  const days = Array.isArray(series?.days) ? series.days : []
  const I_mean = Array.isArray(series?.I_mean) ? series.I_mean : []
  const I_low = Array.isArray(series?.I_low) ? series.I_low : []
  const I_high = Array.isArray(series?.I_high) ? series.I_high : []

  const len = Math.max(days.length, I_mean.length)
  const out = []
  for (let i = 0; i < len; i++) {
    out.push({
      day: days[i] ?? i,
      I_mean: I_mean[i] ?? null,
      I_low: I_low[i] ?? null,
      I_high: I_high[i] ?? null,
    })
  }
  return out
}

function downloadBlob(filename, blob) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

function toCSV(rows) {
  if (!Array.isArray(rows) || rows.length === 0) return ""
  const cols = Array.from(
    rows.reduce((set, r) => {
      Object.keys(r || {}).forEach((k) => set.add(k))
      return set
    }, new Set())
  )
  const esc = (v) => {
    if (v === null || v === undefined) return ""
    const s = String(v)
    if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`
    return s
  }
  const header = cols.join(",")
  const body = rows.map((r) => cols.map((c) => esc(r?.[c])).join(",")).join("\n")
  return `${header}\n${body}\n`
}

export default function App() {
  const [baseConfig, setBaseConfig] = useState({
    population: 10000,
    days: 120,
    initial_infected: 10,
    beta: 0.35,
    incubation_days: 3,
    infectious_days: 7,
    mortality_rate: 0.01,
    seed: 42,
    interventions: [],
  })

  const [runs, setRuns] = useState(30)
  const [bandLow, setBandLow] = useState(0.1)
  const [bandHigh, setBandHigh] = useState(0.9)

  const [presetKey, setPresetKey] = useState("baseline")
  const [scenarioA, setScenarioA] = useState("baseline")
  const [scenarioB, setScenarioB] = useState("lockdown")

  const effectiveConfig = useMemo(() => {
    return pickConfig(baseConfig, PRESETS[presetKey]?.overrides || {})
  }, [baseConfig, presetKey])

  const [multiChart, setMultiChart] = useState(null)
  const [compareChart, setCompareChart] = useState(null)

  const [status, setStatus] = useState("")
  const [error, setError] = useState("")

  const [loadingMulti, setLoadingMulti] = useState(false)
  const [loadingCompare, setLoadingCompare] = useState(false)

  const [hiddenMulti, setHiddenMulti] = useState({
    I_mean: false,
    I_low: false,
    I_high: false,
  })

  const [hiddenCompare, setHiddenCompare] = useState({
    A_mean: false,
    B_mean: false,
  })

  const multiWrapRef = useRef(null)
  const compareWrapRef = useRef(null)

  async function exportPNG(which) {
    const node = which === "multi" ? multiWrapRef.current : compareWrapRef.current
    if (!node) return
    try {
      const dataUrl = await toPng(node, { cacheBust: true, pixelRatio: 2 })
      const a = document.createElement("a")
      a.href = dataUrl
      a.download = which === "multi" ? "infected_band.png" : "scenario_compare.png"
      a.click()
    } catch (e) {
      setError(String(e.message || e))
    }
  }

  function exportCSV(which) {
    const rows = which === "multi" ? multiChart : compareChart
    if (!Array.isArray(rows) || rows.length === 0) return
    const csv = toCSV(rows)
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" })
    downloadBlob(which === "multi" ? "infected_band.csv" : "scenario_compare.csv", blob)
  }

  async function runMulti() {
    setError("")
    setStatus("Running multi simulation...")
    setMultiChart(null)
    setLoadingMulti(true)

    try {
      const payload = {
        config: effectiveConfig,
        runs: num(runs, 30),
        band_low: num(bandLow, 0.1),
        band_high: num(bandHigh, 0.9),
      }

      const raw = await postJSON(`${API_BASE}/simulate/multi`, payload)

      const xy = buildXY(raw)
      if (!xy.length) {
        console.log("MULTI RAW RESPONSE:", raw)
        throw new Error("Backend returned empty series for /simulate/multi.")
      }

      setMultiChart(xy)
      setStatus("Loaded multi-run band.")
    } catch (e) {
      setStatus("")
      setError(String(e.message || e))
    } finally {
      setLoadingMulti(false)
    }
  }

  async function runCompare() {
    setError("")
    setStatus("Running scenario comparison...")
    setCompareChart(null)
    setLoadingCompare(true)

    try {
      const cfgA = pickConfig(baseConfig, PRESETS[scenarioA]?.overrides || {})
      const cfgB = pickConfig(baseConfig, PRESETS[scenarioB]?.overrides || {})

      const payload = {
        config_a: cfgA,
        config_b: cfgB,
        runs: num(runs, 30),
        band_low: num(bandLow, 0.1),
        band_high: num(bandHigh, 0.9),
      }

      const raw = await postJSON(`${API_BASE}/simulate/compare`, payload)

      const a = raw?.a
      const b = raw?.b

      const aXY = a ? buildXY(a) : []
      const bXY = b ? buildXY(b) : []

      if (!aXY.length || !bXY.length) {
        console.log("COMPARE RAW RESPONSE:", raw)
        throw new Error("Compare returned empty series.")
      }

      const len = Math.max(aXY.length, bXY.length)
      const merged = []
      for (let i = 0; i < len; i++) {
        merged.push({
          day: aXY[i]?.day ?? bXY[i]?.day ?? i,
          A_mean: aXY[i]?.I_mean ?? null,
          B_mean: bXY[i]?.I_mean ?? null,
        })
      }

      setCompareChart(merged)
      setStatus("Loaded scenario comparison.")
    } catch (e) {
      setStatus("")
      setError(String(e.message || e))
    } finally {
      setLoadingCompare(false)
    }
  }

  return (
    <div className="page">
      <div className="shell">
        <header className="topbar">
          <h1>Epidemic Simulation Dashboard</h1>
          <p>SEIR model • Multi-run uncertainty • Scenario compare</p>
        </header>

        <div className="layout">
          <aside className="panel">
            <section className="card">
              <h3>Scenario Presets</h3>
              <div className="grid2">
                {Object.entries(PRESETS).map(([k, v]) => (
                  <button
                    key={k}
                    className={`chip ${presetKey === k ? "active" : ""}`}
                    onClick={() => setPresetKey(k)}
                    type="button"
                  >
                    {v.name}
                  </button>
                ))}
              </div>
            </section>

            <section className="card">
              <h3>Simulation Parameters</h3>

              <div className="formGrid">
                <label>
                  <span>Population</span>
                  <input value={baseConfig.population} onChange={(e) => setBaseConfig((s) => ({ ...s, population: e.target.value }))} />
                </label>

                <label>
                  <span>Days</span>
                  <input value={baseConfig.days} onChange={(e) => setBaseConfig((s) => ({ ...s, days: e.target.value }))} />
                </label>

                <label>
                  <span>Initial Infected</span>
                  <input value={baseConfig.initial_infected} onChange={(e) => setBaseConfig((s) => ({ ...s, initial_infected: e.target.value }))} />
                </label>

                <label>
                  <span>Beta</span>
                  <input value={baseConfig.beta} onChange={(e) => setBaseConfig((s) => ({ ...s, beta: e.target.value }))} />
                </label>

                <label>
                  <span>Incubation Days</span>
                  <input value={baseConfig.incubation_days} onChange={(e) => setBaseConfig((s) => ({ ...s, incubation_days: e.target.value }))} />
                </label>

                <label>
                  <span>Infectious Days</span>
                  <input value={baseConfig.infectious_days} onChange={(e) => setBaseConfig((s) => ({ ...s, infectious_days: e.target.value }))} />
                </label>

                <label>
                  <span>Mortality Rate</span>
                  <input value={baseConfig.mortality_rate} onChange={(e) => setBaseConfig((s) => ({ ...s, mortality_rate: e.target.value }))} />
                </label>

                <label>
                  <span>Seed</span>
                  <input value={baseConfig.seed} onChange={(e) => setBaseConfig((s) => ({ ...s, seed: e.target.value }))} />
                </label>
              </div>
            </section>

            <section className="card">
              <h3>Multi-run Settings</h3>

              <div className="formGrid">
                <label>
                  <span>Runs</span>
                  <input value={runs} onChange={(e) => setRuns(e.target.value)} />
                </label>

                <label>
                  <span>Band Low (q)</span>
                  <input value={bandLow} onChange={(e) => setBandLow(e.target.value)} />
                </label>

                <label>
                  <span>Band High (q)</span>
                  <input value={bandHigh} onChange={(e) => setBandHigh(e.target.value)} />
                </label>
              </div>

              <button className="primary" onClick={runMulti} type="button">
                Run Multi Simulation
              </button>
            </section>

            <section className="card">
              <h3>Compare Scenarios</h3>

              <div className="compareRow">
                <label>
                  <span>Scenario A</span>
                  <select value={scenarioA} onChange={(e) => setScenarioA(e.target.value)}>
                    {Object.entries(PRESETS).map(([k, v]) => (
                      <option key={k} value={k}>
                        {v.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  <span>Scenario B</span>
                  <select value={scenarioB} onChange={(e) => setScenarioB(e.target.value)}>
                    {Object.entries(PRESETS).map(([k, v]) => (
                      <option key={k} value={k}>
                        {v.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <button className="primary" onClick={runCompare} type="button">
                Run Compare
              </button>

              {status ? <div className="note">{status}</div> : null}
              {error ? <div className="error">{error}</div> : null}
            </section>
          </aside>

          <main className="charts">
            <div className="chartCard">
              <div className="chartHeaderRow">
                <h3>Infected (Mean + Band)</h3>

                <div className="chartActions">
                  <button className="ghostBtn" type="button" onClick={() => exportCSV("multi")} disabled={!multiChart || loadingMulti}>
                    Export CSV
                  </button>
                  <button className="ghostBtn" type="button" onClick={() => exportPNG("multi")} disabled={loadingMulti}>
                    Export PNG
                  </button>
                </div>
              </div>

              <div className="chartBoxWrap" ref={multiWrapRef}>
                <div className="chartBox">
                  {multiChart ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={multiChart}>
                        <CartesianGrid stroke="rgba(120,180,255,0.22)" strokeDasharray="4 6" />
                        <XAxis dataKey="day" stroke="rgba(234,241,255,0.55)" tick={{ fill: "rgba(234,241,255,0.7)" }} />
                        <YAxis stroke="rgba(234,241,255,0.55)" tick={{ fill: "rgba(234,241,255,0.7)" }} />
                        <Tooltip
                          contentStyle={{
                            background: "rgba(10,16,32,0.92)",
                            border: "1px solid rgba(255,255,255,0.10)",
                            borderRadius: 12,
                          }}
                        />

                        <Legend
                          formatter={(value) => {
                            if (value === "I_mean") return "Mean infected"
                            if (value === "I_low") return "Low band"
                            if (value === "I_high") return "High band"
                            return value
                          }}
                          onClick={(e) => {
                            const key = e?.dataKey
                            if (!key) return
                            setHiddenMulti((s) => ({ ...s, [key]: !s[key] }))
                          }}
                        />

                        <Line type="monotone" dataKey="I_high" dot={false} hide={hiddenMulti.I_high} stroke="rgba(120,210,255,0.75)" strokeWidth={1.5} />
                        <Line type="monotone" dataKey="I_low" dot={false} hide={hiddenMulti.I_low} stroke="rgba(120,210,255,0.45)" strokeWidth={1.5} />
                        <Line type="monotone" dataKey="I_mean" dot={false} hide={hiddenMulti.I_mean} stroke="rgba(170,120,255,0.95)" strokeWidth={3} />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="placeholder">Click “Run Multi Simulation” to load data.</div>
                  )}
                </div>

                {loadingMulti ? (
                  <div className="chartLoading">
                    <div className="shimmer" />
                    <div className="loadingText">Running…</div>
                  </div>
                ) : null}
              </div>
            </div>

            <div className="chartCard">
              <div className="chartHeaderRow">
                <h3>Scenario Comparison (A vs B)</h3>

                <div className="chartActions">
                  <button className="ghostBtn" type="button" onClick={() => exportCSV("compare")} disabled={!compareChart || loadingCompare}>
                    Export CSV
                  </button>
                  <button className="ghostBtn" type="button" onClick={() => exportPNG("compare")} disabled={loadingCompare}>
                    Export PNG
                  </button>
                </div>
              </div>

              <div className="chartBoxWrap" ref={compareWrapRef}>
                <div className="chartBox">
                  {compareChart ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={compareChart}>
                        <CartesianGrid stroke="rgba(120,180,255,0.22)" strokeDasharray="4 6" />
                        <XAxis dataKey="day" stroke="rgba(234,241,255,0.55)" tick={{ fill: "rgba(234,241,255,0.7)" }} />
                        <YAxis stroke="rgba(234,241,255,0.55)" tick={{ fill: "rgba(234,241,255,0.7)" }} />
                        <Tooltip
                          contentStyle={{
                            background: "rgba(10,16,32,0.92)",
                            border: "1px solid rgba(255,255,255,0.10)",
                            borderRadius: 12,
                          }}
                        />

                        <Legend
                          formatter={(value) => {
                            if (value === "A_mean") return "Scenario A"
                            if (value === "B_mean") return "Scenario B"
                            return value
                          }}
                          onClick={(e) => {
                            const key = e?.dataKey
                            if (!key) return
                            setHiddenCompare((s) => ({ ...s, [key]: !s[key] }))
                          }}
                        />

                        <Line type="monotone" dataKey="A_mean" dot={false} hide={hiddenCompare.A_mean} stroke="rgba(170,120,255,0.95)" strokeWidth={3} />
                        <Line type="monotone" dataKey="B_mean" dot={false} hide={hiddenCompare.B_mean} stroke="rgba(120,210,255,0.85)" strokeWidth={3} />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="placeholder">Click “Run Compare” to load data.</div>
                  )}
                </div>

                {loadingCompare ? (
                  <div className="chartLoading">
                    <div className="shimmer" />
                    <div className="loadingText">Running…</div>
                  </div>
                ) : null}
              </div>
            </div>
          </main>
        </div>

        <footer className="footer">
          <span>API: {API_BASE}</span>
        </footer>
      </div>
    </div>
  )
}
