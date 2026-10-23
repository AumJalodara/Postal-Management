import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, PackageCheck, XCircle, Clock, ShieldCheck, MapPin } from 'lucide-react';
import api from '../services/api';
import StatusBadge from '../components/StatusBadge';

export default function PickupDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem('user') || '{}');

  const [pickup, setPickup] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState('');

  const fetchDetails = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/pickups/${id}`);
      setPickup(res.data.data);
    } catch (err) {
      console.error('Failed to load pickup details', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetails();
  }, [id]);

  const handleAgentAccept = async () => {
    setActionLoading(true);
    setMessage('');
    try {
      await api.post(`/agent/pickups/${id}/accept`, {
        reason: 'Pickup accepted by assigned delivery agent',
      });
      setMessage('Pickup request accepted successfully.');
      await fetchDetails();
    } catch (err) {
      alert(err.response?.data?.error?.message || 'Action failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleAgentComplete = async () => {
    setActionLoading(true);
    setMessage('');
    try {
      await api.post(`/agent/pickups/${id}/complete`, {
        reason: 'Consignment collected from citizen doorstep',
      });
      setMessage('Consignment marked as PICKED_UP.');
      await fetchDetails();
    } catch (err) {
      alert(err.response?.data?.error?.message || 'Action failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCitizenCancel = async () => {
    if (!window.confirm('Are you sure you want to cancel this doorstep pickup?')) return;
    setActionLoading(true);
    setMessage('');
    try {
      await api.post(`/pickups/${id}/cancel`, {
        reason: 'Cancelled by citizen from details page',
      });
      setMessage('Doorstep pickup cancelled.');
      await fetchDetails();
    } catch (err) {
      alert(err.response?.data?.error?.message || 'Cancellation failed.');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="container">
        <p style={{ color: '#64748b', padding: '40px 0' }}>Loading pickup details...</p>
      </div>
    );
  }

  if (!pickup) {
    return (
      <div className="container">
        <div className="alert alert-error">Pickup request not found or access denied.</div>
        <button onClick={() => navigate(-1)} className="btn btn-outline">
          <ArrowLeft size={16} /> Go Back
        </button>
      </div>
    );
  }

  const isAgent = user.role === 'AGENT';
  const isCitizen = user.role === 'CITIZEN';

  return (
    <div className="container" style={{ maxWidth: '960px' }}>
      <button
        onClick={() => navigate(-1)}
        className="btn btn-outline btn-sm"
        style={{ marginBottom: '16px' }}
      >
        <ArrowLeft size={14} /> Back
      </button>

      <div className="page-header" style={{ marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h2 className="page-title">Doorstep Pickup #{pickup.id}</h2>
            <StatusBadge status={pickup.status} />
          </div>
          <p className="page-subtitle">Consignment: {pickup.parcel?.tracking_id}</p>
        </div>

        {/* Action controls */}
        <div style={{ display: 'flex', gap: '10px' }}>
          {isAgent && pickup.status === 'ASSIGNED' && (
            <button
              onClick={handleAgentAccept}
              className="btn btn-primary"
              disabled={actionLoading}
            >
              <CheckCircle2 size={16} /> {actionLoading ? 'Accepting...' : 'Accept Pickup'}
            </button>
          )}

          {isAgent && pickup.status === 'ACCEPTED' && (
            <button
              onClick={handleAgentComplete}
              className="btn btn-success"
              disabled={actionLoading}
            >
              <PackageCheck size={16} /> {actionLoading ? 'Completing...' : 'Mark Picked Up'}
            </button>
          )}

          {isCitizen && (pickup.status === 'PENDING' || pickup.status === 'ASSIGNED') && (
            <button
              onClick={handleCitizenCancel}
              className="btn btn-danger"
              disabled={actionLoading}
            >
              <XCircle size={16} /> {actionLoading ? 'Cancelling...' : 'Cancel Pickup'}
            </button>
          )}
        </div>
      </div>

      {message && (
        <div className="alert alert-success">
          <CheckCircle2 size={18} />
          <span>{message}</span>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px' }}>
        {/* Pickup Details Card */}
        <div className="card">
          <h3 className="card-title">Pickup & Scheduling Details</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '0.9rem' }}>
            <div>
              <span style={{ color: '#64748b', display: 'block', fontSize: '0.8rem' }}>Pickup Address:</span>
              <strong style={{ display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
                <MapPin size={16} color="#ea580c" style={{ flexShrink: 0, marginTop: '2px' }} />
                {pickup.pickup_address}, {pickup.pickup_city}, {pickup.pickup_state} — PIN {pickup.pickup_pin}
              </strong>
            </div>

            <div>
              <span style={{ color: '#64748b', display: 'block', fontSize: '0.8rem' }}>Collection Date:</span>
              <strong>{pickup.requested_date}</strong>
            </div>

            <div>
              <span style={{ color: '#64748b', display: 'block', fontSize: '0.8rem' }}>Assigned Delivery Agent:</span>
              {pickup.assigned_agent_id ? (
                <strong style={{ color: '#1e40af' }}>Delivery Agent #{pickup.assigned_agent_id}</strong>
              ) : (
                <span style={{ color: '#b45309', fontStyle: 'italic' }}>Pending Agent Allocation</span>
              )}
            </div>

            <div>
              <span style={{ color: '#64748b', display: 'block', fontSize: '0.8rem' }}>Idempotency Token:</span>
              <code style={{ fontSize: '0.75rem', background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px' }}>
                {pickup.idempotency_key}
              </code>
            </div>
          </div>
        </div>

        {/* Parcel Details Card */}
        <div className="card">
          <h3 className="card-title">Associated Consignment</h3>
          {pickup.parcel ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '0.9rem' }}>
              <div>
                <span style={{ color: '#64748b', display: 'block', fontSize: '0.8rem' }}>Tracking Identifier:</span>
                <span className="tracking-pill">{pickup.parcel.tracking_id}</span>
              </div>

              <div>
                <span style={{ color: '#64748b', display: 'block', fontSize: '0.8rem' }}>Consignee / Receiver:</span>
                <strong>{pickup.parcel.receiver_name}</strong> ({pickup.parcel.receiver_phone})
              </div>

              <div>
                <span style={{ color: '#64748b', display: 'block', fontSize: '0.8rem' }}>Destination Address:</span>
                <div>{pickup.parcel.destination_address}</div>
                <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                  {pickup.parcel.destination_city}, {pickup.parcel.destination_state} ({pickup.parcel.destination_pin})
                </div>
              </div>

              <div>
                <span style={{ color: '#64748b', display: 'block', fontSize: '0.8rem' }}>Weight & Classification:</span>
                <strong>{pickup.parcel.weight} kg</strong> | {pickup.parcel.parcel_type} ({pickup.parcel.priority})
              </div>
            </div>
          ) : (
            <p style={{ color: '#64748b' }}>No parcel details attached.</p>
          )}
        </div>
      </div>

      {/* State Machine Chronological Audit Trail */}
      <div className="card">
        <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldCheck size={20} color="#059669" /> Status Lifecycle & Audit Trail
        </h3>
        <p style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '16px' }}>
          Chronological record of every verified state machine transition.
        </p>

        {pickup.history && pickup.history.length > 0 ? (
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Transition</th>
                  <th>Actor Role</th>
                  <th>Reason / Remarks</th>
                </tr>
              </thead>
              <tbody>
                {pickup.history.map((h) => (
                  <tr key={h.id}>
                    <td>
                      {new Date(h.created_at).toLocaleString(undefined, {
                        dateStyle: 'medium',
                        timeStyle: 'short',
                      })}
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        {h.old_status ? (
                          <>
                            <span style={{ fontSize: '0.78rem', color: '#64748b' }}>{h.old_status}</span>
                            <span>→</span>
                          </>
                        ) : (
                          <span style={{ fontSize: '0.78rem', color: '#64748b' }}>Initial</span>
                        )}
                        <StatusBadge status={h.new_status} />
                      </div>
                    </td>
                    <td>
                      <span className="user-badge" style={{ fontSize: '0.7rem' }}>
                        {h.changed_by_role}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.85rem', color: '#334e68' }}>{h.reason || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p style={{ color: '#64748b' }}>No status history recorded yet.</p>
        )}
      </div>
    </div>
  );
}
