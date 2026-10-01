// Same rules as the backend (backend/app/utils/security.py), so users see problems before submitting
export const PASSWORD_REGEX = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,128}$/;
export const PASSWORD_RULE =
  'Password must be 8-128 characters and include an uppercase letter, a lowercase letter and a number.';

export const USERNAME_REGEX = /^[A-Za-z0-9._-]{3,30}$/;
export const USERNAME_RULE = 'Username must be 3-30 characters: letters, numbers, dot, underscore or hyphen.';

// FastAPI validation errors (422) arrive as a list; show the first message without pydantic's prefix
export const apiErrorMessage = (err, fallback) => {
  if (err.request && !err.response) {
    return "Can't reach the server. Please check your connection and try again.";
  }
  const detail = err.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg.replace(/^Value error, /, '');
  return fallback;
};
