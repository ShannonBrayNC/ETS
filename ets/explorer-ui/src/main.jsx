import React from 'react'
import ReactDOM from 'react-dom/client'

import App from './App.jsx'
import EdgeDarkApp from './EdgeDarkApp.jsx'
import './style.css'
import './edge-dark.css'

const Surface = import.meta.env.VITE_ETS_SURFACE_PROFILE === 'edge' ? EdgeDarkApp : App

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Surface />
  </React.StrictMode>,
)
