import React from 'react'
import ReactDOM from 'react-dom/client'
// Fonts are bundled with the app (no Google Fonts request): Hanken Grotesk for text, Literata for headings
import '@fontsource-variable/hanken-grotesk'
import '@fontsource-variable/literata'
import '@fontsource-variable/literata/wght-italic.css'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
