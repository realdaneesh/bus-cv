import React, { useEffect, useState, useCallback } from 'react';
import { RefreshCw, Cpu, Camera, Navigation, Activity, ChevronRight } from 'lucide-react';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';
import { StatusBadge, PriorityBadge, ProvenanceBadge, StatusDot } from '../components/Badges';
import { getDashboard, getMonitoringStatus } from '../services/api';
import { formatIST } from '../utils/date';
import type { DashboardStats, MonitoringStatus } from '../types';

const CommandCenter: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [monitoring, setMonitoring] = useState<MonitoringStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [, setLastRefreshed] = useState<Date | null>(null);

  const load = useCallback(async () => {
    try {
      const [dashboard, mon] = await Promise.all([
        getDashboard(),
        getMonitoringStatus().catch(() => null),
      ]);
      setStats(dashboard);
      setMonitoring(mon);
      setLastRefreshed(new Date());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load dashboard data from backend.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, [load]);

  function dotVariant(s?: string): 'online' | 'offline' | 'warning' | 'error' {
    if (!s) return 'offline';
    if (['ONLINE', 'LOCKED', 'STREAMING', 'CONNECTED'].includes(s)) return 'online';
    if (['SEARCHING', 'STANDBY', 'INITIALIZING'].includes(s)) return 'warning';
    return 'offline';
  }

  const activeEvents = stats?.recent_events.filter(e => e.status === 'ACTIVE') || [];
  const highPriorityCount = stats?.issues_by_priority?.HIGH || 0;
  const criticalPriorityCount = stats?.issues_by_priority?.CRITICAL || 0;
  const totalHighRisk = highPriorityCount + criticalPriorityCount;

  return (
    <div className="page-body">
      {loading && !stats && <LoadingSpinner message="Fetching dashboard data..." />}
      {error && <ErrorAlert message={error} onRetry={load} />}

      {stats && (
        <>
          {/* Today's Overview Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
            <div>
              <h1 className="page-title dashboard-greeting">Today's Overview</h1>
              <p className="page-subtitle">
                {monitoring?.is_active
                  ? `Monitoring active on ${monitoring.device_name || 'CPU'}`
                  : 'System in standby mode'}
              </p>
            </div>
            <div className="dashboard-alerts">
              <div className="alert-badge high-risk">
                <span className="alert-badge-count">{totalHighRisk}</span>
                <span>High-Risk Alerts</span>
              </div>
              <div className="alert-badge new-results">
                <span className="alert-badge-count">{stats.total_events}</span>
                <span>Total Events</span>
              </div>
              <div className="alert-badge today">
                <span className="alert-badge-count">{stats.active_issues}</span>
                <span>Active Issues</span>
              </div>
            </div>
          </div>

          {/* Main Dashboard Grid */}
          <div className="dashboard-row dashboard-row-3">
            {/* Quick Access Panel */}
            <div className="quick-access">
              <div className="quick-access-title">Quick Access</div>
              <div className="quick-access-item">
                <span className="prefix">[+]</span>
                <span>New Event</span>
              </div>
              <div className="quick-access-item">
                <span className="prefix">{'[>]'}</span>
                <span>All Events</span>
              </div>
              <div className="quick-access-item">
                <span className="prefix">{'[>]'}</span>
                <span>View Map</span>
              </div>
              <div className="quick-access-item">
                <span className="prefix">{'[>]'}</span>
                <span>View Issues</span>
              </div>
            </div>

            {/* Active Events / Ready for Review */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">Active Events</div>
                <span className="stat-value" style={{ fontSize: '1.5rem' }}>
                  {activeEvents.length.toString().padStart(2, '0')}
                </span>
              </div>
              {activeEvents.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', padding: '0.5rem 0' }}>
                  No active events
                </div>
              ) : (
                activeEvents.slice(0, 5).map((ev) => (
                  <div key={ev.id} style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.5rem 0',
                    borderBottom: '1px solid rgba(61, 74, 50, 0.3)',
                    fontSize: '0.75rem'
                  }}>
                    <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                      {ev.event_type}
                    </span>
                    <span style={{ color: 'var(--olive-light)', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.7rem' }}>
                      [VIEW <ChevronRight size={10} style={{ display: 'inline' }} />]
                    </span>
                  </div>
                ))
              )}
            </div>

            {/* High Priority Issues */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">High Priority Issues</div>
                <span className="stat-value" style={{ fontSize: '1.5rem' }}>
                  {totalHighRisk.toString().padStart(2, '0')}
                </span>
              </div>
              {totalHighRisk === 0 ? (
                <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', padding: '0.5rem 0' }}>
                  No high priority issues
                </div>
              ) : (
                <>
                  {Object.entries(stats.issues_by_priority).filter(([p]) => ['HIGH', 'CRITICAL'].includes(p)).map(([priority, count]) => (
                    <div key={priority} style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.75rem',
                      padding: '0.5rem 0',
                      borderBottom: '1px solid rgba(61, 74, 50, 0.3)',
                      fontSize: '0.75rem'
                    }}>
                      <PriorityBadge priority={priority} />
                      <span style={{ color: 'var(--text-muted)' }}>{count} issues</span>
                    </div>
                  ))}
                </>
              )}
            </div>

            {/* Detection Timeline Chart */}
            <div className="chart-container">
              <div className="chart-header">
                <div className="card-title">Detection Timeline</div>
                <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Last 7 Days</span>
              </div>
              <div className="chart-bars">
                {[35, 65, 45, 80, 55, 70, 40].map((height, i) => (
                  <div key={i} className="chart-bar" style={{ height: `${height}%` }} />
                ))}
              </div>
              <div className="chart-labels">
                <span className="chart-label">Mon</span>
                <span className="chart-label">Tue</span>
                <span className="chart-label">Wed</span>
                <span className="chart-label">Thu</span>
                <span className="chart-label">Fri</span>
                <span className="chart-label">Sat</span>
                <span className="chart-label">Sun</span>
              </div>
            </div>
          </div>

          {/* Second Row: Schedule + Event Density + Results */}
          <div className="dashboard-row dashboard-row-2">
            {/* Monitoring Timeline / Today's Schedule */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">Monitoring Timeline</div>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {['09:00', '10:30', '12:00', '02:15', '03:30', '04:45'].map((time, i) => (
                  <div key={i} className={`time-slot ${i < 3 ? 'active' : 'inactive'}`}>
                    {time}
                    <span className="ampm">{i < 2 ? 'am' : i === 2 ? 'am' : 'pm'}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Event Density Heatmap */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">Event Density</div>
              </div>
              <div className="heatmap-grid">
                {/* Hour labels */}
                <div className="heatmap-label">6am</div>
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.2)' }} />
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.15)' }} />
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.1)' }} />
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.05)' }} />
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.2)' }} />
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.15)' }} />
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.1)' }} />

                <div className="heatmap-label">12pm</div>
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.3)' }} />
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.4)' }} />
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.25)' }} />
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.35)' }} />
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.45)' }} />
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.3)' }} />
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.2)' }} />

                <div className="heatmap-label">6pm</div>
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.5)' }} />
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.6)' }} />
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.4)' }} />
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.55)' }} />
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.7)' }} />
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.5)' }} />
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.35)' }} />

                <div className="heatmap-label">9pm</div>
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.2)' }} />
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.25)' }} />
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.15)' }} />
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.2)' }} />
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.3)' }} />
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.2)' }} />
                <div className="heatmap-cell" style={{ background: 'rgba(107, 124, 82, 0.15)' }} />
              </div>
              <div className="heatmap-legend">
                <div className="legend-item">
                  <div className="legend-swatch" style={{ background: 'rgba(107, 124, 82, 0.15)' }} />
                  <span>Low</span>
                </div>
                <div className="legend-item">
                  <div className="legend-swatch" style={{ background: 'rgba(107, 124, 82, 0.4)' }} />
                  <span>Medium</span>
                </div>
                <div className="legend-item">
                  <div className="legend-swatch" style={{ background: 'rgba(107, 124, 82, 0.7)' }} />
                  <span>High</span>
                </div>
              </div>
            </div>

            {/* Detection Results */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">Detection Results</div>
              </div>
              <div className="result-card caution">
                <span className="result-number">{stats.active_issues}</span>
                <span className="result-label" style={{ color: 'var(--amber)' }}>Caution</span>
              </div>
              <div className="result-card high-risk">
                <span className="result-number">{totalHighRisk}</span>
                <span className="result-label" style={{ color: 'var(--rose)' }}>High Risk</span>
              </div>
              <div className="result-card normal">
                <span className="result-number">{stats.resolved_issues}</span>
                <span className="result-label" style={{ color: 'var(--emerald)' }}>Normal</span>
              </div>
            </div>
          </div>

          {/* Recent Events Table */}
          <div className="card" style={{ marginTop: '1rem' }}>
            <div className="card-header">
              <div className="card-title">Recent Events</div>
              <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Last 6</span>
            </div>
            {stats.recent_events.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', padding: '1rem 0', textAlign: 'center' }}>
                No events in database yet
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Confidence</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th>Source</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.recent_events.map((ev) => (
                    <tr key={ev.id}>
                      <td style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{ev.event_type}</td>
                      <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>{(ev.confidence * 100).toFixed(0)}%</td>
                      <td><PriorityBadge priority={ev.priority} /></td>
                      <td><StatusBadge status={ev.status} /></td>
                      <td><ProvenanceBadge source={ev.source} is_demo_data={ev.is_demo_data} /></td>
                      <td style={{ fontSize: '0.65rem', fontFamily: 'JetBrains Mono, monospace' }}>{formatIST(ev.timestamp)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* System Status Bar */}
          <div className="card" style={{ marginTop: '1rem', borderLeft: `3px solid ${monitoring?.is_active ? 'var(--emerald)' : 'var(--amber)'}` }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <Activity size={16} style={{ color: monitoring?.is_active ? 'var(--emerald)' : 'var(--amber)' }} />
                <div>
                  <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.8rem' }}>
                    {monitoring?.is_active ? 'MONITORING ACTIVE' : 'MONITORING STANDBY'}
                  </div>
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                    {monitoring?.is_active
                      ? `Running on ${monitoring.device_name || 'CPU'}`
                      : 'Start monitoring in Live Feed to activate'}
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.65rem' }}>
                  <Cpu size={11} style={{ color: 'var(--olive-light)' }} />
                  <StatusDot status={dotVariant(monitoring?.edge_ai_status)} />
                  {monitoring?.edge_ai_status || 'STANDBY'}
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.65rem' }}>
                  <Camera size={11} style={{ color: 'var(--olive-light)' }} />
                  <StatusDot status={dotVariant(monitoring?.camera_status)} />
                  {monitoring?.camera_status || 'DISCONNECTED'}
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.65rem' }}>
                  <Navigation size={11} style={{ color: 'var(--olive-light)' }} />
                  <StatusDot status={dotVariant(monitoring?.gps_status)} />
                  {monitoring?.gps_status || 'LOCKED'}
                </span>
                <button className="btn btn-ghost" onClick={load} disabled={loading} style={{ fontSize: '0.65rem', padding: '0.25rem 0.5rem' }}>
                  <RefreshCw size={10} />
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default CommandCenter;
