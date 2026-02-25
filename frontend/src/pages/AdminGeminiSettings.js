import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useAlert } from '../contexts/AlertContext';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import { API_BASE_URL } from '../config/api';
import './AdminHomePage.css';

function AdminGeminiSettings() {
  const { user, getAuthHeader } = useAuth();
  const { showAlert } = useAlert();
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modelsError, setModelsError] = useState(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedModel, setSelectedModel] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!user || user.role !== 'admin') {
      navigate('/login');
      return;
    }
    fetchData();
  }, [user, navigate]);

  const fetchData = async () => {
    setLoading(true);
    setModelsError(null);
    try {
      const [statusRes, modelsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/admin/gemini/status`, {
          headers: { ...getAuthHeader(), 'Content-Type': 'application/json' }
        }),
        fetch(`${API_BASE_URL}/api/admin/gemini/models`, {
          headers: { ...getAuthHeader(), 'Content-Type': 'application/json' }
        })
      ]);

      if (statusRes.ok) {
        const s = await statusRes.json();
        setStatus(s);
        setSelectedModel(s.current_version || '');
      }
      if (modelsRes.ok) {
        const m = await modelsRes.json();
        setModels(m.models || []);
        if (m.error) setModelsError(m.error);
      } else {
        const m = await modelsRes.json().catch(() => ({}));
        setModelsError(m.error || 'Failed to load models');
      }
    } catch (err) {
      console.error(err);
      setModelsError(err.message || 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveVersion = async (e) => {
    e.preventDefault();
    if (!selectedModel.trim()) return;
    setSaving(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/gemini/version`, {
        method: 'PUT',
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ model: selectedModel.trim() })
      });
      const data = await response.json();
      if (response.ok && data.success) {
        setStatus(prev => ({ ...prev, current_version: data.current_version }));
        setShowEditModal(false);
        fetchData();
        showAlert('Gemini version updated successfully', 'success');
      } else {
        showAlert(data.detail || data.error || 'Failed to update version', 'error');
      }
    } catch (err) {
      console.error(err);
      showAlert('Failed to update version. Please try again.', 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading && !status) {
    return (
      <div className="admin-home-bg">
        <Header />
        <div className="container mt-4">
          <div className="has-text-centered py-6">
            <div className="is-size-6">Loading settings...</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-home-bg">
      <Header />
      <div className="container mt-4">
        <div className="box admin-home-card">
          <div className="is-size-4 has-text-weight-bold mb-4">Gemini API Settings</div>

          {/* Section 1: Current version + Status */}
          <div className="mb-5">
            <h5 className="title is-5 mb-3">Current Configuration</h5>
            <div className="is-flex is-align-items-center is-flex-wrap-wrap" style={{ gap: '0.75rem' }}>
              <div>
                <span className="has-text-weight-semibold mr-2">Version:</span>
                <span className="gemini-version-text">{status?.current_version || '-'}</span>
              </div>
              <span
                className={`tag is-medium ${status?.status === 'active' ? 'is-success' : 'is-danger'}`}
              >
                {status?.status === 'active' ? 'Active' : 'Inactive'}
              </span>
              <button
                className="button is-primary is-small"
                onClick={() => setShowEditModal(true)}
              >
                <span className="icon is-small">
                  <i className="fas fa-edit"></i>
                </span>
                <span>Edit Version</span>
              </button>
            </div>
          </div>

          {/* Section 2: Available versions */}
          <div>
            <h5 className="title is-5 mb-3">Available Models</h5>
            {modelsError ? (
              <div className="notification is-warning is-light">
                {modelsError}
              </div>
            ) : models.length === 0 ? (
              <p className="has-text-grey">No models available or API key not configured.</p>
            ) : (
              <div className="table-container">
                <table className="table is-fullwidth is-hoverable">
                  <thead>
                    <tr>
                      <th>Model Name</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {models.map((model) => (
                      <tr key={model}>
                        <td>
                          <span className="gemini-version-text">{model}</span>
                          {status?.current_version === model && (
                            <span className="tag is-info is-light ml-2">Current</span>
                          )}
                        </td>
                        <td>
                          <span
                            className={`tag ${
                              status?.current_version === model && status?.status === 'active'
                                ? 'is-success'
                                : status?.current_version === model
                                ? 'is-danger'
                                : 'is-light'
                            }`}
                          >
                            {status?.current_version === model
                              ? status?.status === 'active'
                                ? 'Active'
                                : 'Inactive'
                              : '-'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Edit Version Modal */}
      <div className={`modal ${showEditModal ? 'is-active' : ''}`}>
        <div className="modal-background" onClick={() => !saving && setShowEditModal(false)}></div>
        <div className="modal-card" style={{ backgroundColor: 'white' }}>
          <header
            className="modal-card-head"
            style={{
              backgroundColor: 'white',
              borderBottom: '1px solid var(--medium-grey)'
            }}
          >
            <p
              className="modal-card-title"
              style={{ color: 'var(--primary-black)', fontWeight: 'bold' }}
            >
              Edit Gemini Version
            </p>
            <button
              className="delete"
              onClick={() => !saving && setShowEditModal(false)}
              disabled={saving}
            ></button>
          </header>
          <section className="modal-card-body" style={{ backgroundColor: 'white' }}>
            <form onSubmit={handleSaveVersion}>
              <div className="field">
                <label className="label" style={{ color: 'var(--primary-black)', fontWeight: '600' }}>
                  Select Model
                </label>
                <div className="control">
                  <div className="select is-fullwidth">
                    <select
                      value={selectedModel}
                      onChange={(e) => setSelectedModel(e.target.value)}
                      disabled={saving || models.length === 0}
                    >
                      {models.length === 0 ? (
                        <option value="">No models available</option>
                      ) : (
                        models.map((m) => (
                          <option key={m} value={m}>
                            {m}
                          </option>
                        ))
                      )}
                    </select>
                  </div>
                </div>
              </div>
            </form>
          </section>
          <footer
            className="modal-card-foot"
            style={{
              backgroundColor: 'white',
              borderTop: '1px solid var(--medium-grey)',
              gap: '12px'
            }}
          >
            <button
              className={`button is-primary ${saving ? 'is-loading' : ''}`}
              onClick={handleSaveVersion}
              disabled={saving || !selectedModel || models.length === 0}
              style={{
                backgroundColor: 'var(--primary-color)',
                borderColor: 'var(--primary-color)',
                color: 'white'
              }}
            >
              Save
            </button>
            <button
              className="button"
              onClick={() => !saving && setShowEditModal(false)}
              disabled={saving}
              style={{
                backgroundColor: 'var(--light-grey)',
                borderColor: 'var(--medium-grey)',
                color: 'var(--primary-black)'
              }}
            >
              Cancel
            </button>
          </footer>
        </div>
      </div>
    </div>
  );
}

export default AdminGeminiSettings;
