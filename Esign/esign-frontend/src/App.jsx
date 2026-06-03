// src/App.jsx

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';

import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import PackageDetailPage from './pages/PackageDetailPage';
import UploadPage from './pages/UploadPage';
import CreatePackagePage from './pages/CreatePackagePage';
import SigningPage from './pages/SigningPage';
import AuditTrailPage from './pages/AuditTrailPage';
// Protected route — redirects to login if not authenticated
function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div>Loading...</div>;
  return isAuthenticated ? children : <Navigate to="/login" />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="/upload" element={<ProtectedRoute><UploadPage /></ProtectedRoute>} />
          <Route path="/packages/new" element={<ProtectedRoute><CreatePackagePage /></ProtectedRoute>} />
          <Route path="/packages/:id" element={<ProtectedRoute><PackageDetailPage /></ProtectedRoute>} />
          <Route path="/sign/:token" element={<SigningPage />} />
          <Route path="/packages/:id/audit"element={<ProtectedRoute><AuditTrailPage /></ProtectedRoute>} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}