import React, { useState, useEffect } from 'react';
import { User, Phone, Mail, Shield, Calendar, CheckCircle2, AlertCircle, Save, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';
import api from '../services/api';

export default function Profile() {
  const [profile, setProfile] = useState(null);
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await api.get('/auth/me');
      const data = res.data.data;
      setProfile(data);
      setName(data.name || '');
      setPhone(data.phone || '');
    } catch (err) {
      setErrorMsg(err.response?.data?.error?.message || 'Failed to load profile details.');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    // Client-side validation
    const trimmedName = name.trim();
    const cleanPhone = phone.trim();

    if (!trimmedName || trimmedName.length < 2) {
      setErrorMsg('Full name must be at least 2 characters long.');
      return;
    }
    if (!/^\d{10}$/.test(cleanPhone)) {
      setErrorMsg('Mobile number must be exactly 10 digits.');
      return;
    }

    setSaving(true);
    try {
      const res = await api.put('/auth/me', {
        name: trimmedName,
        phone: cleanPhone,
      });
      const updated = res.data.data;
      setProfile(updated);
      setName(updated.name);
      setPhone(updated.phone);

      // Refresh stored user in localStorage so Navbar and greetings update immediately
      const storedUser = JSON.parse(localStorage.getItem('user') || '{}');
      const refreshedUser = { ...storedUser, name: updated.name, phone: updated.phone };
      localStorage.setItem('user', JSON.stringify(refreshedUser));

      setSuccessMsg('Your profile information has been successfully updated.');
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setErrorMsg(err.response?.data?.error?.message || 'Failed to update profile.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="container" style={{ maxWidth: '640px', marginTop: '48px', textAlign: 'center' }}>
        <p style={{ color: 'var(--text-muted)' }}>Loading account profile...</p>
      </div>
    );
  }

  return (
    <div className="container" style={{ maxWidth: '640px', marginTop: '36px' }}>
      <div style={{ marginBottom: '18px' }}>
        <Link to="/" className="btn btn-outline btn-sm" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
          <ArrowLeft size={15} /> Back to Dashboard
        </Link>
      </div>

      <div className="card" style={{ padding: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '24px', borderBottom: '1px solid #e2e8f0', paddingBottom: '20px' }}>
          <div
            style={{
              width: '54px',
              height: '54px',
              borderRadius: '50%',
              background: '#eff6ff',
              color: '#2563eb',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <User size={28} />
          </div>
          <div>
            <h1 style={{ fontSize: '1.45rem', fontWeight: 700, color: 'var(--primary-navy)' }}>
              User Profile & Settings
            </h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', marginTop: '2px' }}>
              Manage your personal details and account settings
            </p>
          </div>
        </div>

        {errorMsg && (
          <div className="alert alert-error" style={{ marginBottom: '20px', display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
            <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>{errorMsg}</div>
          </div>
        )}

        {successMsg && (
          <div className="alert alert-success" style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CheckCircle2 size={18} />
            <div>{successMsg}</div>
          </div>
        )}

        <form onSubmit={handleUpdate}>
          {/* Read-Only Account Attributes */}
          <div style={{ background: '#f8fafc', borderRadius: '8px', padding: '16px', marginBottom: '22px', border: '1px solid #e2e8f0' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
              <div>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <Mail size={12} /> Registered Email
                </span>
                <span style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-main)', marginTop: '4px', display: 'block' }}>
                  {profile?.email || '—'}
                </span>
                <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Protected primary identifier</span>
              </div>

              <div>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <Shield size={12} /> Assigned Role
                </span>
                <span className="badge badge-booked" style={{ marginTop: '4px', display: 'inline-block' }}>
                  {profile?.role || 'CITIZEN'}
                </span>
                <span style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'block', marginTop: '2px' }}>System privileges tier</span>
              </div>
            </div>

            {profile?.created_at && (
              <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px dashed #cbd5e1', fontSize: '0.78rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Calendar size={13} /> Member since {new Date(profile.created_at).toLocaleDateString()}
              </div>
            )}
          </div>

          {/* Editable Fields */}
          <div className="form-group" style={{ marginBottom: '18px' }}>
            <label className="form-label">
              Full Legal Name <span style={{ color: '#ef4444' }}>*</span>
            </label>
            <input
              type="text"
              className="form-control"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="Enter your full name"
              maxLength={100}
            />
          </div>

          <div className="form-group" style={{ marginBottom: '24px' }}>
            <label className="form-label">
              Contact Mobile Number <span style={{ color: '#ef4444' }}>*</span>
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type="tel"
                className="form-control"
                value={phone}
                onChange={(e) => setPhone(e.target.value.replace(/\D/g, '').slice(0, 10))}
                required
                placeholder="10-digit mobile number (e.g. 9876543210)"
                maxLength={10}
              />
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginTop: '4px' }}>
              Used for doorstep pickup notifications and delivery verification
            </span>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={saving}
            style={{ width: '100%', height: '44px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
          >
            <Save size={16} /> {saving ? 'Saving Changes...' : 'Save Profile Changes'}
          </button>
        </form>
      </div>
    </div>
  );
}

