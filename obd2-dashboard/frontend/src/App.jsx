import { useEffect, useMemo, useState } from "react";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";

const DEFAULT_PAYLOAD = {
  rpm: null,
  speed_kmh: null,
  coolant_temp_c: null,
  throttle_pos: null,
  fuel_level: null,
  intake_temp_c: null,
  engine_load: null,
  fuel_pressure: null,
  barometric_pressure: null,
  timing_advance: null,
  maf: null,
  o2_voltage: null,
  battery_voltage: null,
  source: "unknown",
};

function formatValue(value, decimals = 0) {
  if (value === null || value === undefined) {
    return "—";
  }
  return Number(value).toFixed(decimals);
}

function MetricCard({ label, value, unit }) {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      <div className="metric-unit">{unit}</div>
    </div>
  );
}

function StatusBanner({ status, children }) {
  return <div className={`status-banner ${status}`}>{children}</div>;
}

function ConnectionStatus({ adapterConnected, carConnected }) {
  return (
    <div className="connection-status">
      <div className={`connection-item ${adapterConnected ? "connected" : "disconnected"}`}>
        <span className="connection-label">Adapter</span>
        <span className="connection-dot"></span>
        <span className="connection-text">{adapterConnected ? "Connected" : "Disconnected"}</span>
      </div>
      <div className={`connection-item ${carConnected ? "connected" : "disconnected"}`}>
        <span className="connection-label">Car</span>
        <span className="connection-dot"></span>
        <span className="connection-text">{carConnected ? "Connected" : "Disconnected"}</span>
      </div>
    </div>
  );
}

function RecordingStatus({ recordingActive }) {
  return (
    <div className="recording-status">
      <div className={`recording-indicator ${recordingActive ? "active" : "inactive"}`}>
        <span className="recording-dot"></span>
        <span className="recording-text">
          {recordingActive ? "Recording Active" : "Recording Inactive"}
        </span>
      </div>
    </div>
  );
}

function RecordingButton({ recordingActive, onStart, onStop }) {
  const handleClick = () => {
    if (recordingActive) {
      onStop();
    } else {
      onStart();
    }
  };

  return (
    <button 
      className={`recording-button ${recordingActive ? "stop" : "start"}`}
      onClick={handleClick}
    >
      {recordingActive ? "Stop Recording" : "Start Recording"}
    </button>
  );
}

function Dashboard({ payload, status, adapterConnected, carConnected, statusText, recordingActive, onStartRecording, onStopRecording }) {
  return (
    <div className="app-shell">
      <header>
        <h1>OBD2 Dashboard</h1>
        <nav>
          <Link to="/" className="nav-link active">Dashboard</Link>
          <Link to="/history" className="nav-link">History</Link>
        </nav>
      </header>

      <main>
        <section className="grid">
          <MetricCard label="RPM" value={formatValue(payload.rpm, 0)} unit="rev/min" />
          <MetricCard label="Speed" value={formatValue(payload.speed_kmh, 1)} unit="km/h" />
          <MetricCard label="Throttle" value={formatValue(payload.throttle_pos, 1)} unit="°C" />
          <MetricCard label="Throttle" value={formatValue(payload.throttle_pos, 1)} unit="%" />
        </section>

        <ConnectionStatus adapterConnected={adapterConnected} carConnected={carConnected} />

        <div className="recording-controls">
          <RecordingStatus recordingActive={recordingActive} />
          <RecordingButton 
            recordingActive={recordingActive} 
            onStart={onStartRecording} 
            onStop={onStopRecording} 
          />
        </div>

        <StatusBanner status={status}>{statusText}</StatusBanner>
      </main>
    </div>
  );
}

function History() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sortByRecent, setSortByRecent] = useState(true);

  useEffect(() => {
    fetch('/history')
      .then(res => res.json())
      .then(data => {
        setSessions(data.sessions || []);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load history:', err);
        setLoading(false);
      });
  }, []);

  const sortedSessions = useMemo(() => {
    const sorted = [...sessions];
    if (sortByRecent) {
      sorted.sort((a, b) => b.timestamp - a.timestamp);
    } else {
      sorted.sort((a, b) => a.timestamp - b.timestamp);
    }
    return sorted;
  }, [sessions, sortByRecent]);

  if (loading) {
    return (
      <div className="app-shell">
        <header>
          <h1>OBD2 Dashboard - History</h1>
          <nav>
            <Link to="/" className="nav-link">Dashboard</Link>
            <Link to="/history" className="nav-link active">History</Link>
          </nav>
        </header>
        <main>
          <div className="loading">Loading history...</div>
        </main>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header>
        <h1>OBD2 Dashboard - History</h1>
        <nav>
          <Link to="/" className="nav-link">Dashboard</Link>
          <Link to="/history" className="nav-link active">History</Link>
        </nav>
      </header>
      <main>
        <div className="history-container">
          <div className="history-controls">
            <button 
              className="sort-button"
              onClick={() => setSortByRecent(!sortByRecent)}
            >
              Sort: {sortByRecent ? 'Most Recent First' : 'Oldest First'}
            </button>
          </div>
          {sortedSessions.length === 0 ? (
            <div className="no-data">No historical data available</div>
          ) : (
            sortedSessions.map((session, idx) => (
              <div key={idx} className="session-card">
                <h3>{session.title}</h3>
                <div className="session-stats">
                  <span>{session.data.length} data points</span>
                  <span className="filename">{session.filename}</span>
                </div>
                <div className="data-preview">
                  {session.data.slice(-5).map((point, i) => (
                    <div key={i} className="data-point">
                      <span>{new Date(point.timestamp * 1000).toLocaleTimeString()}</span>
                      <span>RPM: {point.rpm || '—'}</span>
                      <span>Speed: {point.speed_kmh ? `${point.speed_kmh} km/h` : '—'}</span>
                      <span>Temp: {point.coolant_temp_c ? `${point.coolant_temp_c}°C` : '—'}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
}

export default function App() {
  const [payload, setPayload] = useState(DEFAULT_PAYLOAD);
  const [status, setStatus] = useState("connecting");
  const [adapterConnected, setAdapterConnected] = useState(false);
  const [carConnected, setCarConnected] = useState(false);
  const [recordingActive, setRecordingActive] = useState(false);

  const wsUrl = import.meta.env.VITE_WS_URL ?? `ws://${location.host}/ws`;
  const statusUrl = `http://${location.host}/status`;

  useEffect(() => {
    let ws;
    let reconnect = true;
    let reconnectTimer = null;

    const connect = () => {
      setStatus("connecting");
      ws = new WebSocket(wsUrl);

      ws.addEventListener("open", () => {
        setStatus("connected");
      });

      ws.addEventListener("message", (event) => {
        try {
          const data = JSON.parse(event.data);
          setPayload(data);
        } catch (error) {
          console.warn("Failed to parse payload", error);
        }
      });

      ws.addEventListener("close", () => {
        setStatus("disconnected");
        if (reconnect) {
          reconnectTimer = window.setTimeout(connect, 2000);
        }
      });

      ws.addEventListener("error", () => {
        setStatus("error");
      });
    };

    connect();

    return () => {
      reconnect = false;
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer);
      }
      if (ws) {
        ws.close();
      }
    };
  }, [wsUrl]);

  useEffect(() => {
    const pollStatus = async () => {
      try {
        const response = await fetch(statusUrl);
        const data = await response.json();
        setAdapterConnected(data.adapter_connected || false);
        setCarConnected(data.car_connected || false);
        setRecordingActive(data.recording_active || false);
      } catch (error) {
        console.warn("Failed to fetch status", error);
      }
    };

    pollStatus();
    const interval = setInterval(pollStatus, 3000); // Poll every 3 seconds

    return () => clearInterval(interval);
  }, [statusUrl]);

  const handleStartRecording = async () => {
    try {
      const response = await fetch('/recording/start', { method: 'POST' });
      const data = await response.json();
      if (response.ok) {
        setRecordingActive(true);
      } else {
        console.error("Failed to start recording:", data);
      }
    } catch (error) {
      console.error("Failed to start recording:", error);
    }
  };

  const handleStopRecording = async () => {
    try {
      const response = await fetch('/recording/stop', { method: 'POST' });
      const data = await response.json();
      if (response.ok) {
        setRecordingActive(false);
      } else {
        console.error("Failed to stop recording:", data);
      }
    } catch (error) {
      console.error("Failed to stop recording:", error);
    }
  };

  const statusText = useMemo(() => {
    switch (status) {
      case "connected":
        return "Connected";
      case "connecting":
        return "Connecting…";
      case "disconnected":
        return "Disconnected — retrying";
      case "error":
        return "WebSocket error";
      default:
        return "Unknown";
    }
  }, [status]);

  return (
    <Router>
      <Routes>
        <Route path="/" element={
          <Dashboard 
            payload={payload} 
            status={status} 
            adapterConnected={adapterConnected} 
            carConnected={carConnected} 
            statusText={statusText}
            recordingActive={recordingActive}
            onStartRecording={handleStartRecording}
            onStopRecording={handleStopRecording}
          />
        } />
        <Route path="/history" element={<History />} />
      </Routes>
    </Router>
  );
}
