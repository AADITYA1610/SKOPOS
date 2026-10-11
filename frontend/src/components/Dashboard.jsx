import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import html2canvas from "html2canvas";
import ChartBuilder from "../components/ChartBuilder";
import { jsPDF } from "jspdf";
import { useAnalysis } from "../context/AnalysisContext";
import { api } from "../api/client";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

const DASH_PREFS_KEY = "tadaa_dashboard_prefs_v1";

const chartTheme = {
  grid: "rgba(148, 163, 184, 0.15)",
  axis: "#94a3b8",
  tooltipBg: "rgba(15, 23, 42, 0.95)",
  tooltipBorder: "rgba(56, 189, 248, 0.25)",
};

function formatKpiValue(k) {
  const v = Number(k.value);
  if (k.format === "pct") return `${v.toFixed(1)}%`;
  if (k.format === "int") return String(Math.round(v));
  if (Number.isNaN(v)) return "—";
  return v.toLocaleString(undefined, { maximumFractionDigits: 4 });
}

/* ✅ Improved diverging correlation color scale
   - Strong positive = blue
   - Strong negative = red
   - Near zero = dark gray
   - Diagonal = bright blue
*/
function corrCellColor(v) {
  const value = Number(v);

  if (Number.isNaN(value)) {
    return "rgba(51, 65, 85, 0.45)";
  }

  const x = Math.max(-1, Math.min(1, value));

  if (x >= 0.995) {
    return "rgba(14, 165, 233, 0.98)";
  }

  if (x <= -0.995) {
    return "rgba(239, 68, 68, 0.98)";
  }

  const intensity = Math.pow(Math.abs(x), 0.55);

  if (x > 0) {
    return `rgba(56, 189, 248, ${0.18 + intensity * 0.82})`;
  }

  if (x < 0) {
    return `rgba(248, 113, 113, ${0.18 + intensity * 0.82})`;
  }

  return "rgba(71, 85, 105, 0.35)";
}

function corrTextColor(v) {
  const value = Math.abs(Number(v));
  return value >= 0.55 ? "#f8fafc" : "#cbd5e1";
}

function HeatmapPanel({ labels, matrix }) {
  const [tip, setTip] = useState(null);

  if (!labels?.length || !matrix?.length) return null;

  return (
    <div className="heatmap-wrap">
      {tip && (
        <div className="heatmap-tooltip" role="status">
          {tip.row} × {tip.col}: <strong>{tip.v.toFixed(3)}</strong>
        </div>
      )}

      <div className="heatmap-legend" aria-label="Correlation color legend">
        <span className="heatmap-legend__label">-1</span>
        <span className="heatmap-legend__bar" />
        <span className="heatmap-legend__label">0</span>
        <span className="heatmap-legend__bar heatmap-legend__bar--positive" />
        <span className="heatmap-legend__label">+1</span>
      </div>

      <div className="heatmap-scroll">
        <table className="heatmap-table">
          <thead>
            <tr>
              <th className="heatmap-corner" />
              {labels.map((lb) => (
                <th key={lb} className="heatmap-th" title={lb}>
                  {lb}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {labels.map((rowLabel, i) => (
              <tr key={rowLabel}>
                <th className="heatmap-th-row" title={rowLabel}>
                  {rowLabel}
                </th>

                {labels.map((colLabel, j) => {
                  const raw = matrix[i]?.[j];
                  const v = Number(raw ?? 0);

                  return (
                    <td key={`${rowLabel}-${colLabel}`}>
                      <button
                        type="button"
                        className="heatmap-cell"
                        style={{
                          "--heatmap-bg": corrCellColor(v),
                          color: corrTextColor(v),
                        }}
                        title={`${rowLabel} vs ${colLabel}: ${v.toFixed(3)}`}
                        onMouseEnter={() =>
                          setTip({ row: rowLabel, col: colLabel, v })
                        }
                        onMouseLeave={() => setTip(null)}
                        onFocus={() =>
                          setTip({ row: rowLabel, col: colLabel, v })
                        }
                        onBlur={() => setTip(null)}
                        aria-label={`${rowLabel} vs ${colLabel}, correlation ${v.toFixed(
                          3
                        )}`}
                      >
                        {Math.abs(v) >= 0.25 ? v.toFixed(2) : ""}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function BoxPlotPanel({ data }) {
  if (!data?.length) return null;

  const gmin = Math.min(...data.map((b) => b.min));
  const gmax = Math.max(...data.map((b) => b.max));
  const span = gmax - gmin || 1;
  const sx = (v) => ((v - gmin) / span) * 100;

  return (
    <div className="boxplot-wrap">
      {data.map((b) => (
        <div key={b.category} className="boxplot-row">
          <span className="boxplot-label" title={b.category}>
            {b.category}
          </span>

          <svg
            className="boxplot-svg"
            viewBox="0 0 100 28"
            preserveAspectRatio="none"
          >
            <line
              x1={sx(b.min)}
              y1={14}
              x2={sx(b.q1)}
              y2={14}
              stroke="rgba(148,163,184,0.9)"
              strokeWidth={1.5}
            />
            <rect
              x={sx(b.q1)}
              y={6}
              width={Math.max(0.8, sx(b.q3) - sx(b.q1))}
              height={16}
              fill="rgba(56, 189, 248, 0.35)"
              stroke="rgba(56, 189, 248, 0.8)"
              rx={1}
            />
            <line
              x1={sx(b.median)}
              y1={5}
              x2={sx(b.median)}
              y2={23}
              stroke="#f8fafc"
              strokeWidth={2}
            />
            <line
              x1={sx(b.q3)}
              y1={14}
              x2={sx(b.max)}
              y2={14}
              stroke="rgba(148,163,184,0.9)"
              strokeWidth={1.5}
            />
          </svg>

          <span className="boxplot-meta">n={b.n}</span>
        </div>
      ))}

      <p className="boxplot-scale">
        Scale: {gmin.toPrecision(4)} → {gmax.toPrecision(4)}
      </p>
    </div>
  );
}

function PanelChart({ panel }) {
  const commonTooltip = {
    contentStyle: {
      background: chartTheme.tooltipBg,
      border: `1px solid ${chartTheme.tooltipBorder}`,
      borderRadius: 8,
      color: "#e2e8f0",
    },
    labelStyle: { color: "#94a3b8" },
  };

  if ((panel.chart === "bar" || panel.chart === "line") && panel.data?.length) {
    const isCorr = panel.id === "correlation";

    return (
      <ResponsiveContainer width="100%" height={300}>
        <BarChart
          data={panel.data}
          margin={{ top: 8, right: 12, left: 0, bottom: 48 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
          <XAxis
            dataKey="name"
            tick={{ fill: chartTheme.axis, fontSize: 11 }}
            angle={-35}
            textAnchor="end"
            height={70}
            interval={0}
          />
          <YAxis
            tick={{ fill: chartTheme.axis, fontSize: 11 }}
            domain={isCorr ? [-1, 1] : undefined}
          />
          <Tooltip
            {...commonTooltip}
            formatter={(v) => [
              Number(v).toFixed(3),
              isCorr ? "r" : "value",
            ]}
          />

          {isCorr ? (
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {panel.data.map((e) => (
                <Cell
                  key={e.name}
                  fill={
                    e.value >= 0
                      ? "rgba(56, 189, 248, 0.85)"
                      : "rgba(248, 113, 113, 0.75)"
                  }
                />
              ))}
            </Bar>
          ) : (
            <Bar
              dataKey="value"
              fill="rgba(125, 211, 252, 0.75)"
              radius={[4, 4, 0, 0]}
            />
          )}
        </BarChart>
      </ResponsiveContainer>
    );
  }

  if (panel.chart === "histogram" && panel.data?.length) {
    return (
      <ResponsiveContainer width="100%" height={300}>
        <BarChart
          data={panel.data}
          margin={{ top: 8, right: 12, left: 0, bottom: 64 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
          <XAxis
            dataKey="label"
            tick={{ fill: chartTheme.axis, fontSize: 9 }}
            angle={-55}
            textAnchor="end"
            height={90}
            interval={0}
          />
          <YAxis tick={{ fill: chartTheme.axis, fontSize: 11 }} />
          <Tooltip {...commonTooltip} />
          <Bar
            dataKey="value"
            fill="rgba(125, 211, 252, 0.7)"
            radius={[3, 3, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  if (panel.chart === "scatter" && panel.data?.length) {
    return (
      <ResponsiveContainer width="100%" height={320}>
        <ScatterChart margin={{ top: 8, right: 12, left: 8, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
          <XAxis
            type="number"
            dataKey="x"
            name="X"
            tick={{ fill: chartTheme.axis, fontSize: 11 }}
          />
          <YAxis
            type="number"
            dataKey="y"
            name="Y"
            tick={{ fill: chartTheme.axis, fontSize: 11 }}
          />
          <ZAxis range={[60, 60]} />
          <Tooltip
            cursor={{ strokeDasharray: "3 3" }}
            {...commonTooltip}
            formatter={(v, n) => [Number(v).toPrecision(4), n]}
          />
          <Scatter data={panel.data} fill="rgba(56, 189, 248, 0.65)" />
        </ScatterChart>
      </ResponsiveContainer>
    );
  }

  if (panel.chart === "heatmap" && panel.labels?.length) {
    return <HeatmapPanel labels={panel.labels} matrix={panel.matrix} />;
  }

  if (panel.chart === "boxplot" && panel.data?.length) {
    return <BoxPlotPanel data={panel.data} />;
  }

  return <p className="text-muted">No chart data for this panel.</p>;
}

function Dashboard({ payload, qualityScore, onClose }) {
  const printRef = useRef(null);
  const { file: selectedFile } = useAnalysis();

  const [order, setOrder] = useState([]);
  const [visible, setVisible] = useState({});
  const [customizeOpen, setCustomizeOpen] = useState(false);
  const [pdfBusy, setPdfBusy] = useState(false);
  const [customChart, setCustomChart] = useState(null);
  const [customChartLoading, setCustomChartLoading] = useState(false);

  useEffect(() => {
    if (!payload?.panels?.length) return;

    const ids = payload.panels.map((p) => p.id);

    try {
      const raw = localStorage.getItem(DASH_PREFS_KEY);

      if (!raw) {
        setOrder(ids);
        setVisible(Object.fromEntries(ids.map((id) => [id, true])));
        return;
      }

      const saved = JSON.parse(raw);

      if (Array.isArray(saved.ids) && saved.ids.join(",") === ids.join(",")) {
        setOrder(saved.order.filter((id) => ids.includes(id)));
        const vis = {
          ...Object.fromEntries(ids.map((id) => [id, true])),
          ...saved.visibility,
        };
        setVisible(vis);
      } else {
        setOrder(ids);
        setVisible(Object.fromEntries(ids.map((id) => [id, true])));
      }
    } catch {
      setOrder(ids);
      setVisible(Object.fromEntries(ids.map((id) => [id, true])));
    }
  }, [payload]);

  useEffect(() => {
    if (!payload?.panels?.length || !order.length) return;

    const ids = payload.panels.map((p) => p.id);

    localStorage.setItem(
      DASH_PREFS_KEY,
      JSON.stringify({ ids, order, visibility: visible })
    );
  }, [order, visible, payload]);

  const panelById = useMemo(() => {
    const m = new Map();
    (payload?.panels || []).forEach((p) => m.set(p.id, p));
    return m;
  }, [payload]);

  const orderedPanels = useMemo(() => {
    return order
      .map((id) => panelById.get(id))
      .filter(Boolean)
      .filter((p) => visible[p.id] !== false);
  }, [order, panelById, visible]);

  const kpis = useMemo(() => {
    const base = payload?.kpis || [];

    if (
      qualityScore != null &&
      qualityScore !== undefined &&
      !Number.isNaN(Number(qualityScore))
    ) {
      return [
        {
          id: "quality",
          label: "Quality score",
          value: Number(qualityScore),
          format: "float",
          hint: "From your last EDA run (0–100 scale on server)",
        },
        ...base,
      ];
    }

    return base;
  }, [payload, qualityScore]);

  const movePanel = useCallback((id, dir) => {
    setOrder((prev) => {
      const i = prev.indexOf(id);
      if (i < 0) return prev;

      const j = i + dir;
      if (j < 0 || j >= prev.length) return prev;

      const next = [...prev];
      [next[i], next[j]] = [next[j], next[i]];

      return next;
    });
  }, []);

  const resetLayout = useCallback(() => {
    if (!payload?.panels) return;

    const ids = payload.panels.map((p) => p.id);
    setOrder(ids);
    setVisible(Object.fromEntries(ids.map((id) => [id, true])));
    localStorage.removeItem(DASH_PREFS_KEY);
  }, [payload]);

  const downloadPdf = useCallback(async () => {
    const el = printRef.current;
    if (!el) return;

    setPdfBusy(true);

    try {
      const canvas = await html2canvas(el, {
        scale: 1.75,
        useCORS: true,
        backgroundColor: "#0b1220",
        logging: false,
      });

      const imgData = canvas.toDataURL("image/png", 1);
      const pdf = new jsPDF({
        orientation: "landscape",
        unit: "pt",
        format: "a4",
      });

      const pw = pdf.internal.pageSize.getWidth();
      const ph = pdf.internal.pageSize.getHeight();
      const margin = 28;
      const maxW = pw - 2 * margin;
      const maxH = ph - 2 * margin;
      const ratio = Math.min(maxW / canvas.width, maxH / canvas.height);
      const w = canvas.width * ratio;
      const h = canvas.height * ratio;

      pdf.addImage(imgData, "PNG", (pw - w) / 2, (ph - h) / 2, w, h);
      pdf.save(`tadaa-dashboard-${payload?.meta?.target || "export"}.pdf`);
    } catch (e) {
      console.error(e);
      alert(
        "Could not create PDF. Try a smaller window or disable browser extensions."
      );
    } finally {
      setPdfBusy(false);
    }
  }, [payload]);

  const handleGenerateCustomChart = useCallback(
    async (config) => {
      if (!selectedFile) {
        alert("Please upload a file first.");
        return;
      }

      if (config.chartType !== "correlation" && !config.x) {
        alert("Please select X column.");
        return;
      }

      try {
        setCustomChartLoading(true);

        const formData = new FormData();
        formData.append("file", selectedFile);
        formData.append("chart_type", config.chartType);
        formData.append("x_col", config.x || "");
        formData.append("y_col", config.y || "");
        formData.append("group_col", config.group || "");
        formData.append("aggregation", config.agg || "none");

        const res = await api.post("/custom-chart", formData);

        if (res.data?.error) {
          alert(res.data.error);
          return;
        }

        setCustomChart(res.data);
      } catch (err) {
        console.error(err);
        alert("Failed to generate chart.");
      } finally {
        setCustomChartLoading(false);
      }
    },
    [selectedFile]
  );

  if (!payload?.panels?.length) {
    return (
      <div className="dashboard">
        <div className="dashboard__inner">
          <p className="text-muted">No dashboard data.</p>

          <button type="button" className="btn btn--primary" onClick={onClose}>
            Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard dashboard--interactive">
      <div className="dashboard__inner">
        <header className="dashboard__head">
          <div>
            <h1 className="dashboard__title">Interactive dashboard</h1>

            <p className="dashboard__subtitle">
              Target <strong>{payload.meta?.target}</strong> (
              {payload.meta?.targetKind}) · Hover charts for values · Customize
              layout below
            </p>
          </div>

          <div className="dashboard__toolbar">
            <button
              type="button"
              className={`btn btn--ghost btn--small${
                customizeOpen ? " active" : ""
              }`}
              onClick={() => setCustomizeOpen((v) => !v)}
            >
              Customize layout
            </button>

            <button
              type="button"
              className="btn btn--ghost btn--small"
              onClick={downloadPdf}
              disabled={pdfBusy}
            >
              {pdfBusy ? "PDF…" : "Download PDF"}
            </button>

            <button
              type="button"
              className="btn btn--primary btn--small"
              onClick={onClose}
            >
              Back to analysis
            </button>
          </div>
        </header>

        {customizeOpen && (
          <div className="dashboard-customize card">
            <h3 className="card__title">Dashboard customization</h3>

            <p className="dashboard-customize__hint">
              Toggle panels, reorder with arrows. Preferences are saved in this
              browser for the same chart set.
            </p>

            <ul className="dashboard-customize__list">
              {order.map((id) => {
                const p = panelById.get(id);
                if (!p) return null;

                return (
                  <li key={id} className="dashboard-customize__row">
                    <label className="dashboard-customize__check">
                      <input
                        type="checkbox"
                        checked={visible[id] !== false}
                        onChange={(e) =>
                          setVisible((v) => ({
                            ...v,
                            [id]: e.target.checked,
                          }))
                        }
                      />
                      <span>{p.title}</span>
                    </label>

                    <div className="dashboard-customize__move">
                      <button
                        type="button"
                        className="btn btn--ghost btn--small"
                        aria-label="Move up"
                        onClick={() => movePanel(id, -1)}
                      >
                        ↑
                      </button>

                      <button
                        type="button"
                        className="btn btn--ghost btn--small"
                        aria-label="Move down"
                        onClick={() => movePanel(id, 1)}
                      >
                        ↓
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>

            <button
              type="button"
              className="btn btn--ghost btn--small"
              onClick={resetLayout}
            >
              Reset to default
            </button>
          </div>
        )}

        <div ref={printRef} className="dashboard-print-root">
          <section className="kpi-strip" aria-label="Key metrics">
            {kpis.map((k) => (
              <article key={k.id} className="kpi-card" title={k.hint}>
                <span className="kpi-card__label">{k.label}</span>
                <span className="kpi-card__value">{formatKpiValue(k)}</span>
              </article>
            ))}
          </section>

          <div className="chart-builder-card">
            <h2 className="card__title">Create your own chart</h2>

            <p className="text-muted">
              Select features and generate an additional chart without changing
              the default dashboard.
            </p>

            <ChartBuilder
              columns={payload.meta?.columns || []}
              loading={customChartLoading}
              onGenerate={handleGenerateCustomChart}
            />

            {customChart && (
              <div className="chart-card chart-card--interactive">
                <div className="chart-card__head">
                  <h2 className="chart-card__title">{customChart.title}</h2>

                  {customChart.subtitle && (
                    <p className="chart-card__sub">{customChart.subtitle}</p>
                  )}
                </div>

                <div className="chart-card__body">
                  <PanelChart panel={customChart} />
                </div>
              </div>
            )}
          </div>

          <div className="dashboard__grid dashboard__grid--interactive">
            {orderedPanels.map((panel) => (
              <article
                key={panel.id}
                className="chart-card chart-card--interactive"
              >
                <div className="chart-card__head">
                  <h2 className="chart-card__title">{panel.title}</h2>

                  {panel.subtitle && (
                    <p className="chart-card__sub">{panel.subtitle}</p>
                  )}
                </div>

                <div className="chart-card__body">
                  <PanelChart panel={panel} />
                </div>
              </article>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;