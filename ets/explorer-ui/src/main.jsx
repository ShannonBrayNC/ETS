import React from 'react'
import ReactDOM from 'react-dom/client'

import App from './App.jsx'
import EdgeApp from './EdgeApp.jsx'
import './style.css'

const edgeDarkProEnabled = import.meta.env.VITE_ETS_EDGE_DARK_PRO === 'true'
const RootApp = edgeDarkProEnabled ? EdgeApp : App

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <RootApp />
  </React.StrictMode>,
)
