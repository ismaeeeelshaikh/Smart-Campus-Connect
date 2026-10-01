import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, AtSign, Lock, Mail } from 'lucide-react';
import { authAPI } from '../../services/api';
import { PASSWORD_REGEX, PASSWORD_RULE, USERNAME_REGEX, USERNAME_RULE, apiErrorMessage } from '../../services/validation';
import AuthLayout from './AuthLayout';
import { ErrorAlert, PasswordField, Spinner, TextField } from './Fields';

const Register = () => {
  const [formData, setFormData] = useState({ username: '', email: '', password: '', confirmPassword: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    if (error) setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;
    const email = formData.email.trim().toLowerCase();
    const username = formData.username.trim();

    // Same rules as the backend (app/utils/security.py)
    if (!USERNAME_REGEX.test(username)) return setError(USERNAME_RULE);
    if (!PASSWORD_REGEX.test(formData.password)) return setError(PASSWORD_RULE);
    if (formData.password !== formData.confirmPassword) return setError('Passwords do not match.');

    setLoading(true);
    setError('');
    try {
      await authAPI.requestSignupOtp(email);
      navigate('/verify-signup-otp', { state: { username, email, password: formData.password } });
    } catch (err) {
      // e.g. "Please sign up with your college email (@apsit.edu.in)."
      setError(apiErrorMessage(err, 'Could not send the OTP. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      eyebrow="New account"
      title="Create your account"
      subtitle="APSIT students sign up with their college email. We'll send a one-time code to verify it."
      footer={
        <p className="text-center text-sm text-ink-500">
          Already have an account?{' '}
          <Link to="/login" className="font-semibold text-teal-700 hover:text-teal-900 hover:underline">Sign in</Link>
          <span className="mx-2 text-ink-300">·</span>
          No college email?{' '}
          <Link to="/guest" className="font-semibold text-teal-700 hover:text-teal-900 hover:underline">Chat as guest</Link>
        </p>
      }
    >
      <form className="space-y-5" onSubmit={handleSubmit} noValidate>
        <ErrorAlert>{error}</ErrorAlert>
        <TextField
          id="username" name="username" required autoComplete="username" icon={AtSign}
          label="Username" placeholder="e.g. rohan_s" hint="3-30 characters: letters, numbers, . _ -"
          value={formData.username} onChange={handleChange} disabled={loading}
        />
        <TextField
          id="email" name="email" type="email" required autoComplete="email" icon={Mail}
          label="College email" placeholder="yourid@apsit.edu.in" hint="Use your @apsit.edu.in address"
          value={formData.email} onChange={handleChange} disabled={loading}
        />
        <div className="grid gap-5 sm:grid-cols-2">
          <PasswordField
            id="password" name="password" required autoComplete="new-password" icon={Lock}
            label="Password" placeholder="Min. 8 characters"
            value={formData.password} onChange={handleChange} disabled={loading}
          />
          <PasswordField
            id="confirmPassword" name="confirmPassword" required autoComplete="new-password" icon={Lock}
            label="Confirm" placeholder="Repeat password"
            value={formData.confirmPassword} onChange={handleChange} disabled={loading}
          />
        </div>
        <p className="-mt-2 text-xs text-ink-400">Use an uppercase letter, a lowercase letter and a number.</p>
        <button type="submit" disabled={loading} className="btn-primary w-full py-3">
          {loading ? <><Spinner /> Sending code…</> : <>Send verification code <ArrowRight className="h-4 w-4" /></>}
        </button>
      </form>
    </AuthLayout>
  );
};

export default Register;
