import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { WalletContextProvider } from './contexts/WalletContext';
import { CurrencyProvider } from './contexts/CurrencyContext';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <WalletContextProvider>
        <CurrencyProvider>
          <App />
        </CurrencyProvider>
      </WalletContextProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
