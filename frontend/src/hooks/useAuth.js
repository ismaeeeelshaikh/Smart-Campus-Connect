import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { authAPI } from '../services/api';

export const useAuthActions = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { login } = useAuth();

  const register = async (userData) => {
    setLoading(true);
    setError(null);
    try {
      const response = await authAPI.register(userData);
      
      // Auto-login after registration
      const loginResponse = await authAPI.login({
        email: userData.email,
        password: userData.password,
      });
      
      login(loginResponse.data.access_token, response.data);
      return response.data;
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'Registration failed';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const loginUser = async (userData) => {
    setLoading(true);
    setError(null);
    try {
      const response = await authAPI.login(userData);
      login(response.data.access_token, userData);
      return response.data;
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'Login failed';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return { register, loginUser, loading, error };
};
