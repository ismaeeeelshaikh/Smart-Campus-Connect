import React, { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { KeyRound, ShieldCheck } from 'lucide-react';
import { authAPI } from '../../services/api';
import { apiErrorMessage } from '../../services/validation';
import AuthLayout from './AuthLayout';
import { ErrorAlert, Spinner, TextField } from './Fields';

const VerifySignupOtp = () => {
  const location = useLocation();
  const navigate = useNavigate();
  // Details passed from Register.jsx
  const { username, email, password } = location.state || {};
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!username || !email || !password) {
    return <Navigate to="/register" replace />;
  }

  const handleVerify = async (e) => {
    e.preventDefault();
    if (!/^\d{6}$/.test(otp.trim())) {
      setError('Please enter the 6-digit code from your email.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await authAPI.completeSignup({ username, email, password, otp: otp.trim() });
      navigate('/login', { state: { message: 'Account created! Please sign in.' } });
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not verify the code. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      eyebrow="Verify email"
      title="Check your inbox"
      subtitle={<>We sent a 6-digit code to <strong className="font-semibold text-ink">{email}</strong>. It expires in 10 minutes.</>}
      footer={
        <p className="text-center text-sm text-ink-500">
          Didn&apos;t get it? Check spam, or{' '}
          <Link to="/register" className="font-semibold text-teal-700 hover:underline">go back and request a new code</Link>.
        </p>
      }
    >
      <form className="space-y-5" onSubmit={handleVerify}>
        <ErrorAlert>{error}</ErrorAlert>
        <TextField
          id="otp" name="otp" inputMode="numeric" autoComplete="one-time-code" maxLength={6} icon={KeyRound}
          label="Verification code" placeholder="••••••"
          className="field-input pl-11 text-center font-mono text-xl tracking-[0.5em]"
          value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))} disabled={loading} autoFocus
        />
        <button type="submit" disabled={loading} className="btn-primary w-full py-3">
          {loading ? <><Spinner /> Verifying…</> : <><ShieldCheck className="h-[18px] w-[18px]" /> Verify &amp; create account</>}
        </button>
      </form>
    </AuthLayout>
  );
};

export default VerifySignupOtp;
