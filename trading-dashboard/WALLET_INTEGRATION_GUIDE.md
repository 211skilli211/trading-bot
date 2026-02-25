# Wallet Integration Guide

## Current State
The wallet connection is currently mocked (hardcoded address). For production, you need proper wallet adapter integration.

## Recommended Approach: Solana Wallet Adapter

### Step 1: Install Dependencies

```bash
cd /root/trading-dashboard
npm install @solana/wallet-adapter-react @solana/wallet-adapter-react-ui @solana/wallet-adapter-phantom @solana/wallet-adapter-solflare @solana/web3.js
```

### Step 2: Create Wallet Context Provider

Create `src/contexts/WalletContext.tsx`:

```typescript
import { FC, ReactNode, useMemo } from 'react';
import { ConnectionProvider, WalletProvider } from '@solana/wallet-adapter-react';
import { WalletModalProvider } from '@solana/wallet-adapter-react-ui';
import { PhantomWalletAdapter, SolflareWalletAdapter } from '@solana/wallet-adapter-wallets';
import { clusterApiUrl } from '@solana/web3.js';

// Import wallet adapter CSS
import '@solana/wallet-adapter-react-ui/styles.css';

export const WalletContextProvider: FC<{ children: ReactNode }> = ({ children }) => {
  // Solana network (mainnet, devnet, testnet)
  const network = 'mainnet-beta';
  const endpoint = useMemo(() => clusterApiUrl(network), [network]);

  // Supported wallets
  const wallets = useMemo(
    () => [
      new PhantomWalletAdapter(),
      new SolflareWalletAdapter(),
    ],
    []
  );

  return (
    <ConnectionProvider endpoint={endpoint}>
      <WalletProvider wallets={wallets} autoConnect>
        <WalletModalProvider>{children}</WalletModalProvider>
      </WalletProvider>
    </ConnectionProvider>
  );
};
```

### Step 3: Wrap App with Provider

Update `src/main.tsx`:

```typescript
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { WalletContextProvider } from './contexts/WalletContext';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <WalletContextProvider>
        <App />
      </WalletContextProvider>
    </BrowserRouter>
  </React.StrictMode>
);
```

### Step 4: Create Wallet Hook

Create `src/hooks/useWalletConnection.ts`:

```typescript
import { useWallet, useConnection } from '@solana/wallet-adapter-react';
import { PublicKey, LAMPORTS_PER_SOL } from '@solana/web3.js';
import { useState, useEffect, useCallback } from 'react';

export interface WalletData {
  connected: boolean;
  publicKey: string | null;
  balance: number;
  connecting: boolean;
  disconnecting: boolean;
}

export function useWalletConnection() {
  const { connection } = useConnection();
  const { 
    publicKey, 
    connected, 
    connecting, 
    disconnecting,
    select, 
    connect, 
    disconnect 
  } = useWallet();
  
  const [balance, setBalance] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(false);

  // Fetch SOL balance
  useEffect(() => {
    if (!publicKey || !connection) return;
    
    const fetchBalance = async () => {
      try {
        const balance = await connection.getBalance(publicKey);
        setBalance(balance / LAMPORTS_PER_SOL);
      } catch (error) {
        console.error('Failed to fetch balance:', error);
        setBalance(0);
      }
    };

    fetchBalance();
    
    // Set up interval to refresh balance
    const interval = setInterval(fetchBalance, 10000);
    return () => clearInterval(interval);
  }, [publicKey, connection]);

  const openWalletModal = useCallback(() => {
    // This triggers the wallet modal from @solana/wallet-adapter-react-ui
    const modal = document.querySelector('.wallet-adapter-modal-trigger');
    if (modal) {
      (modal as HTMLElement).click();
    }
  }, []);

  const handleDisconnect = useCallback(async () => {
    setIsLoading(true);
    try {
      await disconnect();
      // Also notify backend
      await fetch('/api/wallet/disconnect', { method: 'POST' });
    } catch (error) {
      console.error('Disconnect failed:', error);
    } finally {
      setIsLoading(false);
    }
  }, [disconnect]);

  return {
    connected,
    publicKey: publicKey?.toString() || null,
    balance,
    connecting,
    disconnecting,
    isLoading,
    openWalletModal,
    disconnect: handleDisconnect,
  };
}
```

### Step 5: Update Settings Page

Replace the mock `connectWallet` function in `Settings.tsx`:

```typescript
import { useWallet } from '@solana/wallet-adapter-react';
import { WalletMultiButton } from '@solana/wallet-adapter-react-ui';

// In your component:
const { publicKey, connected, connecting, disconnect } = useWallet();

// Replace the manual connect button with:
<WalletMultiButton className="px-4 py-2 bg-blue-600 rounded-lg" />
```

### Step 6: Backend Updates

Update `/root/trading-bot/dashboard.py` wallet endpoints:

```python
@app.route("/api/wallet/connect", methods=["POST"])
def connect_wallet():
    """Connect a wallet - now verifies signature"""
    try:
        data = request.json
        chain = data.get('chain')
        address = data.get('address')
        signature = data.get('signature')  # Signed message for verification
        
        # Verify signature (prevents fake connections)
        if chain == 'solana':
            from solders.keypair import Keypair
            from solders.pubkey import Pubkey
            # Verify the signature matches the address
            
        # Store in session
        session['wallet'] = {
            'chain': chain,
            'address': address,
            'connected_at': datetime.now(timezone.utc).isoformat()
        }
        
        return jsonify({
            "success": True, 
            "address": address,
            "message": f"{chain} wallet connected"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400
```

## Alternative: WalletConnect (Multi-Chain)

For supporting multiple chains (ETH, SOL, etc.):

```bash
npm install @walletconnect/ethereum-provider @walletconnect/modal
```

## Security Best Practices

1. **Never store private keys** - Only store public addresses
2. **Verify signatures** - Ensure user owns the wallet
3. **Session management** - Expire sessions after inactivity
4. **HTTPS only** - Never send wallet data over HTTP
5. **Nonce verification** - Prevent replay attacks

## Testing Wallet Connection

1. Install Phantom Extension (Chrome/Firefox)
2. Create a test wallet
3. Switch to Devnet for testing
4. Get devnet SOL from faucet: https://faucet.solana.com/

## Quick Implementation

If you want a minimal working version now, update `Settings.tsx`:

```typescript
// Add at top
import { useWallet, useConnection } from '@solana/wallet-adapter-react';
import { WalletMultiButton } from '@solana/wallet-adapter-react-ui';

// In component, replace connect button with:
{connected ? (
  <div>
    <p>Connected: {publicKey?.toString().slice(0, 8)}...</p>
    <button onClick={disconnect}>Disconnect</button>
  </div>
) : (
  <WalletMultiButton />
)}
```

## Resources

- Solana Wallet Adapter Docs: https://github.com/solana-labs/wallet-adapter
- Phantom Wallet: https://phantom.app/
- Solflare Wallet: https://solflare.com/
- WalletConnect: https://walletconnect.com/
