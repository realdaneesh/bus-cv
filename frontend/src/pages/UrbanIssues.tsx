import React, { useEffect, useState, useCallback } from 'react';
import { AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react';
import Header from '../components/Header';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';
import EmptyState from '../components/EmptyState';
import { StatusBadge, PriorityBadge, ProvenanceBadge } from '../components/Badges';
import { getEvents, resolveEvent } from '../services/api';
import { formatIST } from '../utils/date';
import type { UrbanEvent } from '../types';


type FilterStatus = 'ALL' | 'ACTIVE' | 'RESOLVED' | 'INVESTIGATING';
type FilterSource = 'ALL' | 'AI_DETECTION' | 'SEED';

const UrbanIssues: React.FC = () => {
  const [events, setEvents] = useState<UrbanEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<FilterStatus>('ALL');
  const [sourceFilter, setSourceFilter] = useState<FilterSource>('ALL');
  const [resolving, setResolving] = useState<number | null>(null);
  const [resolveError, setResolveError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getEvents(statusFilter, sourceFilter);
      setEvents(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load events from backend.');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, sourceFilter]);

  useEffect(() => { load(); }, [load]);

  const handleResolve = async (id: number) => {
    setResolving(id);
    setResolveError(null);
    try {
      await resolveEvent(id);
      // Refetch so UI reflects actual DB state
      await load();
    } catch (e: unknown) {
      setResolveError(e instanceof Error ? e.message : 'Failed to resolve event.');
    } finally {
      setResolving(null);
    }
  };

  const STATUS_FILTERS: FilterStatus[] = ['ALL', 'ACTIVE', 'RESOLVED', 'INVESTIGATING'];
  const SOURCE_FILTERS: { label: string; value: FilterSource }[] = [
    { label: 'All Sources', value: 'ALL' },
    { label: 'AI Detection', value: 'AI_DETECTION' },
    { label: 'Demo Data', value: 'SEED' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Header title="Urban Issues" subtitle="Real events from database - resolve to update backend status" />
      <div className="page-body">
        {/* Filters & Actions */}
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.25rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <div className="filter-tabs">
            {STATUS_FILTERS.map((f) => (
              <button
                key={f}
                className={`filter-tab${statusFilter === f ? ' active' : ''}`}
                onClick={() => setStatusFilter(f)}
              >
                {f}
              </button>
            ))}
          </div>
          <div className="filter-tabs">
            {SOURCE_FILTERS.map(({ label, value }) => (
              <button
                key={value}
                className={`filter-tab${sourceFilter === value ? ' active' : ''}`}
                onClick={() => setSourceFilter(value)}
              >
                {label}
              </button>
            ))}
          </div>
          <button className="btn btn-ghost" onClick={load} disabled={loading} style={{ marginLeft: 'auto' }}>
            <RefreshCw size={11} /> Refresh
          </button>
        </div>

        {resolveError && (
          <div style={{ marginBottom: '1rem' }}>
            <ErrorAlert message={resolveError} />
          </div>
        )}

        {loading && !events.length && <LoadingSpinner message="Fetching events from backend..." />}
        {error && <ErrorAlert message={error} onRetry={load} />}

        {!loading && !error && events.length === 0 && (
          <EmptyState
            icon={AlertTriangle}
            title="No urban events found"
            message={`No events match the selected filters (Status: ${statusFilter}, Source: ${sourceFilter}). Events appear here when detected by the AI pipeline.`}
          />
        )}

        {events.length > 0 && (
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: '0.875rem 1.25rem', borderBottom: '1px solid var(--border-default)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div className="card-title">{events.length} Events</div>
              <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>
                Resolve button calls PATCH /api/events/{'{id}'}/resolve
              </span>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Type</th>
                    <th>Confidence</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th>Source</th>
                    <th>Location</th>
                    <th>Time</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((ev) => (
                    <tr key={ev.id}>
                      <td style={{ color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.65rem' }}>#{ev.id}</td>
                      <td style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{ev.event_type}</td>
                      <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                        {(ev.confidence * 100).toFixed(0)}%
                      </td>
                      <td><PriorityBadge priority={ev.priority} /></td>
                      <td><StatusBadge status={ev.status} /></td>
                      <td><ProvenanceBadge source={ev.source} is_demo_data={ev.is_demo_data} /></td>
                      <td style={{ fontSize: '0.6rem', fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-muted)' }}>
                        {ev.latitude.toFixed(4)}, {ev.longitude.toFixed(4)}
                      </td>
                      <td style={{ fontSize: '0.6rem', whiteSpace: 'nowrap', fontFamily: 'JetBrains Mono, monospace' }}>
                        {formatIST(ev.timestamp)}
                      </td>

                      <td>
                        {ev.status !== 'RESOLVED' ? (
                          <button
                            className="btn btn-resolve"
                            onClick={() => handleResolve(ev.id)}
                            disabled={resolving === ev.id}
                            id={`btn-resolve-${ev.id}`}
                          >
                            <CheckCircle size={10} />
                            {resolving === ev.id ? 'Updating...' : 'Resolve'}
                          </button>
                        ) : (
                          <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>Closed</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default UrbanIssues;
