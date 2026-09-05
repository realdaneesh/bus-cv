import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { Search, LayoutDashboard, MonitorPlay, MapPin, AlertTriangle, BarChart3 } from 'lucide-react';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/live', label: 'Live Feed', icon: MonitorPlay },
  { to: '/map', label: 'Map', icon: MapPin },
  { to: '/issues', label: 'Issues', icon: AlertTriangle },
  { to: '/traffic', label: 'Traffic', icon: BarChart3 },
];

const TopNav: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <nav className="top-nav">
      {/* Brand */}
      <div className="top-nav-brand">
        <span className="brand-title">BUS-CV</span>
      </div>

      {/* Search Bar */}
      <div className="top-nav-search">
        <Search size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
        <input
          type="text"
          placeholder="Search events, issues..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      {/* Navigation Links */}
      <div className="top-nav-links">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => `top-nav-link${isActive ? ' active' : ''}`}
          >
            <Icon size={14} />
            {label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
};

export default TopNav;
