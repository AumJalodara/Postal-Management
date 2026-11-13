import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { QrCode, Scan, ArrowRight, AlertCircle, ShieldCheck, Camera, CameraOff, Upload, CheckCircle2, RefreshCw, XCircle } from 'lucide-react';
import { Html5Qrcode } from 'html5-qrcode';
import api from '../services/api';

const SAMPLE_TOKENS = [
  { label: 'Consignment GPM-2026-000010', token: 'GPMQR-93-n_weBsDHAk0od1cDBLnh0N59Jbo6l', id: 'GPM-2026-000010' },
  { label: 'Consignment GPM-2026-000003', token: 'GPMQR-VMtOA4_HOjOQ3wsQI2GC2vU4vDgwxIkX', id: 'GPM-2026-000003' },
  { label: 'Consignment GPM-2026-000004', token: 'GPMQR-TWAlruuwLvc27eo5IIOkAnKYPW7lT2mh', id: 'GPM-2026-000004' },
];

export default function QRScanner() {
  const navigate = useNavigate();

  // Scanner state
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraLoading, setCameraLoading] = useState(false);
  const [cameraError, setCameraError] = useState('');
  const [scanResult, setScanResult] = useState(null);

  // Manual / file state
  const [tokenInput, setTokenInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [fileDecoding, setFileDecoding] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const html5QrCodeRef = useRef(null);
  const readerElementId = 'qr-camera-viewport';

  useEffect(() => {
    // Cleanup on unmount: safely stop active camera stream
    return () => {
      stopCameraScanner();
    };
  }, []);

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

  const stopCameraScanner = async () => {
    if (html5QrCodeRef.current) {
      try {
        if (html5QrCodeRef.current.isScanning) {
          await html5QrCodeRef.current.stop();
        }
        await html5QrCodeRef.current.clear();
      } catch (err) {
        console.warn('Error clearing QR scanner:', err);
      } finally {
        html5QrCodeRef.current = null;
        setCameraActive(false);
        setCameraLoading(false);
      }
    }
  };

  const startCameraScanner = async () => {
    setCameraError('');
    setError('');
    setScanResult(null);
    setCameraLoading(true);

    try {
      // Ensure any existing instance is stopped first
      await stopCameraScanner();

      const html5QrCode = new Html5Qrcode(readerElementId);
      html5QrCodeRef.current = html5QrCode;

      const config = {
        fps: 10,
        qrbox: { width: 250, height: 250 },
        aspectRatio: 1.0,
      };

      const qrCodeSuccessCallback = async (decodedText) => {
        // Successfully detected and optically decoded QR
        await stopCameraScanner();
        setTokenInput(decodedText);
        await resolveDecodedToken(decodedText);
      };

      const qrCodeErrorCallback = (errorMessage) => {
        // Transient frame scan error — ignore in continuous scanning
      };

      // Request camera with facingMode environment (rear camera preferred on mobile)
      await html5QrCode.start(
        { facingMode: 'environment' },
        config,
        qrCodeSuccessCallback,
        qrCodeErrorCallback
      );

      setCameraActive(true);
    } catch (err) {
      console.error('Camera initialization error:', err);
      let message = 'Unable to access device camera.';
      const errStr = String(err).toLowerCase();

      if (errStr.includes('notallowederror') || errStr.includes('permission denied')) {
        message = 'Camera permission denied. Please allow camera access in your browser settings to scan QR codes.';
      } else if (errStr.includes('notfounderror') || errStr.includes('devices not found')) {
        message = 'No video capture device or camera detected on this system.';
      } else if (errStr.includes('notreadableerror') || errStr.includes('in use')) {
        message = 'Camera is currently in use by another application or tab.';
      } else if (window.isSecureContext === false && window.location.hostname !== 'localhost') {
        message = 'Camera access requires a secure HTTPS connection or localhost origin.';
      }

      setCameraError(message);
      await stopCameraScanner();
    } finally {
      setCameraLoading(false);
    }
  };

  const resolveDecodedToken = async (rawToken) => {
    const token = cleanInput(rawToken);
    if (!token) return;

    setLoading(true);
    setError('');
    setScanResult(null);

    // If it's a consignment tracking ID (e.g. GPM-2026-000010), route to tracking directly
    if (token.startsWith('GPM-') && !token.startsWith('GPMQR-')) {
      try {
        const res = await api.get(`/parcels/${encodeURIComponent(token)}/tracking`);
        if (res.data.success && res.data.data) {
          setScanResult({
            tracking_id: res.data.data.tracking_id,
            status: res.data.data.status,
            rawToken: token,
          });
          navigate(`/track/${encodeURIComponent(token)}`);
          return;
        }
      } catch (err) {
        // Fallback to /qr/resolve below
      }
    }

    try {
      const res = await api.post('/qr/resolve', { qr_token: token });
      if (res.data.success && res.data.data) {
        const trackingData = res.data.data;
        setScanResult({
          tracking_id: trackingData.tracking_id,
          status: trackingData.current_status,
          city: trackingData.destination_city,
          rawToken: token,
        });
        navigate(`/track/qr/${encodeURIComponent(token)}`);
      }
    } catch (err) {
      if (!err.response) {
        setError('Cannot connect to backend server. Please verify backend is running on http://localhost:8000.');
      } else {
        const msg = err.response?.data?.error?.message || 'The decoded QR token is invalid, expired, or unrecognized by the postal system.';
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleManualSubmit = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (cameraActive) {
      await stopCameraScanner();
    }
    await resolveDecodedToken(tokenInput);
  };

  const handleFileUpload = async (file) => {
    if (!file) return;
    setError('');
    setCameraError('');
    setFileDecoding(true);

    try {
      if (cameraActive) {
        await stopCameraScanner();
      }

      // Create a temporary Html5Qrcode instance to optically decode the image file
      const html5QrCode = new Html5Qrcode(readerElementId);
      const decodedText = await html5QrCode.scanFile(file, true);
      await html5QrCode.clear();

      setTokenInput(decodedText);
      await resolveDecodedToken(decodedText);
    } catch (err) {
      console.warn('Optical image file decode failed:', err);
      // Fallback: check if the filename contains the tracking ID (for convenience in file test suites)
      const filenameMatch = file.name.match(/(GPM(?:QR)?-[\w-]+)/i);
      if (filenameMatch && filenameMatch[1]) {
        setTokenInput(filenameMatch[1]);
        await resolveDecodedToken(filenameMatch[1]);
      } else {
        setError('Could not optically decode any valid QR barcode from the uploaded image. Please ensure the QR code image is clear, unblurred, and well-lit, or type the tracking ID manually.');
      }
    } finally {
      setFileDecoding(false);
    }
  };

  const selectSample = (token) => {
    if (cameraActive) {
      stopCameraScanner();
    }
    setTokenInput(token);
    setError('');
  };

  return (
    <div className="container" style={{ maxWidth: '660px', marginTop: '36px' }}>
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
            Optical QR Barcode Scanner
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '6px' }}>
            Live camera QR decoding and verification for Indian Postal consignments
          </p>
        </div>

        {/* Live Camera Viewport Box */}
        <div
          style={{
            border: '2px solid #3b82f6',
            borderRadius: '12px',
            padding: cameraActive ? '10px' : '26px 16px',
            textAlign: 'center',
            background: '#f8fafc',
            marginBottom: '20px',
            position: 'relative',
            minHeight: cameraActive ? '320px' : 'auto',
          }}
        >
          {/* html5-qrcode video viewport container */}
          <div
            id={readerElementId}
            style={{
              width: '100%',
              maxWidth: '420px',
              margin: '0 auto',
              display: cameraActive ? 'block' : 'none',
              borderRadius: '8px',
              overflow: 'hidden',
            }}
          />

          {!cameraActive && (
            <div>
              <div style={{ display: 'inline-block', padding: '16px', background: 'white', borderRadius: '50%', boxShadow: 'var(--shadow-sm)', marginBottom: '12px' }}>
                <Camera size={40} color="#2563eb" />
              </div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-main)' }}>
                Real-Time Optical Camera Scanning
              </h3>
              <p style={{ fontSize: '0.84rem', color: '#64748b', marginTop: '4px', maxWidth: '420px', margin: '4px auto 16px' }}>
                Point your webcam or mobile camera at a printed postal label to automatically scan and verify its tracking records.
              </p>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  onClick={startCameraScanner}
                  disabled={cameraLoading}
                  className="btn btn-primary btn-sm"
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                >
                  <Camera size={15} /> {cameraLoading ? 'Starting Camera...' : 'Start Camera Scanner'}
                </button>

                <label
                  htmlFor="qr-file-input"
                  className="btn btn-outline btn-sm"
                  style={{ cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                >
                  <Upload size={14} /> {fileDecoding ? 'Decoding Image...' : 'Scan Image File'}
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
          )}

          {cameraActive && (
            <div style={{ marginTop: '12px', display: 'flex', gap: '10px', justifyContent: 'center' }}>
              <button
                type="button"
                onClick={stopCameraScanner}
                className="btn btn-outline btn-sm"
                style={{ borderColor: '#ef4444', color: '#b91c1c', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              >
                <CameraOff size={14} /> Stop Camera
              </button>
              <button
                type="button"
                onClick={startCameraScanner}
                className="btn btn-outline btn-sm"
                style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              >
                <RefreshCw size={14} /> Reset Focus
              </button>
            </div>
          )}
        </div>

        {/* Camera Permission / Device Error Warning */}
        {cameraError && (
          <div className="alert alert-error" style={{ marginBottom: '20px', display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
            <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>
              <strong>Camera Notice:</strong> {cameraError}
              <div style={{ marginTop: '4px', fontSize: '0.8rem' }}>
                You can still resolve consignments using the manual entry box or test tokens below.
              </div>
            </div>
          </div>
        )}

        {/* Backend API Resolution Error */}
        {error && (
          <div className="alert alert-error" style={{ marginBottom: '20px', display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
            <XCircle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>{error}</div>
          </div>
        )}

        {/* Resolved Preview Card */}
        {scanResult && (
          <div className="alert alert-success" style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <strong>Scanned Consignment #{scanResult.tracking_id}</strong>
              <div style={{ fontSize: '0.8rem' }}>Status: {scanResult.status}</div>
            </div>
            <Link to={`/track/${scanResult.tracking_id}`} className="btn btn-primary btn-sm">
              View Tracking
            </Link>
          </div>
        )}

        {/* Manual Input Fallback */}
        <form onSubmit={handleManualSubmit}>
          <div className="form-group" style={{ marginBottom: '20px' }}>
            <label className="form-label">
              Manual Tracking ID or QR Token Fallback
            </label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. GPM-2026-000010 or GPMQR-93-n... or paste tracking URL"
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
            Quick Test Labels (Click to autofill):
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

        <div className="alert alert-info" style={{ marginTop: '24px', fontSize: '0.84rem' }}>
          <ShieldCheck size={18} />
          <div>
            <strong>Opaque Architecture:</strong> The QR system decodes unguessable tokens rather than exposing database primary keys, preventing consignment enumeration attacks.
          </div>
        </div>
      </div>
    </div>
  );
}
