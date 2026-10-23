import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Search, Package, MapPin, Clock, ShieldCheck, QrCode, ArrowRight, CheckCircle2, AlertCircle } from 'lucide-react';
import api from '../services/api';

export default function TrackParcel() {
  const { trackingId, qrToken } = useParams();
  const navigate = useNavigate();

  const [inputQuery, setInputQuery] = useState(trackingId || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [trackingData, setTrackingData] = useState(null);

  useEffect(() => {
    if (qrToken) {
      resolveToken(qrToken);
    } else if (trackingId) {
      fetchTracking(trackingId);
    }
  }, [trackingId, qrToken]);

  const resolveToken = async (token) => {
    setLoading(true);
    setError('');
    try {
      const res = await api.post('/qr/resolve', { qr_token: token });
      setTrackingData(res.data.data);
      setInputQuery(res.data.data.tracking_id);
    } catch (err) {
      const msg = err.response?.data?.error?.message || 'QR code resolution failed. The code may be invalid or expired.';
      setError(msg);
      setTrackingData(null);
    } finally {
      setLoading(false);
    }
  };

  const fetchTracking = async (id) => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get(`/parcels/${id.trim()}/tracking`);
      setTrackingData(res.data.data);
    } catch (err) {
      const msg = err.response?.data?.error?.message || 'Consignment not found or tracking history unavailable.';
      setError(msg);
      setTrackingData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    if (!inputQuery.trim()) return;
    navigate(`/track/${encodeURIComponent(inputQuery.trim())}`);
  };

  const getStatusBadgeClass = (status) => {
    switch (status?.toUpperCase()) {
      case 'BOOKED': return 'badge-booked';
      case 'PICKED_UP': return 'badge-picked_up';
      case 'IN_TRANSIT': return 'badge-in_transit';
      case 'ARRIVED_AT_HUB': return 'badge-arrived_at_hub';
      case 'OUT_FOR_DELIVERY': return 'badge-out_for_delivery';
      case 'DELIVERY_ATTEMPTED': return 'badge-delivery_attempted';
      case 'DELIVERED': return 'badge-delivered';
      default: return 'badge-pending';
    }
  };

  return (
    <div className="container" style={{ maxWidth: '900px', marginTop: '32px' }}>
      <div style={{ textAlign: 'center', marginBottom: '32px' }}>
        <h1 style={{ fontSize: '1.85rem', fontWeight: 700, color: 'var(--primary-navy)' }}>
          Consignment Tracking & Lifecycle
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', marginTop: '6px' }}>
          Real-time prototype tracking timeline with privacy protection
        </p>
      </div>

      {/* Search Input Box */}
      <div className="card" style={{ marginBottom: '28px', padding: '24px' }}>
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: '240px', position: 'relative' }}>
            <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              type="text"
              className="form-control"
              style={{ paddingLeft: '38px', fontSize: '1rem', height: '46px' }}
              placeholder="Enter Consignment Tracking ID (e.g. GPM-2026-000001)"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
            />
          </div>
          <button
            type="submit"
            className="btn btn-primary"
            style={{ height: '46px', padding: '0 24px', display: 'flex', alignItems: 'center', gap: '8px' }}
            disabled={loading}
          >
            {loading ? 'Searching...' : <><Search size={16} /> Track</>}
          </button>
          <Link
            to="/scan"
            className="btn btn-outline"
            style={{ height: '46px', padding: '0 18px', display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <QrCode size={16} /> Scan QR
          </Link>
        </form>
      </div>

      {error && (
        <div className="alert alert-error" style={{ marginBottom: '24px' }}>
          <AlertCircle size={20} />
          <div>
            <strong>Tracking Error:</strong> {error}
          </div>
        </div>
      )}

      {/* Tracking Details View */}
      {trackingData && (
        <div>
          {/* Summary Card */}
          <div className="card" style={{ marginBottom: '24px', padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', borderBottom: '1px solid #e2e8f0', paddingBottom: '18px', marginBottom: '18px' }}>
              <div>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Consignment Tracking Number
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '4px' }}>
                  <span className="tracking-pill" style={{ fontSize: '1.25rem' }}>
                    <Package size={20} color="#2563eb" />
                    {trackingData.tracking_id}
                  </span>
                  <span className={`badge ${getStatusBadgeClass(trackingData.current_status)}`} style={{ padding: '6px 14px', fontSize: '0.85rem' }}>
                    {trackingData.current_status.replace(/_/g, ' ')}
                  </span>
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Last Updated
                </span>
                <div style={{ fontSize: '0.9rem', color: 'var(--text-main)', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '6px', justifyContent: 'flex-end' }}>
                  <Clock size={15} color="var(--text-muted)" />
                  {trackingData.last_updated ? new Date(trackingData.last_updated).toLocaleString() : 'Recently'}
                </div>
              </div>
            </div>

            {/* Privacy Shield Info Bar */}
            <div className="alert alert-info" style={{ marginBottom: '18px', fontSize: '0.85rem' }}>
              <ShieldCheck size={18} />
              <div>
                <strong>Privacy Shield Active:</strong> Citizen names are masked in public tracking views. Contact numbers and complete residential addresses are strictly withheld.
              </div>
            </div>

            {/* Consignment Metadata Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
              <div style={{ background: '#f8fafc', padding: '14px', borderRadius: 'var(--radius)', border: '1px solid #e2e8f0' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Sender</span>
                <p style={{ fontWeight: 600, fontSize: '1rem', marginTop: '4px' }}>{trackingData.sender_masked}</p>
              </div>

              <div style={{ background: '#f8fafc', padding: '14px', borderRadius: 'var(--radius)', border: '1px solid #e2e8f0' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Recipient</span>
                <p style={{ fontWeight: 600, fontSize: '1rem', marginTop: '4px' }}>{trackingData.receiver_masked}</p>
              </div>

              <div style={{ background: '#f8fafc', padding: '14px', borderRadius: 'var(--radius)', border: '1px solid #e2e8f0' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Destination</span>
                <p style={{ fontWeight: 600, fontSize: '1rem', marginTop: '4px' }}>
                  {trackingData.destination_city} ({trackingData.destination_pin})
                </p>
              </div>
            </div>
          </div>

          {/* Chronological Timeline Card */}
          <div className="card" style={{ padding: '24px' }}>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--primary-navy)', marginBottom: '18px' }}>
              Tracking Event History ({trackingData.timeline?.length || 0} events)
            </h2>

            {(!trackingData.timeline || trackingData.timeline.length === 0) ? (
              <p style={{ color: 'var(--text-muted)' }}>No tracking events logged yet.</p>
            ) : (
              <div className="timeline-container">
                {trackingData.timeline.map((evt, idx) => {
                  const isLatest = idx === trackingData.timeline.length - 1;
                  const isDelivered = evt.new_status === 'DELIVERED';

                  return (
                    <div key={evt.id || idx} className="timeline-item">
                      <div className={`timeline-dot ${isDelivered ? 'success' : isLatest ? 'active' : ''}`}>
                        {isDelivered && <CheckCircle2 size={12} color="#ffffff" />}
                      </div>
                      <div className="timeline-content" style={{ borderColor: isLatest ? '#93c5fd' : '#e2e8f0' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '8px' }}>
                          <div>
                            <span className={`badge ${getStatusBadgeClass(evt.new_status)}`} style={{ marginRight: '8px' }}>
                              {evt.new_status.replace(/_/g, ' ')}
                            </span>
                            <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>
                              {evt.location_label}
                            </span>
                          </div>
                          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                            {new Date(evt.created_at).toLocaleString()}
                          </span>
                        </div>
                        <p style={{ color: 'var(--text-main)', fontSize: '0.9rem', marginTop: '8px' }}>
                          {evt.description}
                        </p>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginTop: '6px' }}>
                          Logged by: {evt.actor_type}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
