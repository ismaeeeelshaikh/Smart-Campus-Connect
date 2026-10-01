import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ArrowLeft, KeyRound, Lock, Mail } from 'lucide-react';
import { resetPassword } from '../../services/auth';
import { PASSWORD_REGEX, PASSWORD_RULE, apiErrorMessage } from '../../services/validation';
import AuthLayout from './AuthLayout';
import { ErrorAlert, PasswordField, Spinner, SuccessAlert, TextField } from './Fields';

export default function ResetPassword() {
  const location = useLocation();
  const [email, setEmail] = useState(location.state?.email || '');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!PASSWORD_REGEX.test(newPassword)) {
      setError(PASSWORD_RULE);
      return;
    }
    setLoading(true);
    try {
      await resetPassword(email.trim().toLowerCase(), otp.trim(), newPassword);
      setDone(true);
    } catch (err) {
      setError(apiErrorMessage(err, 'Invalid code or the password could not be reset.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      eyebrow="Password help"
      title="Set a new password"
      subtitle={location.state?.email
        ? 'If an account exists for this email, we sent it a 6-digit code (valid for 15 minutes).'
        : 'Enter your email, the code we emailed you, and a new password.'}
      footer={
        <Link to="/login" className="inline-flex items-center gap-1.5 text-sm font-semibold text-teal-700 hover:underline">
          <ArrowLeft className="h-4 w-4" /> Back to sign in
        </Link>
      }
    >
      {done ? (
        <div className="space-y-5">
          <SuccessAlert>Password updated. Other devices have been signed out.</SuccessAlert>
          <Link to="/login" className="btn-primary w-full py-3">Sign in with your new password</Link>
        </div>
      ) : (
        <form className="space-y-5" onSubmit={handleSubmit}>
          <ErrorAlert>{error}</ErrorAlert>
          <TextField
            id="email" type="email" required autoComplete="email" icon={Mail}
            label="Email" placeholder="yourid@apsit.edu.in"
            value={email} onChange={(e) => setEmail(e.target.value)} disabled={loading}
          />
          <TextField
            id="otp" inputMode="numeric" required autoComplete="one-time-code" maxLength={6} icon={KeyRound}
            label="Code from email" placeholder="6-digit code"
            value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))} disabled={loading}
          />
          <PasswordField
            id="newPassword" required autoComplete="new-password" icon={Lock}
            label="New password" placeholder="Min. 8 characters"
            hint="Use an uppercase letter, a lowercase letter and a number."
            value={newPassword} onChange={(e) => setNewPassword(e.target.value)} disabled={loading}
          />
          <button type="submit" disabled={loading} className="btn-primary w-full py-3">
            {loading ? <><Spinner /> Updating…</> : 'Update password'}
          </button>
        </form>
      )}
    </AuthLayout>
  );
}
