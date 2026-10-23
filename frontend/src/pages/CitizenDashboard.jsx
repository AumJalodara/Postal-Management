import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Package, Truck, Calendar, Send, ArrowRight, Clock, CheckCircle } from 'lucide-react';
import api from '../services/api';
import StatusBadge from '../components/StatusBadge';

export default function CitizenDashboard() {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const [parcels, setParcels] = useState([]);
  const [pickups, setPickups] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [parcelsRes, pickupsRes] = await Promise.all([
          api.get('/parcels/my'),
          api.get('/pickups/my'),
        ]);
        setParcels(parcelsRes.data.data || []);
        setPickups(pickupsRes.data.data || []);
      } catch (err) {
        console.error('Failed to load dashboard data', err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const activePickups = pickups.filter(
    (p) => p.status === 'PENDING' || p.status === 'ASSIGNED' || p.status === 'ACCEPTED'
  );
  const completedPickups = pickups.filter((p) => p.status === 'PICKED_UP');

  return (
    <div className="container">
      <div className="page-header">
        <div>
          <h2 className="page-title">Citizen Postal Services</h2>
          <p className="page-subtitle">Welcome back, {user.name}. Manage your parcels and doorstep collections.</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <Link to="/parcels/new" className="btn btn-primary">
            <Send size={16} /> Book New Parcel
          </Link>
          <Link to="/pickups/new" className="btn btn-accent">
            <Calendar size={16} /> Request Pickup
          </Link>
        </div>
      </div>

      {/* Stats row */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">
            <Package size={24} />
          </div>
          <div>
            <div className="stat-val">{parcels.length}</div>
            <div className="stat-label">Parcels Booked</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ color: '#d97706', backgroundColor: '#fef3c7' }}>
            <Clock size={24} />
          </div>
          <div>
            <div className="stat-val">{activePickups.length}</div>
            <div className="stat-label">Active Pickup Requests</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ color: '#059669', backgroundColor: '#d1fae5' }}>
            <CheckCircle size={24} />
          </div>
          <div>
            <div className="stat-val">{completedPickups.length}</div>
            <div className="stat-label">Parcels Picked Up</div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))', gap: '24px' }}>
        {/* Recent Parcels */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 className="card-title" style={{ margin: 0, border: 'none', padding: 0 }}>
              Recent Booked Parcels
            </h3>
            <Link to="/parcels/my" style={{ fontSize: '0.85rem', color: '#ea580c', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
              View All <ArrowRight size={14} />
            </Link>
          </div>

          {loading ? (
            <p style={{ color: '#64748b' }}>Loading parcels...</p>
          ) : parcels.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '30px 0', color: '#64748b' }}>
              <Package size={36} style={{ opacity: 0.4, marginBottom: '8px' }} />
              <p>You haven't booked any parcels yet.</p>
              <Link to="/parcels/new" className="btn btn-outline btn-sm" style={{ marginTop: '10px' }}>
                Book Your First Parcel
              </Link>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table">
                <thead>
                  <tr>
                    <th>Tracking ID</th>
                    <th>Receiver</th>
                    <th>Destination</th>
                    <th>Type</th>
                  </tr>
                </thead>
                <tbody>
                  {parcels.slice(0, 5).map((p) => (
                    <tr key={p.id}>
                      <td>
                        <span className="tracking-pill">{p.tracking_id}</span>
                      </td>
                      <td>{p.receiver_name}</td>
                      <td>{p.destination_city} ({p.destination_pin})</td>
                      <td>{p.parcel_type}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Recent Pickups */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 className="card-title" style={{ margin: 0, border: 'none', padding: 0 }}>
              Recent Doorstep Pickups
            </h3>
            <Link to="/pickups/my" style={{ fontSize: '0.85rem', color: '#ea580c', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
              View All <ArrowRight size={14} />
            </Link>
          </div>

          {loading ? (
            <p style={{ color: '#64748b' }}>Loading pickups...</p>
          ) : pickups.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '30px 0', color: '#64748b' }}>
              <Truck size={36} style={{ opacity: 0.4, marginBottom: '8px' }} />
              <p>No doorstep pickup requests scheduled.</p>
              <Link to="/pickups/new" className="btn btn-outline btn-sm" style={{ marginTop: '10px' }}>
                Schedule Doorstep Pickup
              </Link>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table">
                <thead>
                  <tr>
                    <th>Pickup ID</th>
                    <th>Date</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {pickups.slice(0, 5).map((pu) => (
                    <tr key={pu.id}>
                      <td>#{pu.id}</td>
                      <td>{pu.requested_date}</td>
                      <td>
                        <StatusBadge status={pu.status} />
                      </td>
                      <td>
                        <Link to={`/pickups/${pu.id}`} className="btn btn-outline btn-sm">
                          Details
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
