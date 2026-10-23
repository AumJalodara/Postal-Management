import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';

export default function ProtectedRoute({ allowedRoles }) {
  const token = localStorage.getItem('token');
  const userJson = localStorage.getItem('user');
  const user = userJson ? JSON.parse(userJson) : null;

  if (!token || !user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    // Redirect unauthorized roles to their respective home dashboard
    if (user.role === 'ADMIN') {
      return <Navigate to="/admin/operations" replace />;
    }
    if (user.role === 'AGENT') {
      return <Navigate to="/agent/dashboard" replace />;
    }
    return <Navigate to="/dashboard" replace />;
  }


  return <Outlet />;
}
