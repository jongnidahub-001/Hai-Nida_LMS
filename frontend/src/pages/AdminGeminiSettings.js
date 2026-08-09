import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useAlert } from '../contexts/AlertContext';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import { API_BASE_URL } from '../config/api';
import './AdminHomePage.css';

const ROLE_CONFIG = [
  {
    role: 'planner',
    label: 'Planner / Reviewer',
    icon: 'fas fa-sitemap',
    color: 'is-link',
    description: 'Used for course/quiz outline planning and validation. Fast model recommended (e.g. Flash).',
  },
  {
    role: 'writer',
    label: 'Content Writer',
    icon: 'fas fa-pen-fancy',
    color: 'is-primary',
    description: 'Used for writing lesson content and quiz questions. Creative model recommended (e.g. Pro).',
  },
  {
    role: 'grader',
    label: 'Grader / Evaluator',
    icon: 'fas fa-check-double',
    color: 'is-success',
    description: 'Used for evaluating student answers and scoring. Fast model recommended.',
  },
];

function AdminGeminiSettings() {
  const { user, getAuthHeader } = useAuth();
  const { showAlert } = useAlert();
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modelsError, setModelsError] = useState(null);

  // Role-model state
  const [roleModels, setRoleModels] = useState({});
  const [roleStatus, setRoleStatus] = useState({});
  const [showRoleEditModal, setShowRoleEditModal] = useState(false);
  const [editingRole, setEditingRole] = useState(null);
  const [selectedRoleModel, setSelectedRoleModel] = useState('');
  const [savingRole, setSavingRole] = useState(false);

  // Legacy single-model modal (kept for backward compat)
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedModel, setSelectedModel] = useState('');
  const [saving, setSaving] = useState(false);

  // API Key state
  const [apiKeyInfo, setApiKeyInfo] = useState(null);
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);
  const [newApiKey, setNewApiKey] = useState('');
  const [savingApiKey, setSavingApiKey] = useState(false);

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
      const [statusRes, modelsRes, apiKeyRes, roleModelsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/admin/gemini/status`, {
          headers: { ...getAuthHeader(), 'Content-Type': 'application/json' }
        }),
        fetch(`${API_BASE_URL}/api/admin/gemini/models`, {
          headers: { ...getAuthHeader(), 'Content-Type': 'application/json' }
        }),
        fetch(`${API_BASE_URL}/api/admin/gemini/api-key`, {
          headers: { ...getAuthHeader(), 'Content-Type': 'application/json' }
        }),
        fetch(`${API_BASE_URL}/api/admin/gemini/role-models`, {
          headers: { ...getAuthHeader(), 'Content-Type': 'application/json' }
        }),
      ]);

      if (statusRes.ok) {
        const s = await statusRes.json();
        setStatus(s);
        setSelectedModel(s.current_version || '');
        if (s.error) showAlert(s.error, 'error');
      }
      if (modelsRes.ok) {
        const m = await modelsRes.json();
        setModels(m.models || []);
        if (m.error) setModelsError(m.error);
      } else {
        const m = await modelsRes.json().catch(() => ({}));
        setModelsError(m.error || 'Failed to load models');
      }
      if (apiKeyRes.ok) {
        const keyData = await apiKeyRes.json();
        setApiKeyInfo(keyData);
      }
      if (roleModelsRes.ok) {
        const rm = await roleModelsRes.json();
        setRoleModels({
          planner: rm.planner_model || '',
          writer: rm.writer_model || '',
          grader: rm.grader_model || '',
        });
        setRoleStatus(rm.status_per_role || {});
      }
    } catch (err) {
      console.error(err);
      setModelsError(err.message || 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveRoleModel = async (e) => {
    e && e.preventDefault();
    if (!editingRole || !selectedRoleModel.trim()) return;
    setSavingRole(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/gemini/role-model`, {
        method: 'PUT',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: editingRole, model: selectedRoleModel.trim() })
      });
      const data = await response.json();
      if (response.ok && data.success) {
        setShowRoleEditModal(false);
        fetchData();
        showAlert(`Model for ${editingRole} updated successfully`, 'success');
      } else {
        showAlert(data.detail || data.error || 'Failed to update model', 'error');
      }
    } catch (err) {
      console.error(err);
      showAlert('Failed to update model. Please try again.', 'error');
    } finally {
      setSavingRole(false);
    }
  };

  const handleSaveVersion = async (e) => {
    e.preventDefault();
    if (!selectedModel.trim()) return;
    setSaving(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/gemini/version`, {
        method: 'PUT',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: selectedModel.trim() })
      });
      const data = await response.json();
      if (response.ok && data.success) {
        setShowEditModal(false);
        fetchData();
        showAlert('All models updated successfully', 'success');
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

  const handleSaveApiKey = async (e) => {
    e.preventDefault();
    if (!newApiKey.trim()) return;
    setSavingApiKey(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/gemini/api-key`, {
        method: 'PUT',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: newApiKey.trim() })
      });
      const data = await response.json();
      if (response.ok && data.success) {
        setShowApiKeyModal(false);
        setNewApiKey('');
        fetchData();
        showAlert('API Key updated successfully', 'success');
      } else {
        showAlert(data.detail || data.error || 'Failed to update API key', 'error');
      }
    } catch (err) {
      console.error(err);
      showAlert('Failed to update API key. Please try again.', 'error');
    } finally {
      setSavingApiKey(false);
    }
  };

  const handleDeleteApiKey = async () => {
    if (!window.confirm('Are you sure you want to remove the custom API key? The system will revert to using the .env file key.')) return;
    setSavingApiKey(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/gemini/api-key`, {
        method: 'DELETE',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' }
      });
      const data = await response.json();
      if (response.ok && data.success) {
        fetchData();
        showAlert('Custom API key removed. Using .env fallback.', 'success');
      } else {
        showAlert(data.detail || data.error || 'Failed to remove API key', 'error');
      }
    } catch (err) {
      showAlert('Failed to remove API key.', 'error');
    } finally {
      setSavingApiKey(false);
    }
  };

  const openRoleEdit = (role) => {
    setEditingRole(role);
    setSelectedRoleModel(roleModels[role] || '');
    setShowRoleEditModal(true);
  };

  const getSourceLabel = (source) => {
    switch (source) {
      case 'web_config': return 'Web Config';
      case 'env_file': return '.env File';
      default: return 'Not Set';
    }
  };

  const getSourceTagClass = (source) => {
    switch (source) {
      case 'web_config': return 'is-info';
      case 'env_file': return 'is-warning';
      default: return 'is-danger';
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

          {/* Section 1: API Key Configuration */}
          <div className="mb-5">
            <h5 className="title is-5 mb-3">API Key</h5>
            <div className="is-flex is-align-items-center is-flex-wrap-wrap" style={{ gap: '0.75rem' }}>
              <div>
                <span className="has-text-weight-semibold mr-2">Key:</span>
                <code style={{ fontSize: '0.9rem' }}>
                  {apiKeyInfo?.has_key ? apiKeyInfo.masked_key : 'Not configured'}
                </code>
              </div>
              <span className={`tag is-medium ${getSourceTagClass(apiKeyInfo?.source)}`}>
                {getSourceLabel(apiKeyInfo?.source)}
              </span>
              <button className="button is-primary is-small" onClick={() => setShowApiKeyModal(true)}>
                <span className="icon is-small"><i className="fas fa-key"></i></span>
                <span>{apiKeyInfo?.has_key ? 'Change Key' : 'Set Key'}</span>
              </button>
              {apiKeyInfo?.source === 'web_config' && (
                <button className="button is-danger is-small is-outlined" onClick={handleDeleteApiKey} disabled={savingApiKey}>
                  <span className="icon is-small"><i className="fas fa-trash"></i></span>
                  <span>Revert to .env</span>
                </button>
              )}
            </div>
            {apiKeyInfo?.source === 'none' && (
              <p className="help has-text-danger mt-2">No API key configured. Please set one to enable Gemini features.</p>
            )}
          </div>

          {/* Section 2: Multi-Model Role Configuration */}
          <div className="mb-5">
            <h5 className="title is-5 mb-3">
              Model Configuration by Role
              <button className="button is-small is-outlined ml-3" onClick={() => setShowEditModal(true)} title="Set all roles to the same model">
                <span className="icon is-small"><i className="fas fa-sync-alt"></i></span>
                <span>Set All</span>
              </button>
            </h5>
            <div className="columns is-multiline">
              {ROLE_CONFIG.map(({ role, label, icon, color, description }) => (
                <div className="column is-4" key={role}>
                  <div className="box" style={{ height: '100%' }}>
                    <div className="is-flex is-align-items-center mb-2">
                      <span className={`icon ${color} mr-2`}><i className={icon}></i></span>
                      <span className="has-text-weight-bold">{label}</span>
                    </div>
                    <p className="is-size-7 has-text-grey mb-3">{description}</p>
                    <div className="is-flex is-align-items-center is-flex-wrap-wrap" style={{ gap: '0.5rem' }}>
                      <code style={{ fontSize: '0.85rem' }}>{roleModels[role] || 'Not set'}</code>
                      <span className={`tag is-small ${roleStatus[role] === 'active' ? 'is-success' : 'is-danger'}`}>
                        {roleStatus[role] === 'active' ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    <button className="button is-small is-outlined mt-3" onClick={() => openRoleEdit(role)}>
                      <span className="icon is-small"><i className="fas fa-edit"></i></span>
                      <span>Edit</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Section 3: Available models list */}
          <div>
            <h5 className="title is-5 mb-3">Available Models</h5>
            {modelsError ? (
              <div className="notification is-warning is-light">{modelsError}</div>
            ) : models.length === 0 ? (
              <p className="has-text-grey">No models available or API key not configured.</p>
            ) : (
              <div className="table-container">
                <table className="table is-fullwidth is-hoverable is-narrow">
                  <thead>
                    <tr><th>Model Name</th><th>Used By</th></tr>
                  </thead>
                  <tbody>
                    {models.map((model) => {
                      const usedBy = Object.entries(roleModels)
                        .filter(([, v]) => v === model)
                        .map(([k]) => k);
                      return (
                        <tr key={model}>
                          <td><span className="gemini-version-text">{model}</span></td>
                          <td>
                            {usedBy.length > 0
                              ? usedBy.map(r => (
                                  <span key={r} className="tag is-light is-info is-small mr-1">{r}</span>
                                ))
                              : <span className="has-text-grey-light">-</span>
                            }
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Role-Model Edit Modal */}
      <div className={`modal ${showRoleEditModal ? 'is-active' : ''}`}>
        <div className="modal-background" onClick={() => !savingRole && setShowRoleEditModal(false)}></div>
        <div className="modal-card" style={{ backgroundColor: 'white' }}>
          <header className="modal-card-head" style={{ backgroundColor: 'white', borderBottom: '1px solid var(--medium-grey)' }}>
            <p className="modal-card-title" style={{ color: 'var(--primary-black)', fontWeight: 'bold' }}>
              Edit Model for: {editingRole ? ROLE_CONFIG.find(r => r.role === editingRole)?.label : ''}
            </p>
            <button className="delete" onClick={() => !savingRole && setShowRoleEditModal(false)} disabled={savingRole}></button>
          </header>
          <section className="modal-card-body" style={{ backgroundColor: 'white' }}>
            <form onSubmit={handleSaveRoleModel}>
              <div className="field">
                <label className="label" style={{ color: 'var(--primary-black)', fontWeight: '600' }}>Select Model</label>
                <div className="control">
                  <div className="select is-fullwidth">
                    <select value={selectedRoleModel} onChange={(e) => setSelectedRoleModel(e.target.value)} disabled={savingRole || models.length === 0}>
                      {models.length === 0 ? (
                        <option value="">No models available</option>
                      ) : (
                        models.map((m) => <option key={m} value={m}>{m}</option>)
                      )}
                    </select>
                  </div>
                </div>
              </div>
            </form>
          </section>
          <footer className="modal-card-foot" style={{ backgroundColor: 'white', borderTop: '1px solid var(--medium-grey)', gap: '12px' }}>
            <button className={`button is-primary ${savingRole ? 'is-loading' : ''}`} onClick={handleSaveRoleModel} disabled={savingRole || !selectedRoleModel} style={{ backgroundColor: 'var(--primary-color)', borderColor: 'var(--primary-color)', color: 'white' }}>
              Save
            </button>
            <button className="button" onClick={() => !savingRole && setShowRoleEditModal(false)} disabled={savingRole} style={{ backgroundColor: 'var(--light-grey)', borderColor: 'var(--medium-grey)', color: 'var(--primary-black)' }}>
              Cancel
            </button>
          </footer>
        </div>
      </div>

      {/* Set All Models Modal (legacy) */}
      <div className={`modal ${showEditModal ? 'is-active' : ''}`}>
        <div className="modal-background" onClick={() => !saving && setShowEditModal(false)}></div>
        <div className="modal-card" style={{ backgroundColor: 'white' }}>
          <header className="modal-card-head" style={{ backgroundColor: 'white', borderBottom: '1px solid var(--medium-grey)' }}>
            <p className="modal-card-title" style={{ color: 'var(--primary-black)', fontWeight: 'bold' }}>Set All Roles to Same Model</p>
            <button className="delete" onClick={() => !saving && setShowEditModal(false)} disabled={saving}></button>
          </header>
          <section className="modal-card-body" style={{ backgroundColor: 'white' }}>
            <form onSubmit={handleSaveVersion}>
              <div className="field">
                <label className="label" style={{ color: 'var(--primary-black)', fontWeight: '600' }}>Select Model (applies to all roles)</label>
                <div className="control">
                  <div className="select is-fullwidth">
                    <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)} disabled={saving || models.length === 0}>
                      {models.length === 0 ? (
                        <option value="">No models available</option>
                      ) : (
                        models.map((m) => <option key={m} value={m}>{m}</option>)
                      )}
                    </select>
                  </div>
                </div>
              </div>
            </form>
          </section>
          <footer className="modal-card-foot" style={{ backgroundColor: 'white', borderTop: '1px solid var(--medium-grey)', gap: '12px' }}>
            <button className={`button is-primary ${saving ? 'is-loading' : ''}`} onClick={handleSaveVersion} disabled={saving || !selectedModel || models.length === 0} style={{ backgroundColor: 'var(--primary-color)', borderColor: 'var(--primary-color)', color: 'white' }}>
              Save
            </button>
            <button className="button" onClick={() => !saving && setShowEditModal(false)} disabled={saving} style={{ backgroundColor: 'var(--light-grey)', borderColor: 'var(--medium-grey)', color: 'var(--primary-black)' }}>
              Cancel
            </button>
          </footer>
        </div>
      </div>

      {/* API Key Modal */}
      <div className={`modal ${showApiKeyModal ? 'is-active' : ''}`}>
        <div className="modal-background" onClick={() => !savingApiKey && setShowApiKeyModal(false)}></div>
        <div className="modal-card" style={{ backgroundColor: 'white' }}>
          <header className="modal-card-head" style={{ backgroundColor: 'white', borderBottom: '1px solid var(--medium-grey)' }}>
            <p className="modal-card-title" style={{ color: 'var(--primary-black)', fontWeight: 'bold' }}>
              {apiKeyInfo?.has_key ? 'Change API Key' : 'Set API Key'}
            </p>
            <button className="delete" onClick={() => !savingApiKey && setShowApiKeyModal(false)} disabled={savingApiKey}></button>
          </header>
          <section className="modal-card-body" style={{ backgroundColor: 'white' }}>
            <form onSubmit={handleSaveApiKey}>
              <div className="field">
                <label className="label" style={{ color: 'var(--primary-black)', fontWeight: '600' }}>Gemini API Key</label>
                <div className="control has-icons-left">
                  <input className="input" type="password" placeholder="Enter your Gemini API key (e.g. AIzaSy...)" value={newApiKey} onChange={(e) => setNewApiKey(e.target.value)} disabled={savingApiKey} autoComplete="off" />
                  <span className="icon is-small is-left"><i className="fas fa-key"></i></span>
                </div>
                <p className="help">
                  The key will be validated before saving. Get a key from{' '}
                  <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer">Google AI Studio</a>.
                </p>
              </div>
            </form>
          </section>
          <footer className="modal-card-foot" style={{ backgroundColor: 'white', borderTop: '1px solid var(--medium-grey)', gap: '12px' }}>
            <button className={`button is-primary ${savingApiKey ? 'is-loading' : ''}`} onClick={handleSaveApiKey} disabled={savingApiKey || !newApiKey.trim()} style={{ backgroundColor: 'var(--primary-color)', borderColor: 'var(--primary-color)', color: 'white' }}>
              Save
            </button>
            <button className="button" onClick={() => !savingApiKey && setShowApiKeyModal(false)} disabled={savingApiKey} style={{ backgroundColor: 'var(--light-grey)', borderColor: 'var(--medium-grey)', color: 'var(--primary-black)' }}>
              Cancel
            </button>
          </footer>
        </div>
      </div>
    </div>
  );
}

export default AdminGeminiSettings;
