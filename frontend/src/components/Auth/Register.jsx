import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { PASSWORD_REGEX, PASSWORD_RULE, USERNAME_REGEX, USERNAME_RULE } from '../../services/validation';

const Register = () => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    if (error) setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (loading || success) return;

    // Validate email presence and format
    if (!formData.email || !formData.email.trim()) {
      alert('Please enter a valid email address.');
      setError('Please enter a valid email address.');
      return;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email.trim())) {
      alert('Please enter a valid email address format.');
      setError('Invalid email address format.');
      return;
    }

    // Same rules as the backend (app/utils/security.py)
    if (!USERNAME_REGEX.test(formData.username.trim())) {
      alert(USERNAME_RULE);
      setError(USERNAME_RULE);
      return;
    }
    if (!PASSWORD_REGEX.test(formData.password)) {
      alert(PASSWORD_RULE);
      setError(PASSWORD_RULE);
      return;
    }

    // Confirm password match
    if (formData.password !== formData.confirmPassword) {
      alert('Passwords do not match.');
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/auth/request-signup-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: formData.email.trim().toLowerCase() }),
      });
      if (!res.ok) {
        // Show the backend's reason, e.g. "Please sign up with your college email (@apsit.edu.in)."
        const data = await res.json().catch(() => ({}));
        throw new Error(typeof data.detail === 'string' ? data.detail : '');
      }

      navigate('/verify-signup-otp', { state: {
        username: formData.username,
        email: formData.email.trim().toLowerCase(),
        password: formData.password
      }});
    } catch (err) {
      setError(err.message || 'Could not send OTP. Please try again or use another email.');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background-dark">
        <div className="max-w-md w-full text-center">
          <div className="bg-green-950 p-6 rounded-lg">
            <h2 className="text-2xl font-bold text-green-400 mb-2">Registration Successful!</h2>
            <p className="text-green-300">Redirecting to dashboard...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background-dark">
      <div className="max-w-md w-full bg-background-card rounded-lg shadow-lg p-8 space-y-6">
        <div>
          <h2 className="text-center text-3xl font-extrabold text-accent">
            Create your account
          </h2>
        </div>
        <form className="space-y-6" onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div>
              <label htmlFor="username" className="block mb-1 text-gray-400 font-medium">
                Username
              </label>
              <input
                id="username"
                name="username"
                type="text"
                required
                disabled={loading}
                className="w-full px-3 py-2 rounded-md bg-background-dark border border-gray-700 placeholder-gray-400 text-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600 transition disabled:bg-gray-800"
                placeholder="Username"
                value={formData.username}
                onChange={handleChange}
                minLength="3"
              />
            </div>
            <div>
              <label htmlFor="email" className="block mb-1 text-gray-400 font-medium">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                required
                disabled={loading}
                className="w-full px-3 py-2 rounded-md bg-background-dark border border-gray-700 placeholder-gray-400 text-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600 transition disabled:bg-gray-800"
                placeholder="yourid@apsit.edu.in"
                value={formData.email}
                onChange={handleChange}
              />
              <p className="mt-1 text-xs text-gray-500">
                Use your APSIT college email (@apsit.edu.in). No college email?{' '}
                <Link to="/guest" className="text-primary-500 hover:underline">Chat as guest</Link>
              </p>
            </div>
            <div>
              <label htmlFor="password" className="block mb-1 text-gray-400 font-medium">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                required
                disabled={loading}
                className="w-full px-3 py-2 rounded-md bg-background-dark border border-gray-700 placeholder-gray-400 text-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600 transition disabled:bg-gray-800"
                placeholder="Password (min 8 characters)"
                value={formData.password}
                onChange={handleChange}
                minLength="6"
              />
            </div>
            <div>
              <label htmlFor="confirmPassword" className="block mb-1 text-gray-400 font-medium">
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                required
                disabled={loading}
                className="w-full px-3 py-2 rounded-md bg-background-dark border border-gray-700 placeholder-gray-400 text-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600 transition disabled:bg-gray-800"
                placeholder="Confirm Password"
                value={formData.confirmPassword}
                onChange={handleChange}
                minLength="6"
              />
            </div>
          </div>

          {error && (
            <div className="bg-red-900 border border-red-700 text-red-400 px-4 py-3 rounded-md text-sm">
              {error}
            </div>
          )}

          <div>
            <button
              type="submit"
              disabled={loading || success}
              className="w-full py-2 px-4 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {loading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Sending OTP...
                </span>
              ) : (
                'Send OTP'
              )}
            </button>
          </div>

          <div className="text-center">
            <Link
              to="/login"
              className="text-primary-600 hover:text-primary-500 font-medium underline"
            >
              Already have an account? Sign in
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Register;
