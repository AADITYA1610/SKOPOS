import { useMemo, useState } from "react";

function ChartBuilder({ columns = [], onGenerate, loading = false }) {
  const [chartType, setChartType] = useState("bar");
  const [x, setX] = useState("");
  const [y, setY] = useState("");
  const [group, setGroup] = useState("");
  const [agg, setAgg] = useState("none");

  const needsX = useMemo(() => {
    return chartType !== "correlation";
  }, [chartType]);

  const needsY = useMemo(() => {
    return ["scatter", "line", "box"].includes(chartType);
  }, [chartType]);

  const showAgg = useMemo(() => {
    return ["bar", "line"].includes(chartType);
  }, [chartType]);

  const showGroup = useMemo(() => {
    return chartType !== "correlation" && chartType !== "histogram";
  }, [chartType]);

  function handleGenerate() {
    if (needsX && !x) {
      alert("Please select X column.");
      return;
    }

    if (needsY && !y) {
      alert("Please select Y column.");
      return;
    }

    onGenerate({
      chartType,
      x,
      y,
      group: group || null,
      agg,
    });
  }

  return (
    <div className="card">
      <h3>Create Custom Chart</h3>

      <select value={chartType} onChange={(e) => setChartType(e.target.value)}>
        <option value="bar">Bar</option>
        <option value="histogram">Histogram</option>
        <option value="scatter">Scatter</option>
        <option value="line">Line</option>
        <option value="box">Box</option>
        <option value="correlation">Correlation Heatmap</option>
      </select>

      {needsX && (
        <select value={x} onChange={(e) => setX(e.target.value)}>
          <option value="">Select X</option>
          {columns.map((col) => (
            <option key={col} value={col}>
              {col}
            </option>
          ))}
        </select>
      )}

      {needsY && (
        <select value={y} onChange={(e) => setY(e.target.value)}>
          <option value="">Select Y</option>
          {columns.map((col) => (
            <option key={col} value={col}>
              {col}
            </option>
          ))}
        </select>
      )}

      {showAgg && (
        <select value={agg} onChange={(e) => setAgg(e.target.value)}>
          <option value="none">No Aggregation</option>
          <option value="count">Count</option>
          <option value="sum">Sum</option>
          <option value="avg">Average</option>
        </select>
      )}

      {showGroup && (
        <select value={group} onChange={(e) => setGroup(e.target.value)}>
          <option value="">No Grouping</option>
          {columns.map((col) => (
            <option key={col} value={col}>
              {col}
            </option>
          ))}
        </select>
      )}

      <button type="button" onClick={handleGenerate} disabled={loading}>
        {loading ? "Generating..." : "Generate Chart"}
      </button>
    </div>
  );
}

export default ChartBuilder;