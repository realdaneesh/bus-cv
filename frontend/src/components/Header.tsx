import React, { useState, useEffect } from 'react';
import { Wifi, WifiOff, Clock } from 'lucide-react';
import { getHealth } from '../services/api';
import { formatISTTimeOnly } from '../utils/date';

interface HeaderProps {
  title: string;
  subtitle?: string;
}

const Header: React.FC<HeaderProps> = ({ title, subtitle }) => {
  const [connected, setConnected] = useState<boolean | null>(null);
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const checkHealth = async () => {
      try {
        await getHealth();
        setConnected(true);
      } catch {
        setConnected(false);
      }
    };
    checkHealth();
    const healthInterval = setInterval(checkHealth, 15000);
    return () => clearInterval(healthInterval);
  }, []);

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="page-header">
      <div className="page-header-left">
        <div className="page-title">{title}</div>
        {subtitle && <div className="page-subtitle">{subtitle}</div>}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
        {/* IST Clock */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.7rem', color: 'var(--text-secondary)', fontFamily: 'JetBrains Mono, monospace' }}>
          <Clock size={12} style={{ color: 'var(--olive-light)' }} />
          <span>{formatISTTimeOnly(now)}</span>
        </div>

        {/* Backend Connection */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.65rem' }}>
          {connected === null ? (
            <span style={{ color: 'var(--text-muted)' }}>Connecting...</span>
          ) : connected ? (
            <>
              <Wifi size={12} style={{ color: 'var(--emerald)' }} />
              <span style={{ color: 'var(--emerald)' }}>Online</span>
            </>
          ) : (
            <>
              <WifiOff size={12} style={{ color: 'var(--rose)' }} />
              <span style={{ color: 'var(--rose)' }}>Offline</span>
            </>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;
