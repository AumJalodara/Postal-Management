import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Truck, Package, ShieldCheck, CheckCircle2, AlertTriangle, ArrowRight, RefreshCw, MapPin } from 'lucide-react';
import api from '../services/api';

export default function AgentDeliveryQueue() {
  const [parcels, setParcels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  useEffect(() => {
    fetchDeliveryQueue();
  }, []);

  const fetchDeliveryQueue = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get('/agent/deliveries');
      setParcels(res.data.data);
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to load delivery queue.');
    } finally {
      setLoading(false);
    }
  };

  const updateParcelStatus = async (trackingId, newStatus) => {
    setActionLoading(trackingId);
    setError('');
    setSuccessMsg('');
    try {
      await api.post(`/agent/parcels/${trackingId}/events`, {
        new_status: newStatus,
        location_label: 'Local Delivery Branch',
        description: `Status advanced to ${newStatus.replace(/_/g, ' ')} by delivery agent.`
      });
      setSuccessMsg(`Parcel ${trackingId} updated to ${newStatus}.`);
      fetchDeliveryQueue();
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to update parcel status.');
    } finally {
      setActionLoading(null);
    }
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
    <div className="container" style={{ maxWidth: '1100px', marginTop: '32px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '14px' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--primary-navy)' }}>
            Delivery Queue & Hub Operations
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '4px' }}>
            Process outgoing consignments, dispatch for delivery, and verify recipient OTP
          </p>
        </div>
        <button
          onClick={fetchDeliveryQueue}
          className="btn btn-outline btn-sm"
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <RefreshCw size={15} /> Refresh Queue
        </button>
      </div>

      {error && (
        <div className="alert alert-error" style={{ marginBottom: '20px' }}>
          <div>{error}</div>
        </div>
      )}

      {successMsg && (
        <div className="alert alert-success" style={{ marginBottom: '20px' }}>
          <div>{successMsg}</div>
        </div>
      )}

      <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
            Loading delivery queue...
          </div>
        ) : parcels.length === 0 ? (
          <div style={{ padding: '48px 24px', textAlign: 'center' }}>
            <Package size={48} color="#94a3b8" style={{ marginBottom: '12px' }} />
            <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>No active deliveries found</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '4px' }}>
              Consignments assigned to your facility or in transit will appear here.
            </p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>Tracking ID</th>
                  <th>Recipient Details</th>
                  <th>Destination Address</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {parcels.map((p) => (
                  <tr key={p.id}>
                    <td>
                      <span className="tracking-pill" style={{ fontSize: '0.85rem' }}>
                        {p.tracking_id}
                      </span>
                      <div style={{ marginTop: '4px' }}>
                        <Link
                          to={`/track/${p.tracking_id}`}
                          style={{ fontSize: '0.75rem', color: '#2563eb', textDecoration: 'none' }}
                        >
                          View History
                        </Link>
                      </div>
                    </td>
                    <td>
                      <div style={{ fontWeight: 600 }}>{p.receiver_name}</div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{p.receiver_phone}</div>
                    </td>
                    <td>
                      <div style={{ fontSize: '0.85rem' }}>{p.destination_address}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '2px' }}>
                        <MapPin size={12} /> {p.destination_city} - {p.destination_pin}
                      </div>
                    </td>
                    <td>
                      <span className={`badge ${getStatusBadgeClass(p.status)}`}>
                        {p.status.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        {p.status === 'PICKED_UP' && (
                          <button
                            onClick={() => updateParcelStatus(p.tracking_id, 'IN_TRANSIT')}
                            className="btn btn-outline btn-sm"
                            disabled={actionLoading === p.tracking_id}
                          >
                            Mark In Transit
                          </button>
                        )}

                        {p.status === 'IN_TRANSIT' && (
                          <button
                            onClick={() => updateParcelStatus(p.tracking_id, 'ARRIVED_AT_HUB')}
                            className="btn btn-outline btn-sm"
                            disabled={actionLoading === p.tracking_id}
                          >
                            Receive at Hub
                          </button>
                        )}

                        {(p.status === 'ARRIVED_AT_HUB' || p.status === 'DELIVERY_ATTEMPTED') && (
                          <button
                            onClick={() => updateParcelStatus(p.tracking_id, 'OUT_FOR_DELIVERY')}
                            className="btn btn-outline btn-sm"
                            style={{ borderColor: '#f97316', color: '#c2410c' }}
                            disabled={actionLoading === p.tracking_id}
                          >
                            Dispatch for Delivery
                          </button>
                        )}

                        {p.status === 'OUT_FOR_DELIVERY' && (
                          <>
                            <Link
                              to={`/agent/deliveries/${p.tracking_id}/verify`}
                              className="btn btn-success btn-sm"
                              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                            >
                              <ShieldCheck size={14} /> Verify OTP & Deliver
                            </Link>

                            <button
                              onClick={() => updateParcelStatus(p.tracking_id, 'DELIVERY_ATTEMPTED')}
                              className="btn btn-outline btn-sm"
                              style={{ borderColor: '#ef4444', color: '#b91c1c' }}
                              disabled={actionLoading === p.tracking_id}
                            >
                              Attempt Failed
                            </button>
                          </>
                        )}

                        {p.status === 'DELIVERED' && (
                          <span style={{ fontSize: '0.8rem', color: '#16a34a', display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <CheckCircle2 size={16} /> Delivered
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
