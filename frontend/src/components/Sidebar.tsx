import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  MonitorPlay,
  MapPin,
  AlertTriangle,
  BarChart3,
  Bus,
} from 'lucide-react';

const NAV_ITEMS = [
  { to: '/', label: 'Command Center', icon: LayoutDashboard, end: true },
  { to: '/live', label: 'Live Intelligence', icon: MonitorPlay },
  { to: '/map', label: 'Urban Map', icon: MapPin },
  { to: '/issues', label: 'Urban Issues', icon: AlertTriangle },
  { to: '/traffic', label: 'Traffic Intelligence', icon: BarChart3 },
];

const Sidebar: React.FC = () => {
  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar-brand">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Bus size={18} style={{ color: 'var(--cyan)' }} />
          <span className="brand-title">BUS-CV</span>
        </div>
        <div className="brand-subtitle">Mobile Urban Intelligence</div>
        <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', marginTop: '0.25rem', opacity: 0.75 }}>
          SIH Prototype · Phase 4
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        <div className="nav-section-label">System</div>
        <div style={{ padding: '0.5rem 0.875rem', marginBottom: '0.5rem', fontSize: '0.68rem', color: 'var(--text-muted)', lineHeight: 1.5, background: 'rgba(0, 212, 232, 0.04)', borderRadius: '0.25rem', border: '1px solid rgba(0, 212, 232, 0.15)' }}>
          <div style={{ fontWeight: 600, color: 'var(--cyan)', marginBottom: '0.25rem' }}>Stack</div>
          Real YOLO11n (vehicle) + YOLOv8s (hazard) inference · MJPEG stream · FastAPI · SQLite · React + Leaflet
        </div>
        <div className="nav-section-label">Navigation</div>
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
          >
            <Icon size={15} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer system state */}
      <div style={{
        padding: '0.875rem 1.25rem',
        borderTop: '1px solid var(--border-default)',
        fontSize: '0.65rem',
        color: 'var(--text-muted)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', marginBottom: '0.25rem' }}>
          <span className="status-dot online" />
          <span>BUS_01 · ACTIVE</span>
        </div>
        <div style={{ fontFamily: 'JetBrains Mono, monospace', opacity: 0.6 }}>
          Phase 1 · Foundation
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
