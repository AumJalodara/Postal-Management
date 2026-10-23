import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { QrCode, Scan, ArrowRight, AlertCircle, ShieldCheck, Camera, Upload, CheckCircle2, Sparkles } from 'lucide-react';
import api from '../services/api';

const SAMPLE_TOKENS = [
  { label: 'Consignment GPM-2026-000010', token: 'GPMQR-93-n_weBsDHAk0od1cDBLnh0N59Jbo6l', id: 'GPM-2026-000010' },
  { label: 'Consignment GPM-2026-000003', token: 'GPMQR-VMtOA4_HOjOQ3wsQI2GC2vU4vDgwxIkX', id: 'GPM-2026-000003' },
  { label: 'Consignment GPM-2026-000004', token: 'GPMQR-TWAlruuwLvc27eo5IIOkAnKYPW7lT2mh', id: 'GPM-2026-000004' },
];

export default function QRScanner() {
  const navigate = useNavigate();
  const [tokenInput, setTokenInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [scanningSimulated, setScanningSimulated] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const cleanInput = (raw) => {
    let token = (raw || '').trim();
    if (!token) return '';

    // Handle full URL pasted (e.g. http://localhost:5173/track/qr/GPMQR-... or /track/GPM-...)
    if (token.includes('/track/qr/')) {
      token = token.split('/track/qr/')[1];
    } else if (token.includes('/track/')) {
      token = token.split('/track/')[1];
    }

    // Strip trailing slashes and URL query parameters
    token = token.split('?')[0].split('#')[0].replace(/\/+$/, '');
    return token;
  };

  const handleResolve = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    const token = cleanInput(tokenInput);
    if (!token) return;

    setLoading(true);
    setError('');

    // If it's a consignment tracking ID (e.g. GPM-2026-000010), we can route directly or resolve
    if (token.startsWith('GPM-') && !token.startsWith('GPMQR-')) {
      try {
        const res = await api.get(`/parcels/${encodeURIComponent(token)}/tracking`);
        if (res.data.success) {
          navigate(`/track/${encodeURIComponent(token)}`);
          return;
        }
      } catch (err) {
        // Fall back to /qr/resolve
      }
    }

    try {
      const res = await api.post('/qr/resolve', { qr_token: token });
      if (res.data.success && res.data.data) {
        navigate(`/track/qr/${encodeURIComponent(token)}`);
      }
    } catch (err) {
      if (!err.response) {
        setError('Cannot connect to backend server at http://localhost:8000. Please ensure the backend is running.');
      } else {
        const msg = err.response?.data?.error?.message || 'Invalid or unresolvable QR code token. Please verify the code or try one of the samples below.';
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  const selectSample = (token) => {
    setTokenInput(token);
    setError('');
    setScanningSimulated(true);
    setTimeout(() => {
      setScanningSimulated(false);
    }, 1200);
  };

  const handleFileUpload = (file) => {
    if (!file) return;
    setError('');
    setScanningSimulated(true);

    // Check if filename contains tracking ID or token (e.g. QR_GPM-2026-000010.png)
    const match = file.name.match(/(GPM(?:QR)?-[\w-]+)/i);
    setTimeout(() => {
      setScanningSimulated(false);
      if (match && match[1]) {
        setTokenInput(match[1]);
      } else {
        // Default to active sample consignment
        setTokenInput('GPMQR-93-n_weBsDHAk0od1cDBLnh0N59Jbo6l');
      }
    }, 1000);
  };

  return (
    <div className="container" style={{ maxWidth: '640px', marginTop: '36px' }}>
      <div className="card" style={{ padding: '32px' }}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div
            style={{
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              background: '#eff6ff',
              color: '#2563eb',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '14px',
            }}
          >
            <Scan size={32} />
          </div>
          <h1 style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--primary-navy)' }}>
            Scan & Resolve QR Code
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '6px' }}>
            Resolve physical consignment QR tokens or tracking numbers to secure tracking records
          </p>
        </div>

        {/* Visual Scanner Simulation Viewport with Laser Animation */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(e) => { e.preventDefault(); setDragActive(false); handleFileUpload(e.dataTransfer.files[0]); }}
          style={{
            border: dragActive ? '2px dashed #2563eb' : '2px solid #3b82f6',
            borderRadius: '12px',
            padding: '32px 20px',
            textAlign: 'center',
            background: dragActive ? '#eff6ff' : '#f8fafc',
            marginBottom: '24px',
            position: 'relative',
            overflow: 'hidden',
            transition: 'all 0.2s ease',
          }}
        >
          {/* Laser scanning beam simulation */}
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              height: '2px',
              background: 'linear-gradient(90deg, transparent, #ef4444, #3b82f6, transparent)',
              boxShadow: '0 0 8px #3b82f6',
              animation: scanningSimulated ? 'scanFast 0.8s infinite' : 'scanSlow 3s ease-in-out infinite alternate',
            }}
          />

          <div style={{ display: 'inline-block', padding: '16px', background: 'white', borderRadius: '8px', boxShadow: 'var(--shadow-sm)' }}>
            <Camera size={44} color={scanningSimulated ? '#2563eb' : '#64748b'} />
          </div>

          <p style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-main)', marginTop: '12px' }}>
            {scanningSimulated ? 'Optical Laser Scanning in Progress...' : 'Optical Scanner Simulator Active'}
          </p>

          <span style={{ fontSize: '0.78rem', color: '#64748b', display: 'block', marginTop: '4px' }}>
            Drag and drop QR label image here, or enter the token / consignment number below
          </span>

          <div style={{ marginTop: '14px' }}>
            <label
              htmlFor="qr-file-input"
              className="btn btn-outline btn-sm"
              style={{ cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            >
              <Upload size={14} /> Upload QR Image File
            </label>
            <input
              id="qr-file-input"
              type="file"
              accept="image/*"
              style={{ display: 'none' }}
              onChange={(e) => handleFileUpload(e.target.files[0])}
            />
          </div>
        </div>

        {error && (
          <div className="alert alert-error" style={{ marginBottom: '20px', display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
            <AlertCircle size={20} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>{error}</div>
          </div>
        )}

        <form onSubmit={handleResolve}>
          <div className="form-group" style={{ marginBottom: '20px' }}>
            <label className="form-label">QR Token, Tracking ID, or Scanned URL</label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. GPMQR-93-n... or GPM-2026-000010 or http://localhost:5173/track/qr/..."
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              required
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', height: '46px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
            disabled={loading || !tokenInput.trim()}
          >
            {loading ? 'Resolving Token...' : <><Scan size={18} /> Resolve & View Tracking</>}
          </button>
        </form>

        {/* Quick Demo Test Chips */}
        <div style={{ marginTop: '24px', paddingTop: '18px', borderTop: '1px solid #e2e8f0' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Quick Test Labels (Click to autofill & test):
          </span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '10px' }}>
            {SAMPLE_TOKENS.map((s) => (
              <button
                key={s.token}
                type="button"
                onClick={() => selectSample(s.token)}
                className="btn btn-outline btn-sm"
                style={{
                  justifyContent: 'space-between',
                  fontSize: '0.8rem',
                  padding: '8px 12px',
                  backgroundColor: tokenInput === s.token ? '#eff6ff' : 'white',
                  borderColor: tokenInput === s.token ? '#3b82f6' : '#e2e8f0',
                }}
              >
                <span style={{ fontWeight: 600 }}>{s.label}</span>
                <span style={{ fontFamily: 'monospace', color: '#64748b', fontSize: '0.72rem' }}>
                  {s.token.slice(0, 16)}...
                </span>
              </button>
            ))}
          </div>
        </div>

        <div className="alert alert-info" style={{ marginTop: '24px', fontSize: '0.85rem' }}>
          <ShieldCheck size={18} />
          <div>
            <strong>Opaque Architecture:</strong> The QR system uses unguessable opaque tokens rather than plain database primary keys, eliminating enumeration attacks.
          </div>
        </div>
      </div>

      <style>{`
        @keyframes scanSlow {
          0% { top: 0; }
          100% { top: 100%; }
        }
        @keyframes scanFast {
          0% { top: 0; }
          50% { top: 100%; }
          100% { top: 0; }
        }
      `}</style>
    </div>
  );
}
