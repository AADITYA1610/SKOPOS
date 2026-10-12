import { useEffect, useRef, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import "./LiveStreamPage.css";

const MEASUREMENTS = [
  [25.4, 62],
  [25.8, null],
  [85, 63],
  [26.1, 120],
  [null, 64],
  [26, 61],
  [25.7, 60],
  [25.9, 62],
  [26.2, 63],
  [26.4, 64],
  [26.1, 62],
  [25.8, 61],
];

function waitForNextReading(signal) {
  return new Promise((resolve) => {
    if (signal.aborted) {
      resolve();
      return;
    }

    const finish = () => {
      clearTimeout(timer);
      signal.removeEventListener("abort", finish);
      resolve();
    };

    const timer = setTimeout(finish, 2000);
    signal.addEventListener("abort", finish, { once: true });
  });
}

function getErrorMessage(error) {
  const detail = error.response?.data?.detail;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).join("; ");
  }

  if (error.code === "ECONNABORTED") {
    return "The backend request timed out. Check that FastAPI is running.";
  }

  return "Could not reach the stream API. Check the backend terminal.";
}

function displayValue(value, unit) {
  return value == null ? "Missing" : `${value} ${unit}`;
}

function describeFlag(flag) {
  if (flag.type === "missing_measurement") {
    return `Missing ${flag.field}`;
  }

  if (flag.type === "outside_demo_range") {
    return `${flag.field} outside range`;
  }

  return "Repeated event identity";
}

function LiveStreamPage() {
  const [source, setSource] = useState("demo");
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState("Ready");
  const [session, setSession] = useState(null);
  const [error, setError] = useState("");
  const controllerRef = useRef(null);

  useEffect(() => {
    if (!running) return undefined;

    const controller = new AbortController();
    controllerRef.current = controller;

    const { signal } = controller;
    const requestOptions = { signal, timeout: 10000 };

    async function runDemo() {
      try {
        setStatus("Connecting");

        const created = await api.post(
          "/streams/sessions",
          {
            name: "Skopos browser demo",
            source_type: "simulated",
            window_size: 10,
          },
          requestOptions
        );

        if (signal.aborted) return;

        const sessionId = created.data.session_id;
        setSession(created.data);
        setStatus("Running");

        const events = [];

        MEASUREMENTS.forEach(([temperature, humidity], index) => {
          const event = {
            event_id: `reading-${String(index + 1).padStart(3, "0")}`,
            sensor_id: "sensor-A",
            temperature,
            humidity,
          };

          events.push(event);

          if (index === 2) {
            events.push({ ...event, duplicate: true });
          }
        });

        let previousTimestamp = null;

        for (let index = 0; index < events.length; index += 1) {
          if (signal.aborted) return;

          const event = events[index];
          const timestamp = event.duplicate
            ? previousTimestamp
            : new Date().toISOString();

          previousTimestamp = timestamp;

          await api.post(
            `/streams/sessions/${sessionId}/readings`,
            {
              event_id: event.event_id,
              timestamp,
              sensor_id: event.sensor_id,
              temperature: event.temperature,
              humidity: event.humidity,
            },
            requestOptions
          );

          if (signal.aborted) return;

          const latest = await api.get(
            `/streams/sessions/${sessionId}`,
            requestOptions
          );

          if (signal.aborted) return;

          setSession(latest.data);

          if (index < events.length - 1) {
            await waitForNextReading(signal);
          }
        }

        if (!signal.aborted) {
          setStatus("Completed");
          setRunning(false);
        }
      } catch (requestError) {
        if (!signal.aborted) {
          setError(getErrorMessage(requestError));
          setStatus("Error");
          setRunning(false);
        }
      }
    }

    runDemo();

    return () => {
      controller.abort();

      if (controllerRef.current === controller) {
        controllerRef.current = null;
      }
    };
  }, [running]);

  function startDemo() {
    setError("");
    setSession(null);
    setStatus("Connecting");
    setRunning(true);
  }

  function stopDemo() {
    controllerRef.current?.abort();
    setRunning(false);
    setStatus("Stopped");
  }

  const quality = session?.quality_summary;
  const readings = session?.readings ?? [];

  const missingCount = Object.values(
    quality?.missing_counts ?? {}
  ).reduce((total, count) => total + count, 0);

  const rangeCount = Object.values(
    quality?.out_of_range_counts ?? {}
  ).reduce((total, count) => total + count, 0);

  // Arrival numbers remain distinct even when event IDs repeat.
  const chartData = readings.map((reading, index) => ({
    ...reading,
    arrival: session.total_received - readings.length + index + 1,
  }));

  const sources = [
    { id: "demo", label: "Demo stream", detail: "Available" },
    { id: "api", label: "API", detail: "Planned" },
    { id: "sensor", label: "Sensor", detail: "Planned" },
  ];

  return (
    <main className="page stream-page">
      <header className="page__intro">
        <h1 className="page__title">Live Stream</h1>
        <p className="page__subtitle">
          Receive successive readings and inspect quality in the latest
          10 arrivals.
        </p>
      </header>

      <section className="card section">
        <h2 className="card__title">Connect a data source</h2>

        <div className="stream-sources">
          {sources.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`stream-source ${
                source === item.id ? "stream-source--selected" : ""
              }`}
              aria-pressed={source === item.id}
              disabled={running}
              onClick={() => setSource(item.id)}
            >
              <strong>{item.label}</strong>
              <span>{item.detail}</span>
            </button>
          ))}
        </div>

        {source === "demo" ? (
          <>
            <p className="stream-description">
              Simulated environmental readings arrive every two seconds.
              The demo includes missing measurements, range violations,
              and a repeated event. No physical sensor is connected.
            </p>

            <div className="stream-controls">
              <button
                type="button"
                className="btn btn--primary"
                disabled={running}
                onClick={startDemo}
              >
                {session ? "Start new demo" : "Start demo"}
              </button>

              <button
                type="button"
                className="btn btn--ghost"
                disabled={!running}
                onClick={stopDemo}
              >
                Stop demo
              </button>

              <span role="status" className="stream-status">
                {status}
              </span>
            </div>
          </>
        ) : (
          <p className="stream-description">
            {source === "api"
              ? "API connection is planned. Researchers will provide a source URL, any required credentials, and a refresh interval."
              : "Sensor connection is planned. Devices or gateways will send readings to a configured ingestion URL."}
            {" "}This connector is not implemented yet. Select Demo stream
            to try the current prototype.
          </p>
        )}

        {error && (
          <p role="alert" className="stream-error">
            {error}
          </p>
        )}
      </section>

      {session ? (
        <>
          <div className="stream-metrics">
            <Metric label="Total received" value={session.total_received} />
            <Metric label="Recent window" value={`${readings.length} / 10`} />
            <Metric
              label="Completeness"
              value={
                quality?.completeness_percentage == null
                  ? "—"
                  : `${quality.completeness_percentage}%`
              }
            />
            <Metric label="Missing measurements" value={missingCount} />
            <Metric label="Range violations" value={rangeCount} />
            <Metric
              label="Extra duplicate records"
              value={quality?.duplicate_extra_records ?? 0}
            />
          </div>

          {readings.length > 0 && (
            <section className="card section">
              <h2 className="card__title">Live measurement charts</h2>
              <p className="stream-description">
                Horizontal axis: arrival number. Missing measurements
                create gaps. Dashed lines show the monitoring limits.
                Values outside those limits remain visible.
              </p>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns:
                    "repeat(auto-fit, minmax(min(100%, 340px), 1fr))",
                  gap: "24px",
                }}
              >
                <MeasurementChart
                  data={chartData}
                  field="temperature"
                  title="Temperature (°C)"
                  unit="°C"
                  color="#22c9ed"
                  limits={quality?.demo_ranges?.temperature}
                />

                <MeasurementChart
                  data={chartData}
                  field="humidity"
                  title="Humidity (%)"
                  unit="%"
                  color="#a78bfa"
                  limits={quality?.demo_ranges?.humidity}
                />
              </div>
            </section>
          )}

          <section className="card section">
            <h2 className="card__title">Recent readings</h2>
            <p className="stream-description">
              Oldest to newest arrival. Original values are preserved.
              Quality counts describe this window, not the full history.
            </p>

            <div className="stream-table-wrap">
              <table className="stream-table">
                <thead>
                  <tr>
                    <th>Event</th>
                    <th>Sensor</th>
                    <th>Measurement time</th>
                    <th>Temperature</th>
                    <th>Humidity</th>
                    <th>Checks</th>
                  </tr>
                </thead>

                <tbody>
                  {readings.map((reading, index) => {
                    const issue = quality?.issues?.find(
                      (item) =>
                        item.event_id === reading.event_id &&
                        item.sensor_id === reading.sensor_id &&
                        item.received_at === reading.received_at
                    );

                    return (
                      <tr key={`${reading.received_at}-${index}`}>
                        <td>{reading.event_id}</td>
                        <td>{reading.sensor_id}</td>
                        <td>
                          {new Date(reading.timestamp).toLocaleTimeString()}
                        </td>
                        <td>{displayValue(reading.temperature, "°C")}</td>
                        <td>{displayValue(reading.humidity, "%")}</td>
                        <td>
                          {issue
                            ? issue.flags.map(describeFlag).join("; ")
                            : "No rule violations"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {!readings.length && <p>Waiting for the first reading.</p>}
          </section>

          <p className="stream-footnote">
            Demo temperature range: −20°C to 60°C. Humidity range: 0% to
            100%. These are rule checks, not drift detection. Sessions
            currently use temporary backend memory. Leaving this page
            stops the browser sender; it does not delete the session.
          </p>
        </>
      ) : (
        <p className="stream-description">
          Start a demo to see readings and quality summaries here.
        </p>
      )}
    </main>
  );
}

function MeasurementChart({ data, field, title, unit, color, limits }) {
  return (
    <div style={{ minWidth: 0 }}>
      <h3 style={{ color: "#e5edf6", marginBottom: "16px" }}>
        {title}
      </h3>

      <div
        role="img"
        aria-label={`${title} by arrival number; exact values appear in the readings table`}
        style={{ width: "100%", height: "280px" }}
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{ top: 20, right: 20, bottom: 20, left: 0 }}
          >
            <CartesianGrid stroke="#334155" strokeDasharray="3 3" />

            <XAxis
              dataKey="arrival"
              stroke="#a5b5c9"
              label={{
                value: "Arrival number",
                position: "insideBottom",
                offset: -12,
                fill: "#a5b5c9",
              }}
            />

            <YAxis stroke="#a5b5c9" domain={["auto", "auto"]} />

            <Tooltip
              filterNull={false}
              contentStyle={{
                backgroundColor: "#101b2b",
                border: "1px solid #475569",
                borderRadius: "8px",
                color: "#e5edf6",
              }}
              labelFormatter={(arrival) => `Arrival ${arrival}`}
              formatter={(value) => [
                value == null ? "Missing" : `${value} ${unit}`,
                title,
              ]}
            />

            {limits && (
              <>
                <ReferenceLine
                  y={limits.min}
                  stroke="#fbbf24"
                  strokeDasharray="5 5"
                  ifOverflow="extendDomain"
                />
                <ReferenceLine
                  y={limits.max}
                  stroke="#fbbf24"
                  strokeDasharray="5 5"
                  ifOverflow="extendDomain"
                />
              </>
            )}

            <Line
              type="linear"
              dataKey={field}
              stroke={color}
              strokeWidth={2}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
              connectNulls={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="card stream-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default LiveStreamPage;