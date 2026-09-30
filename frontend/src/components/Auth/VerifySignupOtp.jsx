import React, { useState } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';

const VerifySignupOtp = () => {
  const location = useLocation();
  const navigate = useNavigate();

  // Get user info passed from Register.jsx
  const { username, email, password } = location.state || {};

  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!username || !email || !password) {
    // If no user info, redirect back to register
    navigate('/register');
    return null;
  }

  const handleVerify = async () => {
    if (!otp) {
      setError('Please enter the OTP received in your email');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch('/apiauth/complete-signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password, otp }),
      });

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(errText || 'OTP verification failed');
      }

      // On success redirect to login page or dashboard
      navigate('/login');
    } catch (err) {
      setError(err.message || 'Failed to verify OTP. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background-dark px-4">
      <div className="max-w-md w-full bg-background-card p-8 rounded-lg shadow-lg">
        <h2 className="text-2xl font-bold text-center text-accent mb-6">
          Verify Signup OTP
        </h2>
        <p className="text-center mb-4 text-gray-400">
          Please enter the OTP sent to <strong className="text-white">{email}</strong>
        </p>
        <input
          type="text"
          name="otp"
          placeholder="Enter OTP"
          value={otp}
          onChange={(e) => setOtp(e.target.value)}
          disabled={loading}
          className="w-full px-4 py-2 rounded-md bg-background-dark border border-gray-700 placeholder-gray-500 text-gray-200 mb-4 focus:outline-none focus:ring-2 focus:ring-primary-600 transition"
        />
        {error && (
          <p className="text-red-600 text-sm mb-4 text-center bg-red-900 rounded-md p-2">{error}</p>
        )}
        <button
          onClick={handleVerify}
          disabled={loading}
          className="w-full py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-md disabled:opacity-50 transition"
        >
          {loading ? 'Verifying...' : 'Verify & Create Account'}
        </button>
        <p className="mt-4 text-center text-sm text-gray-500">
          Didn't receive OTP? Please check your spam or{' '}
          <Link to="/register" className="text-primary-600 hover:underline">
            go back and try again
          </Link>.
        </p>
      </div>
    </div>
  );
};

export default VerifySignupOtp;
