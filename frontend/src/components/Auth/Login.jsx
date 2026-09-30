import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';

const Login = () => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await login(formData);
      if (response.data.user) {
        const userInfo = {
          id: response.data.user.id,
          username: response.data.user.username,
          email: response.data.user.email
        };
        localStorage.setItem('user', JSON.stringify(userInfo));
      }
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background-dark">
      <div className="max-w-md w-full bg-background-card rounded-lg shadow-lg p-8 space-y-6">
        <div>
          <h2 className="text-center text-3xl font-extrabold text-accent">
            Sign in to your account
          </h2>
        </div>
        <form className="space-y-5" onSubmit={handleSubmit}>
          <div>
            <label htmlFor="email" className="block mb-1 text-gray-400 font-medium">
              Email address
            </label>
            <input
              id="email"
              name="email"
              type="email"
              required
              autoComplete="email"
              placeholder="Enter your email"
              value={formData.email}
              onChange={handleChange}
              className="w-full px-3 py-2 rounded-md bg-background-dark border border-gray-700 placeholder-gray-400 text-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600 transition"
            />
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
              autoComplete="current-password"
              placeholder="Enter your password"
              value={formData.password}
              onChange={handleChange}
              className="w-full px-3 py-2 rounded-md bg-background-dark border border-gray-700 placeholder-gray-400 text-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600 transition"
            />
          </div>
          {error && (
            <div className="text-red-600 bg-red-900 rounded-md p-2 text-center text-sm">{error}</div>
          )}
          <div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2 px-4 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-primary-500 disabled:opacity-50 disabled:pointer-events-none transition"
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </div>
          <div className="flex justify-between items-center text-sm text-gray-400">
            <Link to="/forgot-password" className="hover:text-primary-600 underline">
              Forgot password?
            </Link>
            <Link to="/register" className="hover:text-primary-600 underline font-medium">
              Don't have an account? Sign up
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Login;
