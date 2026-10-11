import { useState } from "react";
import { useAnalysis } from "../context/AnalysisContext";
import { useAuth } from "../context/AuthContext";
import { api } from "../api/client";

function PreviewTable({ rows, maxRows }) {
  const slice = maxRows != null ? rows.slice(0, maxRows) : rows;
  if (!rows?.length) return null;

  return (
    <table className="data-table">
      <thead>
        <tr>
          {Object.keys(rows[0]).map((col) => (
            <th key={col}>{col}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {slice.map((row, i) => (
          <tr key={i}>
            {Object.values(row).map((val, j) => (
              <td key={j}>{String(val)}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function UploadSection({ compact = false }) {
  const { setFile, setDatasetDecision, resetAfterNewUpload } = useAnalysis();
  const { logActivity } = useAuth();

  const [selectedFile, setSelectedFile] = useState(null);
  const [datasetInfo, setDatasetInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [previewOpen, setPreviewOpen] = useState(false);

  const handleFileChange = (e) => {
    const f = e.target.files[0];
    setSelectedFile(f);
    setFile(f);
    setError(null);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError("Choose a CSV file first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      setLoading(true);
      setError(null);
      resetAfterNewUpload();

      const response = await api.post("/analyze-dataset", formData);

      if (response.data?.error) {
        setError(response.data.error);
        setDatasetInfo(null);
        setDatasetDecision(null);
        return;
      }

      setDatasetDecision(response.data);
      setDatasetInfo(response.data);

      void logActivity("dataset_analyzed", {
        file_name: selectedFile.name,
        rows: response.data.dataset_summary?.n_rows,
        columns: response.data.dataset_summary?.n_features,
      });
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail ||
          "Could not analyze the dataset. Is the API running?"
      );
    } finally {
      setLoading(false);
    }
  };

  const previewRows = datasetInfo?.preview_rows;
  const columnSummary = datasetInfo?.column_summary;

  return (
    <section className={`section ${compact ? "section--compact" : ""}`}>
      {!compact && <h2 className="section-title">Upload Dataset</h2>}

      {/* Upload Box */}
      <div className="upload-box">
        <input type="file" accept=".csv" onChange={handleFileChange} />

        {/* File Name */}
        {selectedFile && (
          <div className="file-chip">
            📁 {selectedFile.name}
          </div>
        )}

        <button
          className="btn btn--primary upload-btn"
          onClick={handleUpload}
          disabled={loading}
        >
          {loading ? "Analyzing..." : "Analyze Dataset"}
        </button>

        {error && <div className="alert alert--error">{error}</div>}
      </div>

      {/* Overview */}
      {datasetInfo && (
        <div className="card">
          <h3 className="card__title">Dataset Overview</h3>

          <div className="overview-grid">
            <div className="overview-item">
              <span>Rows</span>
              <strong>{datasetInfo.dataset_summary.n_rows}</strong>
            </div>
            <div className="overview-item">
              <span>Columns</span>
              <strong>{datasetInfo.dataset_summary.n_features}</strong>
            </div>
          </div>
        </div>
      )}

      {/* Preview */}
      {previewRows && (
        <div className="card">
          <div className="card__header">
            <h3>Preview</h3>
            <button
              className="btn btn--ghost btn--small"
              onClick={() => setPreviewOpen(true)}
            >
              Expand
            </button>
          </div>

          <div className="table-wrap">
            <PreviewTable rows={previewRows} maxRows={5} />
          </div>
        </div>
      )}

      {/* Modal */}
      {previewOpen && (
        <div className="modal-backdrop" onClick={() => setPreviewOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Full Preview</h2>
            <div className="table-wrap">
              <PreviewTable rows={previewRows} />
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

export default UploadSection;