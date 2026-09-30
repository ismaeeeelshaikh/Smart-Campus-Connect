import api from "./api";

export const getToken = () => localStorage.getItem('token');
export const setToken = (token) => localStorage.setItem('token', token);
export const removeToken = () => localStorage.removeItem('token');

export const getUser = () => {
  const user = localStorage.getItem('user');
  return user ? JSON.parse(user) : null;
};

export const setUser = (user) => localStorage.setItem('user', JSON.stringify(user));
export const removeUser = () => localStorage.removeItem('user');

export const isAuthenticated = () => {
  return !!getToken();
};

export const requestPasswordReset = async (email) => {
  const response = await api.post("/password-reset/request-reset", { email });
  return response.data;
};

export const resetPassword = async (email, otp, newPassword) => {
  const response = await api.post("/password-reset/reset-password", {
    email,
    otp,
    new_password: newPassword,
  });
  return response.data;
};

