import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import ChatSessionLayout from './components/Layout/ChatSessionLayout';  // Updated
import Login from './components/Auth/Login';
import Register from './components/Auth/Register';
import ForgotPassword from "./components/Auth/ForgotPassword";
import ResetPassword from "./components/Auth/ResetPassword";
import VerifySignupOtp from "./components/Auth/VerifySignupOtp";
import GuestChat from "./components/Guest/GuestChat";


const PrivateRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-paper">
        <div className="text-center">
          <img src="/logo.png" alt="" className="mx-auto h-14 w-14 animate-pulse object-contain" />
          <p className="mt-4 text-sm text-ink-400">Loading…</p>
        </div>
      </div>
    );
  }
  
  return isAuthenticated ? children : <Navigate to="/login" replace />;
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="App">
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
             <Route path="/forgot-password" element={<ForgotPassword />} />
             <Route path="/reset-password" element={<ResetPassword />} />
             <Route path="/verify-signup-otp" element={<VerifySignupOtp />} />
             {/* Public: for visitors without an APSIT email */}
             <Route path="/guest" element={<GuestChat />} />

            <Route
              path="/"
              element={
                <PrivateRoute>
                  <ChatSessionLayout />
                </PrivateRoute>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;