import React, { useState } from 'react';
import { useNavigate, Link, useSearchParams } from 'react-router-dom';
import { LogIn, ShieldCheck, AlertCircle, Eye, EyeOff, User, Truck, MapPin, Building2 } from 'lucide-react';
import api from '../services/api';
import { validateEmail } from '../validation/rules';
import { STATE_AGENTS } from '../data/stateAgents';

export default function Login() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const isExpired = searchParams.get('expired');

  const [activeTab, setActiveTab] = useState('citizen'); // 'citizen' or 'agent'
  const [selectedStateIndex, setSelectedStateIndex] = useState(0);

  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [selectedDemo, setSelectedDemo] = useState(null);
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState('');
  const [loading, setLoading] = useState(false);

  const fillDemo = (email, password, key, autoSubmit = false) => {
    setSelectedDemo(key);
    setFormData({ email, password });
    setErrors({});
    setServerError('');

    if (autoSubmit) {
      executeLogin(email, password);
    }
  };

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    setServerError('');
    setErrors({});
    setSelectedDemo(null);

    if (tab === 'agent') {
      const ag = STATE_AGENTS[selectedStateIndex] || STATE_AGENTS[0];
      setFormData({ email: ag.email, password: 'Agent@12345' });
    } else {
      setFormData({ email: '', password: '' });
    }
  };

  const handleStateSelect = (e) => {
    const idx = parseInt(e.target.value, 10);
    setSelectedStateIndex(idx);
    const ag = STATE_AGENTS[idx];
    if (ag) {
      setFormData({ email: ag.email, password: 'Agent@12345' });
      setErrors({});
      setServerError('');
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setSelectedDemo(null);
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: null }));
    }
  };

  const executeLogin = async (email, password) => {
    setLoading(true);
    setServerError('');

    try {
      const response = await api.post('/auth/login', { email, password });
      const data = response.data.data;

      localStorage.setItem('token', data.access_token);
      localStorage.setItem(
        'user',
        JSON.stringify({
          id: data.user_id,
          name: data.name,
          email: data.email,
          role: data.role,
        })
      );

      if (data.role === 'ADMIN') {
        navigate('/admin/operations');
      } else if (data.role === 'AGENT') {
        navigate('/agent/dashboard');
      } else {
        navigate('/dashboard');
      }
    } catch (err) {
      if (!err.response) {
        setServerError('Cannot connect to the backend server at http://localhost:8000. Please verify the backend service is running.');
      } else if (err.response.status === 429) {
        setServerError('Too many login attempts. Please wait 30 seconds before retrying.');
      } else if (err.response?.data?.error?.message) {
        setServerError(err.response.data.error.message);
      } else {
        setServerError('Authentication failed. Please verify your email and password.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setServerError('');

    const emailErr = validateEmail(formData.email);
    if (emailErr) {
      setErrors({ email: emailErr });
      return;
    }

    if (!formData.password) {
      setErrors({ password: 'Password is required.' });
      return;
    }

    executeLogin(formData.email, formData.password);
  };

  const selectedAgent = STATE_AGENTS[selectedStateIndex] || STATE_AGENTS[0];

  return (
    <div className="container" style={{ maxWidth: '540px', marginTop: '36px' }}>
      <div className="card" style={{ padding: '32px' }}>
        {/* Header Branding */}
        <div style={{ textAlign: 'center', marginBottom: '22px' }}>
          <div
            style={{
              width: '54px',
              height: '54px',
              borderRadius: '12px',
              backgroundColor: activeTab === 'agent' ? '#b45309' : '#102a43',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '12px',
              transition: 'background-color 0.25s',
            }}
          >
            {activeTab === 'agent' ? <Truck size={28} color="#fff" /> : <ShieldCheck size={30} color="#fff" />}
          </div>
          <h2 style={{ fontSize: '1.4rem', color: '#102a43', fontWeight: 700 }}>
            {activeTab === 'agent' ? 'Delivery Fleet Portal' : 'Postal Portal Login'}
          </h2>
          <p style={{ fontSize: '0.875rem', color: '#64748b' }}>
            {activeTab === 'agent'
              ? 'Authorized India Post Delivery Personnel & Hub Dispatch'
              : 'Access Citizen Postal Services or Administration Portal'}
          </p>
        </div>

        {/* Portal Switcher Tabs */}
        <div
          style={{
            display: 'flex',
            backgroundColor: '#f1f5f9',
            borderRadius: '8px',
            padding: '4px',
            marginBottom: '22px',
          }}
        >
          <button
            type="button"
            onClick={() => handleTabChange('citizen')}
            style={{
              flex: 1,
              padding: '10px 14px',
              border: 'none',
              borderRadius: '6px',
              fontSize: '0.88rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              backgroundColor: activeTab === 'citizen' ? '#ffffff' : 'transparent',
              color: activeTab === 'citizen' ? '#102a43' : '#64748b',
              boxShadow: activeTab === 'citizen' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
              transition: 'all 0.2s ease',
            }}
          >
            <User size={16} /> Citizen & Admin
          </button>
          <button
            type="button"
            onClick={() => handleTabChange('agent')}
            style={{
              flex: 1,
              padding: '10px 14px',
              border: 'none',
              borderRadius: '6px',
              fontSize: '0.88rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              backgroundColor: activeTab === 'agent' ? '#ffffff' : 'transparent',
              color: activeTab === 'agent' ? '#b45309' : '#64748b',
              boxShadow: activeTab === 'agent' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
              transition: 'all 0.2s ease',
            }}
          >
            <Truck size={16} /> Delivery Agent Portal
          </button>
        </div>

        {isExpired && (
          <div className="alert alert-info">
            <AlertCircle size={18} />
            <span>Your session has expired. Please log in again.</span>
          </div>
        )}

        {serverError && (
          <div className="alert alert-error" style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
            <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
            <span>{serverError}</span>
          </div>
        )}

        {/* AGENT DEDICATED SECTION */}
        {activeTab === 'agent' && (
          <div
            style={{
              backgroundColor: '#fffbeb',
              border: '1px solid #fef3c7',
              borderRadius: '8px',
              padding: '14px',
              marginBottom: '18px',
            }}
          >
            <label className="form-label" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontWeight: 600, color: '#92400e', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Building2 size={16} /> Select State / Circle Hub (36 States & UTs):
              </span>
              <span style={{ fontSize: '0.75rem', color: '#b45309' }}>Pan-India Coverage</span>
            </label>
            <select
              className="form-input"
              value={selectedStateIndex}
              onChange={handleStateSelect}
              style={{
                backgroundColor: '#ffffff',
                borderColor: '#fcd34d',
                fontWeight: 600,
                color: '#1e293b',
                cursor: 'pointer',
                marginBottom: '10px',
              }}
            >
              {STATE_AGENTS.map((ag, idx) => (
                <option key={ag.email} value={idx}>
                  {ag.state} — {ag.hub} (PIN: {ag.pin})
                </option>
              ))}
            </select>

            {/* Agent Live Badge Card */}
            {selectedAgent && (
              <div
                style={{
                  backgroundColor: '#ffffff',
                  border: '1px solid #fef3c7',
                  borderRadius: '6px',
                  padding: '10px 12px',
                  fontSize: '0.82rem',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ color: '#64748b' }}>Assigned Agent:</span>
                  <strong style={{ color: '#0f172a' }}>{selectedAgent.name}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ color: '#64748b' }}>Official Email:</span>
                  <code style={{ color: '#2563eb' }}>{selectedAgent.email}</code>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: '#64748b' }}>Service Hub / PIN:</span>
                  <span className="badge" style={{ background: '#ecfdf5', color: '#065f46', fontSize: '0.78rem' }}>
                    <MapPin size={12} style={{ display: 'inline', marginRight: '2px' }} />
                    {selectedAgent.pin} ({selectedAgent.hub})
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* LOGIN FORM */}
        <form onSubmit={handleSubmit}>
          <div className="form-group" style={{ marginBottom: '16px' }}>
            <label className="form-label">
              {activeTab === 'agent' ? 'Agent Email Address' : 'Email Address'} <span className="required">*</span>
            </label>
            <input
              type="email"
              name="email"
              className="form-input"
              value={formData.email}
              onChange={handleChange}
              placeholder={activeTab === 'agent' ? 'agent.state@postal.gov.in' : 'name@example.com'}
              required
            />
            {errors.email && <span className="form-error">{errors.email}</span>}
          </div>

          <div className="form-group" style={{ marginBottom: '22px' }}>
            <label className="form-label">
              Password <span className="required">*</span>
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type={showPassword ? 'text' : 'password'}
                name="password"
                className="form-input"
                style={{ paddingRight: '40px' }}
                value={formData.password}
                onChange={handleChange}
                placeholder="••••••••"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: 'absolute',
                  right: '10px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: '#64748b',
                  display: 'flex',
                  alignItems: 'center',
                  padding: '4px',
                }}
                title={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {errors.password && <span className="form-error">{errors.password}</span>}
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{
              width: '100%',
              padding: '12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              backgroundColor: activeTab === 'agent' ? '#d97706' : undefined,
              borderColor: activeTab === 'agent' ? '#b45309' : undefined,
            }}
            disabled={loading}
          >
            {activeTab === 'agent' ? <Truck size={18} /> : <LogIn size={18} />}
            {loading ? 'Authenticating...' : activeTab === 'agent' ? `Sign In as ${selectedAgent.state} Agent` : 'Sign In'}
          </button>
        </form>

        {/* Footer Link */}
        {activeTab === 'citizen' && (
          <div style={{ marginTop: '20px', textAlign: 'center', fontSize: '0.875rem' }}>
            Don't have an account?{' '}
            <Link to="/register" style={{ color: '#ea580c', fontWeight: 600 }}>
              Register as Citizen
            </Link>
          </div>
        )}

        {/* Quick Demo Accounts for Citizen / Admin Tab */}
        {activeTab === 'citizen' && (
          <div
            style={{
              marginTop: '26px',
              borderTop: '1px solid #e2e8f0',
              backgroundColor: '#f8fafc',
              margin: '26px -32px -32px -32px',
              padding: '18px 32px',
              borderBottomLeftRadius: '6px',
              borderBottomRightRadius: '6px',
            }}
          >
            <span
              style={{
                fontSize: '0.75rem',
                fontWeight: 700,
                textTransform: 'uppercase',
                color: '#64748b',
                letterSpacing: '0.05em',
                display: 'block',
                marginBottom: '10px',
              }}
            >
              Quick Demo Accounts (1-Click Fill):
            </span>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <button
                type="button"
                className={`btn btn-outline btn-sm ${selectedDemo === 'citizen' ? 'btn-active' : ''}`}
                style={{
                  fontSize: '0.78rem',
                  justifyContent: 'flex-start',
                  backgroundColor: selectedDemo === 'citizen' ? '#eff6ff' : 'white',
                  borderColor: selectedDemo === 'citizen' ? '#3b82f6' : '#cbd5e1',
                }}
                onClick={() => fillDemo('citizen.demo@example.com', 'Citizen@12345', 'citizen')}
              >
                👤 Demo Citizen
              </button>
              <button
                type="button"
                className={`btn btn-outline btn-sm ${selectedDemo === 'admin' ? 'btn-active' : ''}`}
                style={{
                  fontSize: '0.78rem',
                  justifyContent: 'flex-start',
                  backgroundColor: selectedDemo === 'admin' ? '#eff6ff' : 'white',
                  borderColor: selectedDemo === 'admin' ? '#3b82f6' : '#cbd5e1',
                }}
                onClick={() => fillDemo('admin@postal.gov.in', 'Admin@12345', 'admin')}
              >
                ⚙️ Admin Portal
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
