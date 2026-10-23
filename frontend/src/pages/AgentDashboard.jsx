import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Truck, CheckCircle2, PackageCheck, AlertCircle, RefreshCw } from 'lucide-react';
import api from '../services/api';
import StatusBadge from '../components/StatusBadge';

export default function AgentDashboard() {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const [pickups, setPickups] = useState([]);
  const [filter, setFilter] = useState('ALL');
  const [loading, setLoading] = useState(true);
  const [actionLoadingId, setActionLoadingId] = useState(null);
  const [actionMessage, setActionMessage] = useState('');

  const fetchAssignedPickups = async () => {
    setLoading(true);
    try {
      const res = await api.get('/agent/pickups');
      setPickups(res.data.data || []);
    } catch (err) {
      console.error('Failed to fetch assigned pickups', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssignedPickups();
  }, []);

  const handleAccept = async (id) => {
    setActionLoadingId(id);
    setActionMessage('');
    try {
      await api.post(`/agent/pickups/${id}/accept`, {
        reason: 'Pickup accepted by assigned delivery agent',
      });
      setActionMessage(`Pickup #${id} accepted successfully!`);
      await fetchAssignedPickups();
    } catch (err) {
      const msg = err.response?.data?.error?.message || 'Failed to accept pickup.';
      alert(msg);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleComplete = async (id) => {
    setActionLoadingId(id);
    setActionMessage('');
    try {
      await api.post(`/agent/pickups/${id}/complete`, {
        reason: 'Parcel physically collected from doorstep',
      });
      setActionMessage(`Pickup #${id} marked as PICKED_UP successfully!`);
      await fetchAssignedPickups();
    } catch (err) {
      const msg = err.response?.data?.error?.message || 'Failed to complete pickup.';
      alert(msg);
    } finally {
      setActionLoadingId(null);
    }
  };

  const filteredPickups = pickups.filter((p) => {
    if (filter === 'ALL') return true;
    return p.status === filter;
  });

  const assignedCount = pickups.filter((p) => p.status === 'ASSIGNED').length;
  const acceptedCount = pickups.filter((p) => p.status === 'ACCEPTED').length;
  const completedCount = pickups.filter((p) => p.status === 'PICKED_UP').length;

  return (
    <div className="container">
      <div className="page-header">
        <div>
          <h2 className="page-title">Delivery Agent Workspace</h2>
          <p className="page-subtitle">Logged in as {user.name} ({user.email})</p>
        </div>
        <button
          onClick={fetchAssignedPickups}
          className="btn btn-outline"
          disabled={loading}
        >
          <RefreshCw size={15} /> Refresh List
        </button>
      </div>

      {actionMessage && (
        <div className="alert alert-success">
          <CheckCircle2 size={18} />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* Summary counters */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon" style={{ color: '#1e40af', backgroundColor: '#dbeafe' }}>
            <Truck size={24} />
          </div>
          <div>
            <div className="stat-val">{assignedCount}</div>
            <div className="stat-label">Awaiting Acceptance</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ color: '#5b21b6', backgroundColor: '#ede9fe' }}>
            <CheckCircle2 size={24} />
          </div>
          <div>
            <div className="stat-val">{acceptedCount}</div>
            <div className="stat-label">Accepted (Ready to Collect)</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ color: '#065f46', backgroundColor: '#d1fae5' }}>
            <PackageCheck size={24} />
          </div>
          <div>
            <div className="stat-val">{completedCount}</div>
            <div className="stat-label">Completed Pickups</div>
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
        {['ALL', 'ASSIGNED', 'ACCEPTED', 'PICKED_UP'].map((tab) => (
          <button
            key={tab}
            onClick={() => setFilter(tab)}
            className={`btn btn-sm ${filter === tab ? 'btn-primary' : 'btn-outline'}`}
          >
            {tab === 'ALL' ? 'All Assigned' : tab.replace('_', ' ')}
          </button>
        ))}
      </div>

      <div className="card">
        {loading ? (
          <p style={{ color: '#64748b', padding: '20px 0' }}>Loading assigned pickups...</p>
        ) : filteredPickups.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '48px 0', color: '#64748b' }}>
            <Truck size={48} style={{ opacity: 0.3, marginBottom: '12px' }} />
            <h3>No Pickups Found</h3>
            <p style={{ fontSize: '0.9rem' }}>No pickups matching this status are currently assigned to you.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Tracking ID</th>
                  <th>Pickup Address</th>
                  <th>Scheduled Date</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredPickups.map((pu) => (
                  <tr key={pu.id}>
                    <td><strong>#{pu.id}</strong></td>
                    <td>
                      <span className="tracking-pill">{pu.parcel?.tracking_id}</span>
                    </td>
                    <td>
                      <div>{pu.pickup_address}</div>
                      <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                        {pu.pickup_city} — PIN {pu.pickup_pin}
                      </div>
                    </td>
                    <td>{pu.requested_date}</td>
                    <td>
                      <StatusBadge status={pu.status} />
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <Link to={`/pickups/${pu.id}`} className="btn btn-outline btn-sm">
                          Details
                        </Link>

                        {pu.status === 'ASSIGNED' && (
                          <button
                            onClick={() => handleAccept(pu.id)}
                            className="btn btn-primary btn-sm"
                            disabled={actionLoadingId === pu.id}
                          >
                            <CheckCircle2 size={13} /> {actionLoadingId === pu.id ? '...' : 'Accept'}
                          </button>
                        )}

                        {pu.status === 'ACCEPTED' && (
                          <button
                            onClick={() => handleComplete(pu.id)}
                            className="btn btn-success btn-sm"
                            disabled={actionLoadingId === pu.id}
                          >
                            <PackageCheck size={13} /> {actionLoadingId === pu.id ? '...' : 'Mark Picked Up'}
                          </button>
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
