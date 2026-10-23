import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Package, Truck, LogOut, User, Send, ListOrdered, Calendar, Search, QrCode, ShieldCheck, MessageSquare } from 'lucide-react';

export default function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const userJson = localStorage.getItem('user');
  const user = userJson ? JSON.parse(userJson) : null;

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  return (
    <header className="sidebar-header">
      <div className="tricolor-strip"></div>
      <nav className="navbar">
        <Link to="/" className="navbar-brand">
          <div style={{ background: '#d97706', padding: '6px', borderRadius: '6px', display: 'flex' }}>
            <Package size={22} color="#fff" />
          </div>
          <div>
            <h1>Smart Postal System</h1>
          </div>
        </Link>

        <div className="nav-links">
          {/* Public Track Link available to all */}
          <Link
            to="/track"
            className={`nav-link ${location.pathname.startsWith('/track') ? 'active' : ''}`}
          >
            <Search size={15} /> Track Parcel
          </Link>

          {/* Public QR Scanner */}
          <Link
            to="/scan"
            className={`nav-link ${location.pathname === '/scan' ? 'active' : ''}`}
          >
            <QrCode size={15} /> Scan QR
          </Link>

          {/* Public Postal Assistant */}
          <Link
            to="/assistant"
            className={`nav-link ${location.pathname === '/assistant' ? 'active' : ''}`}
          >
            <MessageSquare size={15} /> Postal Assistant
          </Link>

          {user ? (
            <>
              {user.role === 'CITIZEN' && (
                <>
                  <Link
                    to="/dashboard"
                    className={`nav-link ${location.pathname === '/dashboard' ? 'active' : ''}`}
                  >
                    Dashboard
                  </Link>
                  <Link
                    to="/parcels/new"
                    className={`nav-link ${location.pathname === '/parcels/new' ? 'active' : ''}`}
                  >
                    <Send size={15} /> Book Parcel
                  </Link>
                  <Link
                    to="/parcels/my"
                    className={`nav-link ${location.pathname === '/parcels/my' ? 'active' : ''}`}
                  >
                    <ListOrdered size={15} /> My Parcels
                  </Link>
                  <Link
                    to="/pickups/new"
                    className={`nav-link ${location.pathname === '/pickups/new' ? 'active' : ''}`}
                  >
                    <Calendar size={15} /> Request Pickup
                  </Link>
                  <Link
                    to="/pickups/my"
                    className={`nav-link ${location.pathname === '/pickups/my' ? 'active' : ''}`}
                  >
                    <Truck size={15} /> My Pickups
                  </Link>
                </>
              )}

              {user.role === 'AGENT' && (
                <>
                  <Link
                    to="/agent/dashboard"
                    className={`nav-link ${location.pathname === '/agent/dashboard' ? 'active' : ''}`}
                  >
                    <Truck size={15} /> Pickups
                  </Link>
                  <Link
                    to="/agent/deliveries"
                    className={`nav-link ${location.pathname.startsWith('/agent/deliveries') ? 'active' : ''}`}
                  >
                    <ShieldCheck size={15} /> Delivery Queue
                  </Link>
                </>
              )}

              {user.role === 'ADMIN' && (
                <Link
                  to="/admin/operations"
                  className={`nav-link ${location.pathname.startsWith('/admin/operations') ? 'active' : ''}`}
                >
                  <ShieldCheck size={15} /> Operations
                </Link>
              )}

              <div className="nav-user">
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>{user.name}</span>
                  <span className="user-badge">{user.role}</span>
                </div>
                <button
                  onClick={handleLogout}
                  className="btn btn-outline btn-sm"
                  style={{ color: '#ffffff', borderColor: 'rgba(255,255,255,0.3)', padding: '5px 10px' }}
                  title="Logout"
                >
                  <LogOut size={14} /> Logout
                </button>
              </div>
            </>
          ) : (
            <>
              <Link
                to="/login"
                className={`nav-link ${location.pathname === '/login' ? 'active' : ''}`}
              >
                Login
              </Link>
              <Link
                to="/register"
                className="btn btn-accent btn-sm"
              >
                Citizen Registration
              </Link>
            </>
          )}

        </div>
      </nav>
    </header>
  );
}


