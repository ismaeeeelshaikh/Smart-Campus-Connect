import React, { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuth = () => {
      const token = localStorage.getItem('token');
      const userData = localStorage.getItem('user');
      
      if (token && userData) {
        try {
          const parsedUser = JSON.parse(userData);
          setUser(parsedUser);
          setIsAuthenticated(true);
        } catch (error) {
          console.error('Error parsing user data:', error);
          // Clear corrupted data
          localStorage.removeItem('token');
          localStorage.removeItem('user');
        }
      }
      setLoading(false);
    };

    checkAuth();
  }, []);

  const login = async (userData) => {
    try {
      const response = await authAPI.login(userData);
      const { access_token, token_type } = response.data;
      
      // Store token
      localStorage.setItem('token', access_token);
      
      // Store user data - THIS IS THE KEY FIX
      const userInfo = {
        email: userData.email,
        username: userData.username || userData.email.split('@')[0] // Fallback to email username
      };
      localStorage.setItem('user', JSON.stringify(userInfo));
      
      setUser(userInfo);
      setIsAuthenticated(true);
      
      return response;
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const register = async (userData) => {
  try {
    console.log('AuthContext: Starting registration for', userData.email);
    const response = await authAPI.register(userData);
    console.log('AuthContext: Registration successful');
    
    // Don't automatically log in after registration
    // Let them manually log in to avoid conflicts
    return response;
  } catch (error) {
    console.error('AuthContext: Registration failed:', error);
    throw error;
  }
};


  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    setIsAuthenticated(false);
  };

  const value = {
    isAuthenticated,
    user,
    loading,
    login,
    register,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
