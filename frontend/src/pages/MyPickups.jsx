import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Truck, Calendar, AlertCircle, XCircle } from 'lucide-react';
import api from '../services/api';
import StatusBadge from '../components/StatusBadge';

export default function MyPickups() {
  const [pickups, setPickups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [cancellingId, setCancellingId] = useState(null);
  const [message, setMessage] = useState('');

  const fetchPickups = async () => {
    try {
      const res = await api.get('/pickups/my');
      setPickups(res.data.data || []);
    } catch (err) {
      console.error('Failed to load pickups', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPickups();
  }, []);

  const handleCancel = async (id) => {
    if (!window.confirm(`Are you sure you want to cancel Pickup Request #${id}?`)) {
      return;
    }
    setCancellingId(id);
    setMessage('');
    try {
      await api.post(`/pickups/${id}/cancel`, {
        reason: 'Cancelled by citizen request from dashboard',
      });
      setMessage(`Pickup Request #${id} was cancelled successfully.`);
      await fetchPickups();
    } catch (err) {
      const msg = err.response?.data?.error?.message || 'Failed to cancel pickup request.';
      alert(msg);
    } finally {
      setCancellingId(null);
    }
  };

  return (
    <div className="container">
      <div className="page-header">
        <div>
          <h2 className="page-title">Doorstep Pickups</h2>
          <p className="page-subtitle">Track pickup statuses, view assigned postal agents, and manage requests.</p>
        </div>
        <Link to="/pickups/new" className="btn btn-accent">
          <Calendar size={16} /> Request New Pickup
        </Link>
      </div>

      {message && (
        <div className="alert alert-info">
          <AlertCircle size={18} />
          <span>{message}</span>
        </div>
      )}

      <div className="card">
        {loading ? (
          <p style={{ color: '#64748b', padding: '20px 0' }}>Loading pickup requests...</p>
        ) : pickups.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '48px 0', color: '#64748b' }}>
            <Truck size={48} style={{ opacity: 0.3, marginBottom: '12px' }} />
            <h3 style={{ fontSize: '1.1rem', color: '#1e293b', marginBottom: '6px' }}>No Pickup Requests</h3>
            <p style={{ fontSize: '0.9rem', marginBottom: '16px' }}>You have not scheduled any doorstep collections.</p>
            <Link to="/pickups/new" className="btn btn-accent btn-sm">
              Schedule a Pickup
            </Link>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>Request ID</th>
                  <th>Tracking ID</th>
                  <th>Pickup Address</th>
                  <th>Scheduled Date</th>
                  <th>Assigned Agent</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {pickups.map((pu) => {
                  const canCancel = pu.status === 'PENDING' || pu.status === 'ASSIGNED';
                  return (
                    <tr key={pu.id}>
                      <td>
                        <strong>#{pu.id}</strong>
                      </td>
                      <td>
                        <span className="tracking-pill">{pu.parcel?.tracking_id}</span>
                      </td>
                      <td>
                        <div>{pu.pickup_address}</div>
                        <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                          {pu.pickup_city}, {pu.pickup_state} ({pu.pickup_pin})
                        </div>
                      </td>
                      <td>{pu.requested_date}</td>
                      <td>
                        {pu.assigned_agent_id ? (
                          <span style={{ fontWeight: 600, color: '#1e40af' }}>
                            Agent #{pu.assigned_agent_id}
                          </span>
                        ) : (
                          <span style={{ color: '#94a3b8', fontStyle: 'italic' }}>Awaiting Agent</span>
                        )}
                      </td>
                      <td>
                        <StatusBadge status={pu.status} />
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                          <Link to={`/pickups/${pu.id}`} className="btn btn-outline btn-sm">
                            View
                          </Link>
                          {canCancel && (
                            <button
                              onClick={() => handleCancel(pu.id)}
                              className="btn btn-danger btn-sm"
                              disabled={cancellingId === pu.id}
                              title="Cancel this pickup"
                            >
                              <XCircle size={13} /> {cancellingId === pu.id ? '...' : 'Cancel'}
                            </button>
                          )}
                        </div>
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
  );
}
