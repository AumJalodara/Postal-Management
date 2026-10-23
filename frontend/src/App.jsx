import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import ProtectedRoute from './routes/ProtectedRoute';

import Login from './pages/Login';
import Register from './pages/Register';
import CitizenDashboard from './pages/CitizenDashboard';
import CreateParcel from './pages/CreateParcel';
import MyParcels from './pages/MyParcels';
import CreatePickup from './pages/CreatePickup';
import MyPickups from './pages/MyPickups';
import AgentDashboard from './pages/AgentDashboard';
import PickupDetails from './pages/PickupDetails';

// Module 2 Pages
import TrackParcel from './pages/TrackParcel';
import QRCodeDisplay from './pages/QRCodeDisplay';
import QRScanner from './pages/QRScanner';
import AgentDeliveryQueue from './pages/AgentDeliveryQueue';
import DeliveryVerification from './pages/DeliveryVerification';

// Module 3 Pages
import PostalAssistant from './pages/PostalAssistant';

// Module 4 Pages
import OperationsDashboard from './pages/OperationsDashboard';

function RootRedirect() {
  const token = localStorage.getItem('token');
  const userJson = localStorage.getItem('user');
  if (!token || !userJson) {
    return <Navigate to="/track" replace />;
  }
  try {
    const user = JSON.parse(userJson);
    if (user.role === 'ADMIN') {
      return <Navigate to="/admin/operations" replace />;
    }
    if (user.role === 'AGENT') {
      return <Navigate to="/agent/dashboard" replace />;
    }
    return <Navigate to="/dashboard" replace />;
  } catch (e) {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    return <Navigate to="/track" replace />;
  }
}


export default function App() {
  return (
    <BrowserRouter>
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'row' }}>
        <Navbar />
        <main style={{ flex: 1, minWidth: 0, paddingBottom: '40px' }}>
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<RootRedirect />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            {/* Public Tracking & QR Routes */}
            <Route path="/track" element={<TrackParcel />} />
            <Route path="/track/:trackingId" element={<TrackParcel />} />
            <Route path="/track/qr/:qrToken" element={<TrackParcel />} />
            <Route path="/scan" element={<QRScanner />} />
            <Route path="/assistant" element={<PostalAssistant />} />

            {/* Citizen Protected Routes */}
            <Route element={<ProtectedRoute allowedRoles={['CITIZEN', 'ADMIN']} />}>
              <Route path="/dashboard" element={<CitizenDashboard />} />
              <Route path="/parcels/new" element={<CreateParcel />} />
              <Route path="/parcels/my" element={<MyParcels />} />
              <Route path="/pickups/new" element={<CreatePickup />} />
              <Route path="/pickups/my" element={<MyPickups />} />
            </Route>

            {/* Agent Protected Routes */}
            <Route element={<ProtectedRoute allowedRoles={['AGENT', 'ADMIN']} />}>
              <Route path="/agent/dashboard" element={<AgentDashboard />} />
              <Route path="/agent/deliveries" element={<AgentDeliveryQueue />} />
              <Route path="/agent/deliveries/:trackingId/verify" element={<DeliveryVerification />} />
            </Route>

            {/* Admin Protected Routes */}
            <Route element={<ProtectedRoute allowedRoles={['ADMIN']} />}>
              <Route path="/admin/operations" element={<OperationsDashboard />} />
              <Route path="/operations" element={<OperationsDashboard />} />
            </Route>

            {/* Shared Protected Routes (Citizen, Agent, Admin) */}
            <Route element={<ProtectedRoute allowedRoles={['CITIZEN', 'AGENT', 'ADMIN']} />}>
              <Route path="/pickups/:id" element={<PickupDetails />} />
              <Route path="/parcels/:trackingId/qr" element={<QRCodeDisplay />} />
            </Route>

            {/* Fallback */}
            <Route path="*" element={<RootRedirect />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
