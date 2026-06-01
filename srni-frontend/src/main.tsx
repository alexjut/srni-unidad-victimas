import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { Toaster } from 'sonner';
import ErrorBoundary from '@/components/ErrorBoundary';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <App />
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              fontFamily: 'Work Sans, system-ui, sans-serif',
              fontSize: '0.875rem',
            },
          }}
          richColors
          closeButton
        />
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>,
);
