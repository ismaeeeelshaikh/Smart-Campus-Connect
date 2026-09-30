import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { resetPassword } from "../../services/auth";

export default function ResetPassword() {
  const location = useLocation();
  const [email, setEmail] = useState(location.state?.email || "");
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage("");
    setError("");
    try {
      await resetPassword(email, otp, newPassword);
      setMessage("Password updated successfully. Please login.");
    } catch (err) {
      setError("Invalid OTP or error resetting password.");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background-dark">
      <div className="max-w-md w-full bg-background-card rounded-lg shadow-lg p-8 space-y-6">
        <div>
          <h2 className="text-center text-3xl font-extrabold text-accent">
            Reset Password
          </h2>
        </div>
        <form className="space-y-6" onSubmit={handleSubmit}>
          <div>
            <label htmlFor="email" className="block mb-1 text-gray-400 font-medium">
              Email address
            </label>
            <input
              id="email"
              type="email"
              required
              className="w-full px-3 py-2 rounded-md bg-background-dark border border-gray-700 placeholder-gray-400 text-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600 transition"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
            />
          </div>
          <div>
            <label htmlFor="otp" className="block mb-1 text-gray-400 font-medium">
              OTP
            </label>
            <input
              id="otp"
              type="text"
              required
              className="w-full px-3 py-2 rounded-md bg-background-dark border border-gray-700 placeholder-gray-400 text-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600 transition"
              placeholder="OTP"
              value={otp}
              onChange={(e) => setOtp(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="newPassword" className="block mb-1 text-gray-400 font-medium">
              New Password
            </label>
            <input
              id="newPassword"
              type="password"
              required
              minLength={8}
              className="w-full px-3 py-2 rounded-md bg-background-dark border border-gray-700 placeholder-gray-400 text-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600 transition"
              placeholder="New Password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
            />
          </div>
          {message && (
            <div className="text-green-500 bg-green-900 rounded-md p-2 text-center text-sm">{message}</div>
          )}
          {error && (
            <div className="text-red-600 bg-red-900 rounded-md p-2 text-center text-sm">{error}</div>
          )}
          <div>
            <button
              type="submit"
              className="w-full py-2 px-4 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-md focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-primary-500 disabled:opacity-50 disabled:pointer-events-none transition"
            >
              Reset Password
            </button>
          </div>
          <div className="text-center">
            <span
              className="text-primary-600 hover:text-primary-500 cursor-pointer font-medium underline"
              onClick={() => navigate("/login")}
            >
              Back to login
            </span>
          </div>
        </form>
      </div>
    </div>
  );
}
