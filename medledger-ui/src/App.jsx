// src/App.jsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import LoginForm from './pages/LoginForm';
import PatientDashboard from './pages/PatientDashboard';
import DoctorDashboard  from './pages/DoctorDashboard';
import AdminDashboard   from './pages/AdminDashboard';
import PatientDetails from './pages/PatientDetails';
import AdminViewPatient from './pages/AdminViewPatient';

function PrivateRoute({ children, requiredRole }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== requiredRole) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
         <Route
           path="/dashboard/doctor"
           element={
             <PrivateRoute requiredRole="doctor">
               <DoctorDashboard />
             </PrivateRoute>
           }
         />
         <Route
           path="/dashboard/doctor/patient/:id"
           element={
             <PrivateRoute requiredRole="doctor">
               <PatientDetails />
             </PrivateRoute>
           }
         />

          <Route path="/" element={<LandingPage />} />

          {/* Role Selection */}
          <Route path="/login" element={<LoginPage />} />
          {/* Actual Login Form for each role */}
          <Route path="/login/:role" element={<LoginForm />} />

          {/* Protected Dashboards */}
          <Route
            path="/dashboard/patient"
            element={
              <PrivateRoute requiredRole="patient">
                <PatientDashboard />
              </PrivateRoute>
            }
          />
          <Route
            path="/dashboard/doctor"
            element={
              <PrivateRoute requiredRole="doctor">
                <DoctorDashboard />
              </PrivateRoute>
            }
          />
          <Route
            path="/dashboard/admin"
            element={
              <PrivateRoute requiredRole="admin">
                <AdminDashboard />
              </PrivateRoute>
            }
          />

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/" replace />} />
          <Route
            path="/dashboard/admin/patient/:id"
            element={
              <PrivateRoute requiredRole="admin">
                <AdminViewPatient />
              </PrivateRoute>
            }
          />
        </Routes>
      </Router>
    </AuthProvider>
  );
}
