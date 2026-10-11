import { useRef, useState } from "react";
import { useAnalysis } from "../context/AnalysisContext";
import { api } from "../api/client";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// ── Palette ──────────────────────────────────────────────────────────────────
const BAR_COLORS = [
  "rgba(56,189,248,0.85)",
  "rgba(125,211,252,0.75)",
  "rgba(99,179,237,0.8)",
  "rgba(147,197,253,0.75)",
  "rgba(167,243,208,0.7)",
  "rgba(252,211,77,0.7)",
];

const CHART_THEME = {
  grid:        "rgba(148,163,184,0.12)",
  axis:        "#94a3b8",
  tooltipBg:   "rgba(15,23,42,0.97)",
  tooltipBorder:"rgba(56,189,248,0.3)",
};

const commonTooltip = {
  contentStyle: {
    background:   CHART_THEME.tooltipBg,
    border:       `1px solid ${CHART_THEME.tooltipBorder}`,
    borderRadius: 8,
    color:        "#e2e8f0",
    fontSize:     12,
  },
  labelStyle: { color: "#94a3b8" },
};

// ── Mini chart renderer ───────────────────────────────────────────────────────
function KlausChart({ chartType, data }) {
  if (!data?.length) return null;

  if (chartType === "line") {
    return (
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 48 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.grid} />
          <XAxis
            dataKey="name"
            tick={{ fill: CHART_THEME.axis, fontSize: 10 }}
            angle={-35}
            textAnchor="end"
            height={60}
            interval={0}
          />
          <YAxis tick={{ fill: CHART_THEME.axis, fontSize: 10 }} />
          <Tooltip {...commonTooltip} />
          <Line
            type="monotone"
            dataKey="value"
            stroke="rgba(56,189,248,0.9)"
            strokeWidth={2}
            dot={{ fill: "rgba(56,189,248,0.9)", r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>
    );
  }

  if (chartType === "pie") {
    return (
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            outerRadius={80}
            label={({ name, percent }) =>
              `${name} (${(percent * 100).toFixed(0)}%)`
            }
            labelLine={false}
          >
            {data.map((_, i) => (
              <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip {...commonTooltip} />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  if (chartType === "scatter") {
    return (
      <ResponsiveContainer width="100%" height={220}>
        <ScatterChart margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.grid} />
          <XAxis
            type="number"
            dataKey="x"
            name="x"
            tick={{ fill: CHART_THEME.axis, fontSize: 10 }}
          />
          <YAxis
            type="number"
            dataKey="y"
            name="y"
            tick={{ fill: CHART_THEME.axis, fontSize: 10 }}
          />
          <Tooltip {...commonTooltip} />
          <Scatter data={data} fill="rgba(56,189,248,0.65)" />
        </ScatterChart>
      </ResponsiveContainer>
    );
  }

  // Default: bar
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 48 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.grid} />
        <XAxis
          dataKey="name"
          tick={{ fill: CHART_THEME.axis, fontSize: 10 }}
          angle={-35}
          textAnchor="end"
          height={60}
          interval={0}
        />
        <YAxis tick={{ fill: CHART_THEME.axis, fontSize: 10 }} />
        <Tooltip {...commonTooltip} />
        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
          {data.map((_, i) => (
            <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// ── Insight renderer (supports **bold** markdown subset) ─────────────────────
function KlausInsight({ text }) {
  if (!text) return null;
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <p className="klaus-insight__text">
      {parts.map((part, i) =>
        part.startsWith("**") && part.endsWith("**") ? (
          <strong key={i}>{part.slice(2, -2)}</strong>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </p>
  );
}

// ── Suggested prompts ─────────────────────────────────────────────────────────
const SUGGESTIONS = [
  "Compare total sales by region",
  "Show average salary by department",
  "Count records by category",
  "Which product has the highest revenue?",
];

// ── Main component ────────────────────────────────────────────────────────────
function KlausChat() {
  const { file } = useAnalysis();
  const inputRef  = useRef(null);

  const [query,    setQuery]    = useState("");
  const [loading,  setLoading]  = useState(false);
  const [history,  setHistory]  = useState([]); // [{query, result, error}]

  // ── Submit ──────────────────────────────────────────────────────────────────
  const handleSubmit = async (q = query) => {
    const trimmed = q.trim();
    if (!trimmed || loading) return;

    if (!file) {
      setHistory((h) => [
        { query: trimmed, error: "No dataset loaded. Upload a CSV first." },
        ...h,
      ]);
      setQuery("");
      return;
    }

    setLoading(true);
    setQuery("");

    try {
      const formData = new FormData();
      formData.append("file",  file);
      formData.append("query", trimmed);

      const res  = await api.post("/chat-viz", formData);
      const data = res.data;

      if (data?.error) {
        setHistory((h) => [{ query: trimmed, error: data.error }, ...h]);
      } else {
        setHistory((h) => [{ query: trimmed, result: data }, ...h]);
      }
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        "Request failed. Is the backend running?";
      setHistory((h) => [{ query: trimmed, error: msg }, ...h]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="klaus-chat">
      {/* Header */}
      <div className="klaus-chat__header">
        <span className="klaus-chat__avatar" aria-hidden="true">🧐</span>
        <div>
          <h3 className="klaus-chat__name">Klaus</h3>
          <p className="klaus-chat__tagline">Ask me anything about your data</p>
        </div>
        {file && (
          <span className="klaus-chat__file-badge" title={file.name}>
            📁 {file.name.length > 18 ? file.name.slice(0, 16) + "…" : file.name}
          </span>
        )}
      </div>

      {/* Suggestions (only when history is empty) */}
      {history.length === 0 && (
        <div className="klaus-chat__suggestions">
          <p className="klaus-chat__suggestions-label">Try asking:</p>
          <div className="klaus-chat__suggestion-chips">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                type="button"
                className="btn btn--ghost btn--small"
                onClick={() => handleSubmit(s)}
                disabled={loading || !file}
              >
                {s}
              </button>
            ))}
          </div>

          {!file && (
            <div className="alert alert--warning" style={{ marginTop: "0.75rem" }}>
              Upload a CSV dataset first to start querying.
            </div>
          )}
        </div>
      )}

      {/* History (newest first) */}
      <div className="klaus-chat__history">
        {/* Loading skeleton */}
        {loading && (
          <div className="klaus-message">
            <div className="klaus-message__query-bubble">
              <span className="text-muted" style={{ fontSize: "0.8rem" }}>You</span>
              <p>{query || "…"}</p>
            </div>
            <div className="klaus-message__result card card--inset">
              <div className="klaus-thinking">
                <span />
                <span />
                <span />
                <p>Klaus is thinking…</p>
              </div>
            </div>
          </div>
        )}

        {history.map((item, idx) => (
          <div key={idx} className="klaus-message">
            {/* User query bubble */}
            <div className="klaus-message__query-bubble">
              <span className="text-muted" style={{ fontSize: "0.8rem" }}>You</span>
              <p>{item.query}</p>
            </div>

            {/* Klaus response */}
            <div className="klaus-message__result card card--inset">
              {item.error ? (
                <div className="alert alert--error" role="alert">
                  <strong>Klaus:</strong> {item.error}
                </div>
              ) : (
                <>
                  {/* Meta pill */}
                  <div className="klaus-meta-row">
                    <span className="badge badge--medium">
                      {item.result.meta?.aggregation?.toUpperCase()} of{" "}
                      <em>{item.result.meta?.value_col}</em>
                    </span>
                    <span className="badge badge--low">
                      by <em>{item.result.meta?.category_col}</em>
                    </span>
                    <span className="badge badge--low" style={{ marginLeft: "auto" }}>
                      {item.result.meta?.chart_type} chart
                    </span>
                  </div>

                  {/* Chart */}
                  <div style={{ marginTop: "0.75rem" }}>
                    <KlausChart
                      chartType={item.result.action?.chart_type}
                      data={item.result.chart_data}
                    />
                  </div>

                  {/* Insight */}
                  {item.result.insight && (
                    <div className="klaus-insight">
                      <span className="klaus-insight__label">Klaus's take</span>
                      <KlausInsight text={item.result.insight} />
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="klaus-chat__input-row">
        <input
          ref={inputRef}
          className="select"
          style={{ flex: 1, height: "2.5rem" }}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKey}
          placeholder={
            file
              ? "Ask Klaus: 'Compare total revenue by product…'"
              : "Upload a CSV first…"
          }
          disabled={loading || !file}
          aria-label="Ask Klaus a question about your data"
        />
        <button
          type="button"
          className="btn btn--primary btn--small"
          onClick={() => handleSubmit()}
          disabled={loading || !query.trim() || !file}
          style={{ whiteSpace: "nowrap" }}
        >
          {loading ? "…" : "Ask"}
        </button>
      </div>

      {/* Clear history */}
      {history.length > 0 && (
        <button
          type="button"
          className="btn btn--ghost btn--small"
          style={{ marginTop: "0.5rem", width: "100%" }}
          onClick={() => setHistory([])}
        >
          Clear conversation
        </button>
      )}
    </div>
  );
}

export default KlausChat;
