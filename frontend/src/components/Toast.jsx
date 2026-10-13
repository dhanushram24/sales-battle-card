import React from 'react';

export function Toast({ toasts = [] }) {
  if (!toasts || toasts.length === 0) return null;

  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t.id} className={`toast ${t.type || 'success'}`}>
          <span>{t.type === 'error' ? '⚠️' : '✓'}</span>
          <span>{t.message}</span>
        </div>
      ))}
    </div>
  );
}
