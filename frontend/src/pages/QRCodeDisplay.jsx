import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { QrCode, Download, Printer, ArrowLeft, Package, ExternalLink, ShieldCheck, AlertCircle } from 'lucide-react';
import api from '../services/api';

export default function QRCodeDisplay() {
  const { trackingId } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [qrData, setQrData] = useState(null);

  useEffect(() => {
    fetchQRCode();
  }, [trackingId]);

  const fetchQRCode = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get(`/parcels/${trackingId}/qr`);
      setQrData(res.data.data);
    } catch (err) {
      const msg = err.response?.data?.error?.message || 'Failed to generate or retrieve QR code for this consignment.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!qrData?.qr_code_base64) return;
    const link = document.createElement('a');
    link.href = qrData.qr_code_base64;
    link.download = `QR_${trackingId}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="container" style={{ maxWidth: '650px', marginTop: '32px' }}>
      <div style={{ marginBottom: '20px' }}>
        <Link to="/parcels/my" className="btn btn-outline btn-sm" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
          <ArrowLeft size={16} /> Back to My Parcels
        </Link>
      </div>

      <div className="card" style={{ padding: '32px', textAlign: 'center' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--primary-navy)' }}>
          Consignment Tracking QR Code
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '6px' }}>
          Affix this official tracking label to the exterior of your consignment
        </p>

        {error && (
          <div className="alert alert-error" style={{ marginTop: '20px', textAlign: 'left' }}>
            <AlertCircle size={20} />
            <div>{error}</div>
          </div>
        )}

        {loading ? (
          <div style={{ padding: '40px 0', color: 'var(--text-muted)' }}>
            Generating high-resolution secure QR code...
          </div>
        ) : qrData ? (
          <div style={{ marginTop: '24px' }}>
            {/* Postal Label Simulation */}
            <div
              style={{
                border: '2px dashed #94a3b8',
                borderRadius: '8px',
                padding: '24px',
                background: '#ffffff',
                maxWidth: '380px',
                margin: '0 auto 24px auto',
              }}
            >
              <div style={{ borderBottom: '1px solid #e2e8f0', paddingBottom: '10px', marginBottom: '14px' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, letterSpacing: '0.08em', color: 'var(--primary-navy)', textTransform: 'uppercase' }}>
                  Smart Postal Service Prototype
                </span>
                <div style={{ fontSize: '1.15rem', fontWeight: 800, fontFamily: 'monospace', color: '#1e40af', marginTop: '4px' }}>
                  {qrData.tracking_id}
                </div>
              </div>

              {/* QR Image */}
              <div style={{ padding: '10px', background: '#f8fafc', borderRadius: '6px', display: 'inline-block' }}>
                <img
                  src={qrData.qr_code_base64}
                  alt={`QR Code for ${qrData.tracking_id}`}
                  style={{ width: '220px', height: '220px', display: 'block' }}
                />
              </div>

              <div style={{ marginTop: '12px', fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                Token: {qrData.qr_token.slice(0, 16)}...
              </div>
            </div>

            {/* Privacy note */}
            <div className="alert alert-info" style={{ textAlign: 'left', fontSize: '0.85rem', marginBottom: '24px' }}>
              <ShieldCheck size={18} />
              <div>
                <strong>Secure Opaque Code:</strong> This QR code encodes only a cryptographic resolution token. Personal citizen details and mobile numbers are never embedded in the QR payload.
              </div>
            </div>

            {/* Action Buttons */}
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', flexWrap: 'wrap' }}>
              <button
                onClick={handleDownload}
                className="btn btn-primary"
                style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
              >
                <Download size={16} /> Download PNG
              </button>
              <button
                onClick={handlePrint}
                className="btn btn-outline"
                style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
              >
                <Printer size={16} /> Print Label
              </button>
              <Link
                to={`/track/${trackingId}`}
                className="btn btn-outline"
                style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
              >
                <ExternalLink size={16} /> Track Timeline
              </Link>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
