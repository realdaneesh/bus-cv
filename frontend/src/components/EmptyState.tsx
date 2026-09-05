import React from 'react';
import type { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  message?: string;
}

const EmptyState: React.FC<EmptyStateProps> = ({ icon: Icon, title, message }) => (
  <div className="state-container">
    {Icon && (
      <div className="state-icon">
        <Icon size={36} />
      </div>
    )}
    <div className="state-title">{title}</div>
    {message && <div className="state-message">{message}</div>}
  </div>
);

export default EmptyState;
