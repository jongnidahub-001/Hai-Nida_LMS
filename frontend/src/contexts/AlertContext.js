import React, { createContext, useContext, useState, useCallback, useRef } from 'react';

const AlertContext = createContext(null);

export const useAlert = () => {
  const context = useContext(AlertContext);
  if (!context) {
    throw new Error('useAlert must be used within an AlertProvider');
  }
  return context;
};

const confirmConfig = {
  icon: 'fa-question-circle',
  iconColor: '#3e8ed0',
  borderColor: '#3e8ed0',
  bgLight: '#f0f7ff'
};

function ConfirmModal({ confirm, onConfirm, onCancel }) {
  if (!confirm) return null;

  const { icon, iconColor, borderColor, bgLight } = confirmConfig;
  const { message, title = 'Confirm', confirmText = 'OK', cancelText = 'Cancel', type = 'warning' } = confirm;

  const dangerStyle = type === 'danger' ? {
    iconColor: '#f14668',
    borderColor: '#f14668',
    bgLight: '#fff5f5'
  } : {};

  const finalConfig = { ...confirmConfig, ...dangerStyle };

  return (
    <div 
      className="modal is-active" 
      style={{ animation: 'fadeIn 0.2s ease-out', zIndex: 9999 }}
    >
      <div 
        className="modal-background" 
        onClick={onCancel}
        style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}
      />
      <div 
        className="modal-content"
        style={{ margin: '1.5rem', maxWidth: '420px', animation: 'slideUp 0.25s ease-out' }}
      >
        <div
          style={{
            backgroundColor: 'white',
            borderRadius: '12px',
            padding: '24px',
            boxShadow: '0 10px 40px rgba(0,0,0,0.15), 0 0 0 1px rgba(0,0,0,0.05)',
            borderLeft: `4px solid ${finalConfig.borderColor}`
          }}
        >
          <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
            <div
              style={{
                width: '48px',
                height: '48px',
                borderRadius: '50%',
                backgroundColor: finalConfig.bgLight,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0
              }}
            >
              <i
                className={`fas ${finalConfig.icon}`}
                style={{ fontSize: '24px', color: finalConfig.iconColor }}
              />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <p
                className="has-text-weight-bold"
                style={{ fontSize: '1.1rem', marginBottom: '8px', color: '#363636' }}
              >
                {title}
              </p>
              <p
                style={{
                  fontSize: '0.95rem',
                  lineHeight: 1.5,
                  color: '#4a4a4a',
                  marginBottom: '20px'
                }}
              >
                {message}
              </p>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  className="button"
                  onClick={onCancel}
                  style={{
                    backgroundColor: '#f5f5f5',
                    borderColor: '#dbdbdb',
                    color: '#363636',
                    fontWeight: 600
                  }}
                >
                  {cancelText}
                </button>
                <button
                  className="button"
                  onClick={onConfirm}
                  style={{
                    backgroundColor: type === 'danger' ? '#f14668' : 'var(--primary-yellow)',
                    borderColor: type === 'danger' ? '#f14668' : 'var(--primary-yellow)',
                    color: type === 'danger' ? 'white' : 'var(--primary-black)',
                    fontWeight: 600
                  }}
                >
                  {confirmText}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

const typeConfig = {
  success: {
    icon: 'fa-check-circle',
    iconColor: '#48c774',
    borderColor: '#48c774',
    bgLight: '#f5fdf8'
  },
  error: {
    icon: 'fa-exclamation-circle',
    iconColor: '#f14668',
    borderColor: '#f14668',
    bgLight: '#fff5f5'
  },
  warning: {
    icon: 'fa-exclamation-triangle',
    iconColor: '#ffdd57',
    borderColor: '#ffdd57',
    bgLight: '#fffbeb'
  },
  info: {
    icon: 'fa-info-circle',
    iconColor: '#3e8ed0',
    borderColor: '#3e8ed0',
    bgLight: '#f0f7ff'
  }
};

function AlertModal({ alert, onClose }) {
  if (!alert) return null;

  const config = typeConfig[alert.type] || typeConfig.info;
  const { icon, iconColor, borderColor, bgLight } = config;

  return (
    <div 
      className="modal is-active" 
      style={{ 
        animation: 'fadeIn 0.2s ease-out',
        zIndex: 9999 
      }}
    >
      <div 
        className="modal-background" 
        onClick={onClose}
        style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}
      />
      <div 
        className="modal-content"
        style={{
          margin: '1.5rem',
          maxWidth: '420px',
          animation: 'slideUp 0.25s ease-out'
        }}
      >
        <div
          style={{
            backgroundColor: 'white',
            borderRadius: '12px',
            padding: '24px',
            boxShadow: '0 10px 40px rgba(0,0,0,0.15), 0 0 0 1px rgba(0,0,0,0.05)',
            borderLeft: `4px solid ${borderColor}`
          }}
        >
          <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
            <div
              style={{
                width: '48px',
                height: '48px',
                borderRadius: '50%',
                backgroundColor: bgLight,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0
              }}
            >
              <i
                className={`fas ${icon}`}
                style={{
                  fontSize: '24px',
                  color: iconColor
                }}
              />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              {alert.title && (
                <p
                  className="has-text-weight-bold"
                  style={{
                    fontSize: '1.1rem',
                    marginBottom: '8px',
                    color: '#363636'
                  }}
                >
                  {alert.title}
                </p>
              )}
              <p
                style={{
                  fontSize: '0.95rem',
                  lineHeight: 1.5,
                  color: '#4a4a4a',
                  marginBottom: alert.title ? '16px' : '20px'
                }}
              >
                {alert.message}
              </p>
              <button
                className="button"
                onClick={onClose}
                style={{
                  backgroundColor: 'var(--primary-yellow)',
                  borderColor: 'var(--primary-yellow)',
                  color: 'var(--primary-black)',
                  fontWeight: 600
                }}
              >
                OK
              </button>
            </div>
          </div>
        </div>
      </div>
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}

export const AlertProvider = ({ children }) => {
  const [alert, setAlert] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const confirmResolveRef = useRef(null);

  const showConfirm = useCallback((message, options = {}) => {
    return new Promise((resolve) => {
      confirmResolveRef.current = resolve;
      setConfirm({
        message,
        title: options.title || 'Confirm',
        confirmText: options.confirmText || 'OK',
        cancelText: options.cancelText || 'Cancel',
        type: options.type || 'info'
      });
    });
  }, []);

  const handleConfirm = useCallback(() => {
    if (confirmResolveRef.current) confirmResolveRef.current(true);
    confirmResolveRef.current = null;
    setConfirm(null);
  }, []);

  const handleCancel = useCallback(() => {
    if (confirmResolveRef.current) confirmResolveRef.current(false);
    confirmResolveRef.current = null;
    setConfirm(null);
  }, []);

  const showAlert = useCallback((message, typeOrOptions = 'info') => {
    const options = typeof typeOrOptions === 'string' 
      ? { type: typeOrOptions } 
      : typeOrOptions;
    const { type = 'info', title } = options;
    const defaultTitle = type === 'error' ? 'Error' : type === 'success' ? 'Success' : type === 'warning' ? 'Warning' : 'Notice';
    setAlert({
      message,
      title: title ?? defaultTitle,
      type
    });
  }, []);

  const closeAlert = useCallback(() => {
    setAlert(null);
  }, []);

  const value = { showAlert, showConfirm, closeAlert };

  return (
    <AlertContext.Provider value={value}>
      {children}
      <AlertModal alert={alert} onClose={closeAlert} />
      <ConfirmModal confirm={confirm} onConfirm={handleConfirm} onCancel={handleCancel} />
    </AlertContext.Provider>
  );
};
