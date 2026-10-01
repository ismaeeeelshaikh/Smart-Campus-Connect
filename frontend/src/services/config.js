// Where the backend lives. In development the Vite dev server forwards /api to the backend
// (see vite.config.js). For a production build set VITE_API_URL, e.g.
//   VITE_API_URL=https://api.example.com npm run build
export const API_BASE = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '');
