import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Package, Calendar, Send, Copy, Check, QrCode, Search } from 'lucide-react';
import api from '../services/api';

export default function MyParcels() {
  const [parcels, setParcels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [copiedId, setCopiedId] = useState(null);

  useEffect(() => {
    async function fetchParcels() {
      try {
        const res = await api.get('/parcels/my');
        setParcels(res.data.data || []);
      } catch (err) {
        console.error('Failed to load parcels', err);
      } finally {
        setLoading(false);
      }
    }
    fetchParcels();
  }, []);

  const handleCopy = (tid) => {
    navigator.clipboard.writeText(tid);
    setCopiedId(tid);
    setTimeout(() => setCopiedId(null), 2000);
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
    <div className="container">
      <div className="page-header">
        <div>
          <h2 className="page-title">My Booked Parcels</h2>
          <p className="page-subtitle">View all registered consignments, track timelines, and download QR codes.</p>
        </div>
        <Link to="/parcels/new" className="btn btn-primary">
          <Send size={16} /> Book New Parcel
        </Link>
      </div>

      <div className="card">
        {loading ? (
          <p style={{ color: '#64748b', padding: '20px 0' }}>Loading your parcels...</p>
        ) : parcels.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '48px 0', color: '#64748b' }}>
            <Package size={48} style={{ opacity: 0.3, marginBottom: '12px' }} />
            <h3 style={{ fontSize: '1.1rem', color: '#1e293b', marginBottom: '6px' }}>No Parcels Found</h3>
            <p style={{ fontSize: '0.9rem', marginBottom: '16px' }}>You haven't booked any parcels yet.</p>
            <Link to="/parcels/new" className="btn btn-primary btn-sm">
              Book a Parcel Now
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
                  <th>Status</th>
                  <th>Type & Priority</th>
                  <th>Date Booked</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {parcels.map((p) => (
                  <tr key={p.id}>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span className="tracking-pill">{p.tracking_id}</span>
                        <button
                          onClick={() => handleCopy(p.tracking_id)}
                          className="btn btn-outline btn-sm"
                          style={{ padding: '4px 6px' }}
                          title="Copy tracking ID"
                        >
                          {copiedId === p.tracking_id ? <Check size={12} color="#059669" /> : <Copy size={12} />}
                        </button>
                      </div>
                    </td>
                    <td>
                      <div style={{ fontWeight: 600 }}>{p.receiver_name}</div>
                      <div style={{ fontSize: '0.8rem', color: '#64748b' }}>{p.receiver_phone}</div>
                    </td>
                    <td>
                      <div>{p.destination_city}, {p.destination_state}</div>
                      <div style={{ fontSize: '0.8rem', color: '#64748b' }}>PIN: {p.destination_pin}</div>
                    </td>
                    <td>
                      <span className={`badge ${getStatusBadgeClass(p.status)}`}>
                        {(p.status || 'BOOKED').replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td>
                      <div>{p.parcel_type}</div>
                      <span style={{ fontSize: '0.75rem', fontWeight: 600, color: p.priority === 'EXPRESS' ? '#ea580c' : '#64748b' }}>
                        {p.priority}
                      </span>
                    </td>
                    <td>
                      {new Date(p.created_at).toLocaleDateString(undefined, {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                        <Link
                          to={`/track/${p.tracking_id}`}
                          className="btn btn-outline btn-sm"
                          style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                        >
                          <Search size={13} /> Track
                        </Link>
                        <Link
                          to={`/parcels/${p.tracking_id}/qr`}
                          className="btn btn-outline btn-sm"
                          style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                        >
                          <QrCode size={13} /> QR
                        </Link>
                        {p.status === 'BOOKED' && (
                          <Link
                            to={`/pickups/new?parcel_id=${p.id}`}
                            className="btn btn-outline btn-sm"
                            style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                          >
                            <Calendar size={13} /> Pickup
                          </Link>
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
