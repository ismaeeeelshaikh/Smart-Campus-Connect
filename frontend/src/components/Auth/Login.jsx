import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, Lock, Mail, MessagesSquare } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { apiErrorMessage } from '../../services/validation';
import AuthLayout from './AuthLayout';
import { ErrorAlert, PasswordField, Spinner, SuccessAlert, TextField } from './Fields';

const Login = () => {
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();
  // e.g. "Account created! Please sign in." after signup
  const successMessage = useLocation().state?.message;

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    if (error) setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await login(formData);
      navigate('/');
    } catch (err) {
      setError(apiErrorMessage(err, 'Sign in failed. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      eyebrow="Student sign in"
      title="Welcome back"
      subtitle="Sign in with your APSIT college email to continue your chats."
      footer={
        <div>
          <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-wider text-ink-300">
            <span className="h-px flex-1 bg-line" /> or <span className="h-px flex-1 bg-line" />
          </div>
          <Link to="/guest" className="btn-outline mt-5 w-full py-3">
            <MessagesSquare className="h-[18px] w-[18px]" />
            Chat as guest: no account needed
          </Link>
          <p className="mt-2 text-center text-xs text-ink-400">For future students and parents. Guest chats aren&apos;t saved.</p>
        </div>
      }
    >
      <form className="space-y-5" onSubmit={handleSubmit}>
        {!error && <SuccessAlert>{successMessage}</SuccessAlert>}
        <ErrorAlert>{error}</ErrorAlert>
        <TextField
          id="email" name="email" type="email" required autoComplete="email" icon={Mail}
          label="College email" placeholder="yourid@apsit.edu.in"
          value={formData.email} onChange={handleChange}
        />
        <div>
          <PasswordField
            id="password" name="password" required autoComplete="current-password" icon={Lock}
            label="Password" placeholder="Your password"
            value={formData.password} onChange={handleChange}
          />
          <div className="mt-2 text-right">
            <Link to="/forgot-password" className="text-sm font-medium text-teal-700 hover:text-teal-900 hover:underline">
              Forgot password?
            </Link>
          </div>
        </div>
        <button type="submit" disabled={loading} className="btn-primary w-full py-3">
          {loading ? <><Spinner /> Signing in…</> : <>Sign in <ArrowRight className="h-4 w-4" /></>}
        </button>
        <p className="text-center text-sm text-ink-500">
          New here?{' '}
          <Link to="/register" className="font-semibold text-teal-700 hover:text-teal-900 hover:underline">
            Create an account
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
};

export default Login;
