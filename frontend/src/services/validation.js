// Same rules as the backend (backend/app/utils/security.py), so users see problems before submitting
export const PASSWORD_REGEX = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,128}$/;
export const PASSWORD_RULE =
  'Password must be 8-128 characters and include an uppercase letter, a lowercase letter and a number.';

// Any script (e.g. Hindi/Marathi names too): letters, spaces, . ' -  (2-60 characters)
export const normalizeName = (name) => name.trim().replace(/\s+/g, ' ');
export const isValidFullName = (name) => {
  const n = normalizeName(name);
  return n.length >= 2 && n.length <= 60 && /^[\p{L}\p{M} .'-]+$/u.test(n) && (n.match(/[\p{L}\p{M}]/gu) || []).length >= 2;
};
export const FULL_NAME_RULE = "Please enter your full name (2-60 characters: letters, spaces, . ' -).";

// What to show for a user (accounts from before full names used "username")
export const displayName = (user) => user?.full_name || user?.username || user?.email?.split('@')[0] || '';

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
