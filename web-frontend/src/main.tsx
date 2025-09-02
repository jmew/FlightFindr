import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import 'bootstrap/dist/css/bootstrap.min.css';
import './index.css'
import App from './App.tsx'
import favicon from './assets/plane-icon.svg'

const faviconLink = document.createElement('link');
faviconLink.rel = 'icon';
faviconLink.href = favicon;
document.head.appendChild(faviconLink);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)