// src/components/PrivateRoute.jsx
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function PrivateRoute({ requiredRole, children }) {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) {
    // Not logged in → send to /login, but remember where they were
    return (
      <Navigate
        to="/login"
        state={{ from: location }}
        replace
      />
    );
  }

  if (requiredRole && user.role !== requiredRole) {
    // Wrong role → bounce home
    return <Navigate to="/" replace />;
  }

  return children;
}
