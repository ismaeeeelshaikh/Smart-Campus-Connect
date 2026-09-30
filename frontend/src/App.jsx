import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import ChatSessionLayout from './components/Layout/ChatSessionLayout';  // Updated
import Login from './components/Auth/Login';
import Register from './components/Auth/Register';
import ForgotPassword from "./components/Auth/ForgotPassword";
import ResetPassword from "./components/Auth/ResetPassword";
import VerifySignupOtp from "./components/Auth/VerifySignupOtp";


const PrivateRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
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