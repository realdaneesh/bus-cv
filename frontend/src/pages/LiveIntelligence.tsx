import React, { useEffect, useState, useCallback, useRef } from 'react';
import { Play, Square, Camera, Cpu, Navigation, VideoOff, AlertCircle, Car, Bike, Bus as BusIcon, Truck, AlertTriangle, Gauge, MonitorPlay } from 'lucide-react';
import Header from '../components/Header';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';
import { StatusDot } from '../components/Badges';
import { getMonitoringStatus, startMonitoring, stopMonitoring, API_BASE_URL } from '../services/api';
import type { MonitoringStatus } from '../types';

function statusDotVariant(s: string): 'online' | 'offline' | 'warning' | 'error' {
  if (['ONLINE', 'LOCKED', 'STREAMING', 'CONNECTED'].includes(s)) return 'online';
  if (['SEARCHING', 'STANDBY', 'INITIALIZING'].includes(s)) return 'warning';
  if (['OFFLINE', 'DISCONNECTED', 'ERROR'].includes(s)) return 'offline';
  return 'offline';
}

function sourceTypeColor(t?: string): string {
  if (t === 'REAL FOOTAGE') return 'var(--emerald)';
  if (t === 'DEVELOPMENT TEST FOOTAGE') return 'var(--amber)';
  if (t === 'USER_PROVIDED') return 'var(--olive-light)';
  return 'var(--text-muted)';
}

const LiveIntelligence: React.FC = () => {
  const [status, setStatus] = useState<MonitoringStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [streamError, setStreamError] = useState(false);
  const [streamKey, setStreamKey] = useState(Date.now());
  const activeRef = useRef<boolean>(false);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await getMonitoringStatus();
      setStatus(data);
      activeRef.current = data.is_active;
      if (data.is_active && streamError) {
        setStreamError(false);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Cannot reach backend.');
    } finally {
      setLoading(false);
    }
  }, [streamError]);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(() => {
      fetchStatus();
    }, activeRef.current ? 2000 : 5000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const handleStart = async () => {
    setActionLoading(true);
    setActionError(null);
    setStreamError(false);
    try {
      const res = await startMonitoring();
      setStatus(res.status);
      setStreamKey(Date.now());
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : 'Failed to start monitoring.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleStop = async () => {
    setActionLoading(true);
    setActionError(null);
    try {
      const res = await stopMonitoring();
      setStatus(res.status);
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : 'Failed to stop monitoring.');
    } finally {
      setActionLoading(false);
    }
  };

  const streamUrl = `${API_BASE_URL}/api/video/stream?t=${streamKey}`;
  const counts = status?.live_counts || { car: 0, motorcycle: 0, bus: 0, truck: 0, total: 0 };
  const gps = status?.live_gps || { latitude: 19.1197, longitude: 72.9050, speed: 0 };
  const sourceType = status?.video_validation?.source_type;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Header title="Live Intelligence" subtitle="Edge AI video stream & real-time YOLO vehicle detection" />
      <div className="page-body">
        {loading && !status && <LoadingSpinner message="Fetching monitoring state from backend..." />}
        {error && <ErrorAlert message={error} onRetry={fetchStatus} />}

        {status && (
          <>
            {(status.latest_error || status.edge_ai_status === 'ERROR') && (
              <div style={{ marginBottom: '1rem' }}>
                <ErrorAlert message={status.latest_error || 'Edge AI processor encountered an error.'} onRetry={fetchStatus} />
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '1rem' }}>
              {/* ========================= LEFT: VIDEO + CONTROLS + VEHICLE COUNTS ========================= */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {/* Live Camera Feed Card */}
                <div className="card">
                  <div className="card-header">
                    <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <Camera size={14} style={{ color: 'var(--olive-light)' }} />
                      <span>LIVE CAMERA FEED</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <span style={{
                        fontSize: '0.6rem', color: sourceTypeColor(sourceType), fontWeight: 600, letterSpacing: '0.04em'
                      }}>
                        {sourceType || 'NO VIDEO'}
                      </span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.65rem', color: status.camera_status === 'STREAMING' ? 'var(--emerald)' : 'var(--text-muted)' }}>
                        <StatusDot status={statusDotVariant(status.camera_status)} />
                        {status.camera_status}
                      </span>
                    </div>
                  </div>

                  <div className="video-viewport" style={{ background: '#0f120d', position: 'relative', aspectRatio: '16/9', overflow: 'hidden', borderRadius: '0.5rem' }}>
                    {status.is_active && !streamError ? (
                      <>
                        <img
                          src={streamUrl}
                          alt="Live YOLO Detection Stream"
                          style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
                          onError={() => setStreamError(true)}
                        />
                        <div style={{
                          position: 'absolute', top: '0.75rem', left: '0.75rem',
                          display: 'flex', alignItems: 'center', gap: '0.35rem',
                          background: 'rgba(26, 31, 22, 0.85)', backdropFilter: 'blur(4px)',
                          border: '1px solid rgba(196, 92, 92, 0.5)',
                          padding: '0.25rem 0.6rem', borderRadius: '9999px',
                          fontSize: '0.6rem', fontWeight: 700, color: '#c45c5c', letterSpacing: '0.05em'
                        }}>
                          <span style={{
                            width: '6px', height: '6px', borderRadius: '50%',
                            background: '#c45c5c', boxShadow: '0 0 8px #c45c5c', display: 'inline-block'
                          }} />
                          LIVE
                        </div>
                      </>
                    ) : status.is_active && streamError ? (
                      <div className="video-offline-overlay">
                        <AlertTriangle size={32} style={{ color: 'var(--amber)' }} />
                        <p>
                          Connecting to video stream...<br />
                          <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                            YOLO is processing frames. Retrying stream...
                          </span>
                        </p>
                        <button
                          className="btn btn-ghost"
                          onClick={() => { setStreamError(false); setStreamKey(Date.now()); }}
                          style={{ fontSize: '0.65rem', padding: '0.3rem 0.6rem' }}
                        >
                          Retry Stream
                        </button>
                      </div>
                    ) : (
                      <div className="video-offline-overlay">
                        <VideoOff size={32} style={{ opacity: 0.3 }} />
                        <p>
                          Edge AI pipeline is <strong style={{ color: 'var(--rose)' }}>offline</strong>.<br />
                          Click <strong>Start Monitoring</strong> to activate camera feed & YOLO inference.
                        </p>
                      </div>
                    )}
                  </div>

                  <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
                    <button
                      className="btn btn-primary"
                      onClick={handleStart}
                      disabled={actionLoading || status.is_active}
                      style={{ flex: 1 }}
                      id="btn-start-monitoring"
                    >
                      <Play size={13} />
                      Start Monitoring
                    </button>
                    <button
                      className="btn btn-danger"
                      onClick={handleStop}
                      disabled={actionLoading || !status.is_active}
                      style={{ flex: 1 }}
                      id="btn-stop-monitoring"
                    >
                      <Square size={13} />
                      Stop Monitoring
                    </button>
                  </div>
                  {actionError && (
                    <div style={{ marginTop: '0.75rem' }}>
                      <ErrorAlert message={actionError} />
                    </div>
                  )}
                </div>

                {/* Current Frame Vehicle Detections */}
                <div className="card">
                  <div className="card-header">
                    <div className="card-title">Current Frame Vehicle Detections</div>
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace' }}>
                      {status.is_active ? `Total: ${counts.total}` : 'Offline'}
                    </span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.5rem' }}>
                    <div style={{ background: 'var(--bg-surface)', padding: '0.6rem', borderRadius: '0.5rem', border: '1px solid var(--border-default)', textAlign: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.25rem', color: 'var(--blue)', fontSize: '0.65rem', marginBottom: '0.25rem' }}>
                        <Car size={12} /> Cars
                      </div>
                      <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace' }}>
                        {status.is_active ? counts.car : '--'}
                      </div>
                    </div>
                    <div style={{ background: 'var(--bg-surface)', padding: '0.6rem', borderRadius: '0.5rem', border: '1px solid var(--border-default)', textAlign: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.25rem', color: 'var(--olive-light)', fontSize: '0.65rem', marginBottom: '0.25rem' }}>
                        <Bike size={12} /> Bikes
                      </div>
                      <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace' }}>
                        {status.is_active ? counts.motorcycle : '--'}
                      </div>
                    </div>
                    <div style={{ background: 'var(--bg-surface)', padding: '0.6rem', borderRadius: '0.5rem', border: '1px solid var(--border-default)', textAlign: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.25rem', color: 'var(--amber)', fontSize: '0.65rem', marginBottom: '0.25rem' }}>
                        <BusIcon size={12} /> Buses
                      </div>
                      <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace' }}>
                        {status.is_active ? counts.bus : '--'}
                      </div>
                    </div>
                    <div style={{ background: 'var(--bg-surface)', padding: '0.6rem', borderRadius: '0.5rem', border: '1px solid var(--border-default)', textAlign: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.25rem', color: 'var(--rose)', fontSize: '0.65rem', marginBottom: '0.25rem' }}>
                        <Truck size={12} /> Trucks
                      </div>
                      <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace' }}>
                        {status.is_active ? counts.truck : '--'}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Road Hazard Intelligence Card */}
                <div className="card">
                  <div className="card-header">
                    <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <AlertTriangle size={13} style={{ color: 'var(--rose)' }} />
                      <span>Road Hazard Intelligence (Pothole AI)</span>
                    </div>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.65rem', color: status.hazard_model_status === 'ONLINE' ? 'var(--emerald)' : 'var(--text-muted)' }}>
                      <StatusDot status={statusDotVariant(status.hazard_model_status || 'STANDBY')} />
                      {status.hazard_model_status || 'STANDBY'}
                    </span>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem', marginBottom: '0.75rem' }}>
                    <div style={{ background: 'var(--bg-surface)', padding: '0.5rem', borderRadius: '0.5rem', border: '1px solid var(--border-default)', textAlign: 'center' }}>
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.6rem', marginBottom: '0.25rem' }}>Live In Frame</div>
                      <div style={{ fontSize: '1.1rem', fontWeight: 600, color: (status.latest_hazard_detections?.length || 0) > 0 ? 'var(--rose)' : 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace' }}>
                        {status.is_active ? (status.latest_hazard_detections?.length || 0) : '--'}
                      </div>
                    </div>
                    <div style={{ background: 'var(--bg-surface)', padding: '0.5rem', borderRadius: '0.5rem', border: '1px solid var(--border-default)', textAlign: 'center' }}>
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.6rem', marginBottom: '0.25rem' }}>Confirmed Events</div>
                      <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--amber)', fontFamily: 'JetBrains Mono, monospace' }}>
                        {status.confirmed_hazard_count ?? 0}
                      </div>
                    </div>
                    <div style={{ background: 'var(--bg-surface)', padding: '0.5rem', borderRadius: '0.5rem', border: '1px solid var(--border-default)', textAlign: 'center' }}>
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.6rem', marginBottom: '0.25rem' }}>Hazard AI FPS</div>
                      <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--olive-light)', fontFamily: 'JetBrains Mono, monospace' }}>
                        {status.is_active && (status.hazard_fps || 0) > 0 ? `${(status.hazard_fps || 0).toFixed(1)}` : status.is_active ? 'measuring...' : '--'}
                      </div>
                    </div>
                  </div>

                  {status.last_hazard ? (
                    <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '0.5rem', padding: '0.5rem 0.75rem', fontSize: '0.7rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                        <span style={{ fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                          <span style={{ color: 'var(--rose)' }}>●</span> Latest: {status.last_hazard.event_type}
                        </span>
                        <span className={`badge badge-${status.last_hazard.priority.toLowerCase()}`} style={{ fontSize: '0.55rem' }}>
                          {status.last_hazard.priority}
                        </span>
                      </div>
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.6rem', display: 'flex', justifyContent: 'space-between' }}>
                        <span>Confidence: {Math.round(status.last_hazard.confidence * 100)}%</span>
                        <span>GPS: {status.last_hazard.latitude.toFixed(4)}, {status.last_hazard.longitude.toFixed(4)}</span>
                      </div>
                    </div>
                  ) : (
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.65rem', textAlign: 'center', padding: '0.3rem 0' }}>
                      {status.is_active ? 'Temporal confirmation active. Waiting for road defect triggers.' : 'Hazard detection offline.'}
                    </div>
                  )}
                </div>
              </div>

              {/* ========================= RIGHT: SYSTEM TELEMETRY ========================= */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div className="card">
                  <div className="card-header" style={{ marginBottom: '0.75rem' }}>
                    <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <MonitorPlay size={13} style={{ color: 'var(--olive-light)' }} />
                      <span>System Telemetry</span>
                    </div>
                    <span className={`badge ${status.is_active ? 'badge-active' : 'badge-resolved'}`}>
                      {status.is_active ? 'ACTIVE' : 'STANDBY'}
                    </span>
                  </div>

                  {/* Component status grid */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.75rem' }}>
                    <div style={compStyle}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.65rem' }}>
                        <Cpu size={11} style={{ color: 'var(--olive-light)' }} />
                        Vehicle AI
                      </div>
                      <div style={{ fontSize: '0.7rem', fontWeight: 600, color: statusDotVariant(status.edge_ai_status) === 'online' ? 'var(--emerald)' : 'var(--text-muted)' }}>
                        <StatusDot status={statusDotVariant(status.edge_ai_status)} /> {status.edge_ai_status}
                      </div>
                    </div>
                    <div style={compStyle}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.65rem' }}>
                        <AlertTriangle size={11} style={{ color: 'var(--rose)' }} />
                        Hazard AI
                      </div>
                      <div style={{ fontSize: '0.7rem', fontWeight: 600, color: status.hazard_model_status === 'ONLINE' ? 'var(--emerald)' : 'var(--amber)' }}>
                        <StatusDot status={status.hazard_model_status === 'ONLINE' ? 'online' : 'warning'} /> {status.hazard_model_status === 'ONLINE' ? 'ONLINE' : 'DEGRADED'}
                      </div>
                    </div>
                    <div style={compStyle}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.65rem' }}>
                        <Camera size={11} style={{ color: 'var(--olive-light)' }} />
                        Camera Feed
                      </div>
                      <div style={{ fontSize: '0.7rem', fontWeight: 600, color: statusDotVariant(status.camera_status) === 'online' ? 'var(--emerald)' : 'var(--text-muted)' }}>
                        <StatusDot status={statusDotVariant(status.camera_status)} /> {status.camera_status}
                      </div>
                    </div>
                    <div style={compStyle}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.65rem' }}>
                        <Navigation size={11} style={{ color: 'var(--olive-light)' }} />
                        GPS Receiver
                      </div>
                      <div style={{ fontSize: '0.7rem', fontWeight: 600, color: statusDotVariant(status.gps_status) === 'online' ? 'var(--emerald)' : 'var(--text-muted)' }}>
                        <StatusDot status={statusDotVariant(status.gps_status)} /> {status.gps_status}
                      </div>
                    </div>
                  </div>

                  {/* Key-Value info rows */}
                  <div>
                    <div className="info-row">
                      <span className="info-row-label">Bus ID</span>
                      <span className="info-row-value">{status.bus_code}</span>
                    </div>
                    <div className="info-row">
                      <span className="info-row-label">Pipeline Uptime</span>
                      <span className="info-row-value">{status.uptime_seconds != null ? `${status.uptime_seconds}s` : '--'}</span>
                    </div>
                    <div className="info-row">
                      <span className="info-row-label">Device</span>
                      <span className="info-row-value" style={{ fontWeight: 600, color: status.device_name?.includes('CUDA') ? 'var(--emerald)' : 'var(--olive-light)' }}>
                        {status.device_name || 'CPU'}
                      </span>
                    </div>
                    <div className="info-row">
                      <span className="info-row-label">Processing Resolution</span>
                      <span className="info-row-value">{status.processing_resolution || '1280x720 @ AI 480'}</span>
                    </div>
                  </div>
                </div>

                {/* FPS Telemetry Card */}
                <div className="card">
                  <div className="card-header" style={{ marginBottom: '0.75rem' }}>
                    <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <Gauge size={13} style={{ color: 'var(--olive-light)' }} />
                      <span>FPS Telemetry</span>
                    </div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem' }}>
                    <div style={fpsTile}>
                      <div style={fpsLabel}>Video Stream</div>
                      <div style={fpsValue}>{status.is_active ? `${(status.fps || 0).toFixed(1)} FPS` : '--'}</div>
                    </div>
                    <div style={fpsTile}>
                      <div style={fpsLabel}>Vehicle AI</div>
                      <div style={fpsValue}>{status.is_active ? `${(status.vehicle_fps || 0).toFixed(1)} FPS` : '--'}</div>
                    </div>
                    <div style={fpsTile}>
                      <div style={fpsLabel}>Hazard AI</div>
                      <div style={fpsValue}>{status.is_active ? `${(status.hazard_fps || 0).toFixed(1)} FPS` : '--'}</div>
                    </div>
                  </div>
                  <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', marginTop: '0.5rem', lineHeight: 1.5 }}>
                    Video Stream = measured MJPEG playback rate. Vehicle/Hazard AI = measured YOLO inference rate.
                  </div>
                </div>

                {/* GPS + Source Card */}
                <div className="card">
                  <div className="card-header" style={{ marginBottom: '0.75rem' }}>
                    <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <Navigation size={13} style={{ color: 'var(--olive-light)' }} />
                      <span>GPS & Video Source</span>
                    </div>
                  </div>
                  <div className="info-row">
                    <span className="info-row-label">GPS Mode</span>
                    <span className="info-row-value" style={{ color: 'var(--amber)', fontSize: '0.6rem', fontWeight: 600 }}>
                      SIMULATED MUMBAI ROAD ROUTE
                    </span>
                  </div>
                  <div className="info-row">
                    <span className="info-row-label">Coordinates</span>
                    <span className="info-row-value">
                      {gps.latitude.toFixed(5)}, {gps.longitude.toFixed(5)}
                    </span>
                  </div>
                  <div className="info-row">
                    <span className="info-row-label">Bus Speed</span>
                    <span className="info-row-value">{gps.speed.toFixed(1)} km/h</span>
                  </div>
                  <div className="info-row">
                    <span className="info-row-label">Video Source</span>
                    <span className="info-row-value" style={{ fontSize: '0.6rem', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={status.video_source || ''}>
                      {status.video_source ? status.video_source.split(/[\\/]/).pop() : '--'}
                    </span>
                  </div>
                  <div className="info-row">
                    <span className="info-row-label">Source Classification</span>
                    <span className="info-row-value" style={{ fontSize: '0.6rem', fontWeight: 600, color: sourceTypeColor(sourceType) }}>
                      {sourceType || '--'}
                    </span>
                  </div>
                </div>

                {/* Status description */}
                <div style={{
                  background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '0.5rem',
                  padding: '0.75rem 1rem', fontSize: '0.7rem', color: 'var(--text-muted)', lineHeight: 1.5,
                  display: 'flex', gap: '0.5rem', alignItems: 'flex-start'
                }}>
                  <AlertCircle size={13} style={{ flexShrink: 0, marginTop: 1, color: 'var(--olive-light)' }} />
                  <span>{status.message}</span>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

const compStyle: React.CSSProperties = {
  background: 'var(--bg-surface)', padding: '0.5rem 0.6rem',
  borderRadius: '0.5rem', border: '1px solid var(--border-default)',
  display: 'flex', flexDirection: 'column', gap: '0.3rem'
};

const fpsTile: React.CSSProperties = {
  background: 'var(--bg-surface)', padding: '0.5rem',
  borderRadius: '0.5rem', border: '1px solid var(--border-default)',
  textAlign: 'center'
};

const fpsLabel: React.CSSProperties = {
  color: 'var(--text-muted)', fontSize: '0.55rem', marginBottom: '0.25rem',
  textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600
};

const fpsValue: React.CSSProperties = {
  fontSize: '0.95rem', fontWeight: 600, color: 'var(--olive-light)',
  fontFamily: 'JetBrains Mono, monospace'
};

export default LiveIntelligence;
