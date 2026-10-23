import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ShieldCheck, KeyRound, Clock, AlertCircle, CheckCircle2, ArrowLeft, Send, Package, RefreshCw } from 'lucide-react';
import api from '../services/api';

export default function DeliveryVerification() {
  const { trackingId } = useParams();
  const navigate = useNavigate();

  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [otpGenLoading, setOtpGenLoading] = useState(false);
  const [otpGenerated, setOtpGenerated] = useState(false);
  const [testOtp, setTestOtp] = useState(null);
  const [expiresAt, setExpiresAt] = useState(null);
  const [timeLeft, setTimeLeft] = useState(null);
  const [error, setError] = useState('');
  const [successNotice, setSuccessNotice] = useState('');
  const [successData, setSuccessData] = useState(null);
  const hasRequestedOtpRef = useRef(false);

  const parseUtcExpiry = (isoString) => {
    if (!isoString) return null;
    const str = String(isoString).trim();
    const normalized = (str.endsWith('Z') || /[+-]\d{2}:?\d{2}$/.test(str)) ? str : `${str}Z`;
    const time = new Date(normalized).getTime();
    return isNaN(time) ? null : time;
  };

  // Countdown timer effect
  useEffect(() => {
    if (!expiresAt) return;

    const tick = () => {
      const now = Date.now();
      const expiry = parseUtcExpiry(expiresAt);
      if (!expiry) return;
      const diff = Math.max(0, Math.floor((expiry - now) / 1000));
      setTimeLeft(diff);
      return diff;
    };

    tick();
    const interval = setInterval(() => {
      const diff = tick();
      if (diff !== undefined && diff <= 0) {
        clearInterval(interval);
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [expiresAt]);

  const handleGenerateOTP = async () => {
    setOtpGenLoading(true);
    setError('');
    setSuccessNotice('');
    try {
      const res = await api.post(`/parcels/${trackingId}/delivery-otp`);
      setOtpGenerated(true);
      setOtp(''); // Clear any previous stale OTP

      const expiryStr = res.data.data.expires_at;
      setExpiresAt(expiryStr);
      const expiryMs = parseUtcExpiry(expiryStr);
      if (expiryMs) {
        setTimeLeft(Math.max(0, Math.floor((expiryMs - Date.now()) / 1000)));
      } else {
        setTimeLeft(900); // 15 minutes default
      }

      if (res.data.data.test_otp) {
        setTestOtp(res.data.data.test_otp);
      }
      setSuccessNotice('New 6-digit delivery verification code generated.');
      setTimeout(() => setSuccessNotice(''), 4000);
    } catch (err) {
      if (!err.response) {
        setError('Cannot connect to the backend server at http://localhost:8000. Please ensure the backend is running.');
      } else {
        setError(err.response?.data?.error?.message || 'Failed to generate delivery OTP.');
      }
    } finally {
      setOtpGenLoading(false);
    }
  };

  // Automatically request/generate OTP on load so agent doesn't need to click extra button
  useEffect(() => {
    if (trackingId && !hasRequestedOtpRef.current) {
      hasRequestedOtpRef.current = true;
      handleGenerateOTP();
    }
  }, [trackingId]);

  const handleVerifyDelivery = async (e) => {
    e.preventDefault();
    if (otp.length !== 6) {
      setError('Please enter a valid 6-digit numeric OTP.');
      return;
    }

    if (timeLeft !== null && timeLeft <= 0) {
      setError('The OTP code has expired. Please click "Resend Code" to generate a fresh verification code.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const res = await api.post(`/parcels/${trackingId}/verify-delivery`, { otp: otp.trim() });
      setSuccessData(res.data.data);
    } catch (err) {
      if (!err.response) {
        setError('Cannot connect to backend server. Please verify backend is running.');
      } else {
        setError(err.response?.data?.error?.message || 'OTP verification failed. Please re-enter.');
      }
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (seconds) => {
    if (seconds === null) return '--:--';
    if (seconds <= 0) return 'Expired';
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const isExpired = timeLeft !== null && timeLeft <= 0;

  return (
    <div className="container" style={{ maxWidth: '600px', marginTop: '36px' }}>
      <div style={{ marginBottom: '20px' }}>
        <Link to="/agent/deliveries" className="btn btn-outline btn-sm" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
          <ArrowLeft size={16} /> Back to Delivery Queue
        </Link>
      </div>

      <div className="card" style={{ padding: '32px' }}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div
            style={{
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              background: '#ecfdf5',
              color: '#059669',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '12px',
            }}
          >
            <ShieldCheck size={36} />
          </div>
          <h1 style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--primary-navy)' }}>
            Secure Delivery Confirmation
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '4px' }}>
            Consignment #{trackingId}
          </p>
        </div>

        {error && (
          <div className="alert alert-error" style={{ marginBottom: '20px', display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
            <AlertCircle size={20} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>{error}</div>
          </div>
        )}

        {successNotice && (
          <div className="alert alert-success" style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CheckCircle2 size={18} />
            <div>{successNotice}</div>
          </div>
        )}

        {isExpired && (
          <div className="alert alert-error" style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertCircle size={18} />
              <span style={{ fontSize: '0.85rem' }}>This verification code has expired. Please request a new code.</span>
            </div>
            <button
              type="button"
              onClick={handleGenerateOTP}
              className="btn btn-primary btn-sm"
              disabled={otpGenLoading}
            >
              <RefreshCw size={14} /> {otpGenLoading ? 'Generating...' : 'Resend Code Now'}
            </button>
          </div>
        )}

        {successData ? (
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <div style={{ color: '#16a34a', marginBottom: '16px' }}>
              <CheckCircle2 size={56} style={{ margin: '0 auto' }} />
            </div>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#15803d' }}>
              Consignment Successfully Delivered!
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', marginTop: '8px' }}>
              Delivery OTP verified and immutable delivery record committed.
            </p>
            <div style={{ background: '#f8fafc', padding: '14px', borderRadius: 'var(--radius)', border: '1px solid #e2e8f0', margin: '20px auto', maxWidth: '360px' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Delivered Timestamp</span>
              <div style={{ fontWeight: 600, fontSize: '0.95rem', marginTop: '2px' }}>
                {new Date(successData.delivered_at).toLocaleString()}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', marginTop: '24px' }}>
              <Link to="/agent/deliveries" className="btn btn-primary">
                Return to Delivery Queue
              </Link>
              <Link to={`/track/${trackingId}`} className="btn btn-outline">
                View Tracking Timeline
              </Link>
            </div>
          </div>
        ) : (
          <div>
            {!otpGenerated ? (
              <div style={{ textAlign: 'center', padding: '16px 0' }}>
                <p style={{ fontSize: '0.95rem', color: 'var(--text-main)', marginBottom: '20px' }}>
                  To ensure secure handover, trigger a one-time 6-digit delivery code to the recipient's registered device.
                </p>
                <button
                  onClick={handleGenerateOTP}
                  className="btn btn-primary"
                  style={{ height: '44px', padding: '0 24px', display: 'inline-flex', alignItems: 'center', gap: '8px' }}
                  disabled={otpGenLoading}
                >
                  <Send size={16} /> {otpGenLoading ? 'Generating Code...' : 'Send Delivery OTP to Recipient'}
                </button>
              </div>
            ) : (
              <form onSubmit={handleVerifyDelivery}>
                <div style={{ background: isExpired ? '#fef2f2' : '#f0fdf4', border: `1px solid ${isExpired ? '#fecaca' : '#bbf7d0'}`, borderRadius: '8px', padding: '14px 16px', marginBottom: '20px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.85rem', color: isExpired ? '#b91c1c' : '#166534', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Clock size={16} /> Code Expiry: {formatTime(timeLeft)}
                    </span>
                    <button
                      type="button"
                      onClick={handleGenerateOTP}
                      className="btn btn-outline btn-sm"
                      style={{ fontSize: '0.75rem', padding: '4px 8px' }}
                      disabled={otpGenLoading}
                    >
                      <RefreshCw size={12} /> Resend Code
                    </button>
                  </div>

                  {testOtp && (
                    <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: `1px dashed ${isExpired ? '#fca5a5' : '#86efac'}`, fontSize: '0.8rem', color: isExpired ? '#991b1b' : '#14532d', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <strong>Demo / Testing Helper:</strong> Recipient OTP is{' '}
                      <button
                        type="button"
                        onClick={() => { setOtp(testOtp); setError(''); }}
                        title="Click to auto-fill OTP"
                        style={{
                          background: isExpired ? '#fee2e2' : '#dcfce7',
                          border: `1px solid ${isExpired ? '#f87171' : '#86efac'}`,
                          padding: '3px 10px',
                          borderRadius: '6px',
                          fontFamily: 'monospace',
                          fontWeight: 800,
                          fontSize: '1.05rem',
                          color: isExpired ? '#991b1b' : '#14532d',
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}
                      >
                        {testOtp}
                        <span style={{ fontSize: '0.72rem', fontWeight: 600, color: isExpired ? '#dc2626' : '#15803d' }}>
                          (click to auto-fill)
                        </span>
                      </button>
                    </div>
                  )}
                </div>

                <div className="form-group" style={{ marginBottom: '24px', textAlign: 'center' }}>
                  <label className="form-label" style={{ fontSize: '0.9rem', marginBottom: '8px' }}>
                    Enter 6-Digit Recipient OTP
                  </label>
                  <input
                    type="text"
                    maxLength={6}
                    className="form-control"
                    style={{
                      fontSize: '1.75rem',
                      letterSpacing: '0.35em',
                      textAlign: 'center',
                      fontWeight: 700,
                      maxWidth: '240px',
                      margin: '0 auto',
                      height: '52px',
                    }}
                    placeholder="000000"
                    value={otp}
                    onChange={(e) => { setOtp(e.target.value.replace(/\D/g, '')); setError(''); }}
                    autoFocus
                    required
                  />
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginTop: '6px' }}>
                    Recipient must provide this code in person at the doorstep
                  </span>
                </div>

                <button
                  type="submit"
                  className="btn btn-success"
                  style={{ width: '100%', height: '46px', fontSize: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
                  disabled={loading || otp.length !== 6 || isExpired}
                >
                  <CheckCircle2 size={18} /> {loading ? 'Verifying...' : 'Confirm Delivery & Handover'}
                </button>
              </form>
            )}

            <div className="alert alert-info" style={{ marginTop: '24px', fontSize: '0.8rem' }}>
              <KeyRound size={16} />
              <div>
                <strong>Argon2id Secure Hashing:</strong> Plaintext OTPs are never stored in the database. 15-minute validity window with maximum 5 attempt lockouts strictly enforced.
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
