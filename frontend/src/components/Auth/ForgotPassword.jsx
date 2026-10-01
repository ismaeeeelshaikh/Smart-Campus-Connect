import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Mail, Send } from 'lucide-react';
import { requestPasswordReset } from '../../services/auth';
import { apiErrorMessage } from '../../services/validation';
import AuthLayout from './AuthLayout';
import { ErrorAlert, Spinner, TextField } from './Fields';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await requestPasswordReset(email.trim().toLowerCase());
      navigate('/reset-password', { state: { email: email.trim().toLowerCase() } });
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not send the code. Please try again later.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      eyebrow="Password help"
      title="Forgot your password?"
      subtitle="Enter your account email and we'll send you a code to set a new password."
      footer={
        <Link to="/login" className="inline-flex items-center gap-1.5 text-sm font-semibold text-teal-700 hover:underline">
          <ArrowLeft className="h-4 w-4" /> Back to sign in
        </Link>
      }
    >
      <form className="space-y-5" onSubmit={handleSubmit}>
        <ErrorAlert>{error}</ErrorAlert>
        <TextField
          id="email" type="email" required autoComplete="email" icon={Mail}
          label="Email" placeholder="yourid@apsit.edu.in"
          value={email} onChange={(e) => setEmail(e.target.value)} disabled={loading}
        />
        <button type="submit" disabled={loading} className="btn-primary w-full py-3">
          {loading ? <><Spinner /> Sending…</> : <><Send className="h-4 w-4" /> Send reset code</>}
        </button>
      </form>
    </AuthLayout>
  );
}
