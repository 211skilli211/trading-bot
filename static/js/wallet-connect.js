/**
 * WalletConnect Integration for Trading Bot
 * Supports: Phantom (Solana), Trust Wallet, MetaMask (EVM chains)
 */

class WalletConnectManager {
    constructor() {
        this.connected = false;
        this.address = null;
        this.chain = null;
        this.provider = null;
        this.balance = 0;
        
        this.init();
    }
    
    async init() {
        // Check for existing session
        await this.checkExistingSession();
        
        // Setup event listeners
        this.setupEventListeners();
    }
    
    // =========================================================================
    // Solana (Phantom) Integration
    // =========================================================================
    
    async connectPhantom() {
        try {
            // Check if Phantom is installed
            if (!('solana' in window)) {
                this.showNotification('Phantom wallet not found. Redirecting to install...', 'warning');
                setTimeout(() => {
                    window.open('https://phantom.app/', '_blank');
                }, 2000);
                return false;
            }
            
            const provider = window.solana;
            
            // Connect to wallet
            const response = await provider.connect();
            const publicKey = response.publicKey.toString();
            
            this.address = publicKey;
            this.chain = 'solana';
            this.provider = provider;
            this.connected = true;
            
            // Send to backend
            const result = await this.registerWithBackend({
                chain: 'solana',
                address: publicKey,
                provider: 'phantom'
            });
            
            if (result.success) {
                this.balance = result.balance || 0;
                this.updateUI();
                this.showNotification('Phantom wallet connected!', 'success');
                
                // Setup disconnect listener
                provider.on('disconnect', () => {
                    this.handleDisconnect();
                });
                
                return true;
            } else {
                throw new Error(result.error || 'Backend registration failed');
            }
            
        } catch (error) {
            console.error('Phantom connection error:', error);
            this.showNotification('Connection failed: ' + error.message, 'error');
            return false;
        }
    }
    
    // =========================================================================
    // EVM WalletConnect (Trust Wallet, MetaMask)
    // =========================================================================
    
    async connectWalletConnect() {
        try {
            // Load WalletConnect provider dynamically
            if (!window.WalletConnectProvider) {
                await this.loadScript('https://unpkg.com/@walletconnect/web3-provider@1.8.0/dist/umd/index.min.js');
            }
            
            const provider = new window.WalletConnectProvider({
                rpc: {
                    1: "https://eth-mainnet.g.alchemy.com/v2/demo",
                    56: "https://bsc-dataseed.binance.org",
                    137: "https://polygon-rpc.com"
                },
                bridge: 'https://bridge.walletconnect.org',
                qrcode: true
            });
            
            // Enable session
            await provider.enable();
            
            const accounts = provider.accounts;
            if (!accounts || accounts.length === 0) {
                throw new Error('No accounts found');
            }
            
            this.address = accounts[0];
            this.chain = 'ethereum'; // Could detect actual chain
            this.provider = provider;
            this.connected = true;
            
            // Register with backend
            const result = await this.registerWithBackend({
                chain: this.chain,
                address: this.address,
                provider: 'walletconnect'
            });
            
            if (result.success) {
                this.balance = result.balance || 0;
                this.updateUI();
                this.showNotification('Wallet connected!', 'success');
                
                // Listen for disconnect
                provider.on('disconnect', () => {
                    this.handleDisconnect();
                });
                
                return true;
            }
            
        } catch (error) {
            console.error('WalletConnect error:', error);
            this.showNotification('Connection failed: ' + error.message, 'error');
            return false;
        }
    }
    
    // =========================================================================
    // Backend Integration
    // =========================================================================
    
    async registerWithBackend(data) {
        try {
            const response = await fetch('/api/wallet/connect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            return await response.json();
        } catch (error) {
            console.error('Backend registration error:', error);
            return { success: false, error: error.message };
        }
    }
    
    async checkExistingSession() {
        try {
            const response = await fetch('/api/wallet/session');
            const data = await response.json();
            
            if (data.connected && data.address) {
                this.connected = true;
                this.address = data.address;
                this.chain = data.chain;
                this.balance = data.balance || 0;
                this.updateUI();
            }
        } catch (error) {
            console.log('No existing session');
        }
    }
    
    async disconnect() {
        try {
            // Disconnect from provider if possible
            if (this.provider) {
                if (this.chain === 'solana' && this.provider.disconnect) {
                    await this.provider.disconnect();
                } else if (this.provider.disconnect) {
                    await this.provider.disconnect();
                }
            }
            
            // Clear backend session
            await fetch('/api/wallet/disconnect', {
                method: 'POST'
            });
            
            this.handleDisconnect();
            this.showNotification('Wallet disconnected', 'info');
            
        } catch (error) {
            console.error('Disconnect error:', error);
        }
    }
    
    handleDisconnect() {
        this.connected = false;
        this.address = null;
        this.chain = null;
        this.provider = null;
        this.balance = 0;
        this.updateUI();
    }
    
    // =========================================================================
    // Transaction Signing
    // =========================================================================
    
    async signTransaction(transactionData) {
        if (!this.connected) {
            throw new Error('Wallet not connected');
        }
        
        if (this.chain === 'solana') {
            return await this.signSolanaTransaction(transactionData);
        } else {
            return await this.signEVMTransaction(transactionData);
        }
    }
    
    async signSolanaTransaction(transactionData) {
        try {
            // This would integrate with solana-web3.js
            // For now, show confirmation dialog
            const confirmed = confirm(
                `Sign transaction?\n\n` +
                `From: ${transactionData.from}\n` +
                `To: ${transactionData.to}\n` +
                `Amount: ${transactionData.amount} ${transactionData.token}`
            );
            
            if (!confirmed) {
                return { success: false, error: 'User rejected' };
            }
            
            // In real implementation:
            // const transaction = new solanaWeb3.Transaction();
            // ... add instructions ...
            // const signature = await this.provider.signAndSendTransaction(transaction);
            
            return { 
                success: true, 
                signature: 'simulated_signature_' + Date.now(),
                message: 'Transaction signed (simulated)'
            };
            
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    async signEVMTransaction(transactionData) {
        try {
            const tx = {
                from: this.address,
                to: transactionData.to,
                value: transactionData.value,
                data: transactionData.data
            };
            
            const result = await this.provider.request({
                method: 'eth_sendTransaction',
                params: [tx]
            });
            
            return { success: true, hash: result };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    // =========================================================================
    // UI Updates
    // =========================================================================
    
    updateUI() {
        const connectBtn = document.getElementById('connect-wallet-btn');
        const walletStatus = document.getElementById('wallet-status');
        const walletAddress = document.getElementById('wallet-address');
        const walletBalance = document.getElementById('wallet-balance');
        const fundingBanner = document.getElementById('funding-banner');
        
        if (this.connected && this.address) {
            // Hide connect button, show status
            if (connectBtn) connectBtn.style.display = 'none';
            if (walletStatus) walletStatus.style.display = 'flex';
            
            // Update address display
            if (walletAddress) {
                walletAddress.textContent = `${this.address.slice(0, 4)}...${this.address.slice(-4)}`;
                walletAddress.title = this.address;
            }
            
            // Update balance
            if (walletBalance) {
                const chainSymbol = this.chain === 'solana' ? 'SOL' : 'ETH';
                walletBalance.textContent = `${this.balance.toFixed(4)} ${chainSymbol}`;
            }
            
            // Update funding banner
            if (fundingBanner) {
                fundingBanner.className = 'funding-banner funded';
                fundingBanner.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <i class="bi bi-check-circle"></i> <strong>Wallet Connected</strong>
                            <small class="d-block">${this.address.slice(0, 8)}...${this.address.slice(-8)}</small>
                        </div>
                        <span class="badge bg-success">Connected</span>
                    </div>
                `;
            }
            
            // Enable trading features
            document.querySelectorAll('[data-requires-wallet]').forEach(el => {
                el.classList.remove('disabled', 'opacity-50');
                el.removeAttribute('disabled');
            });
            
        } else {
            // Show connect button, hide status
            if (connectBtn) connectBtn.style.display = 'inline-flex';
            if (walletStatus) walletStatus.style.display = 'none';
            
            // Reset funding banner
            if (fundingBanner) {
                fundingBanner.className = 'funding-banner unfunded';
                fundingBanner.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <i class="bi bi-info-circle"></i> <strong>Paper Mode Active</strong>
                            <small class="d-block">Connect wallet to enable live trading</small>
                        </div>
                        <button class="btn btn-warning btn-sm" onclick="walletManager.showConnectModal()">
                            <i class="bi bi-wallet2"></i> Connect
                        </button>
                    </div>
                `;
            }
            
            // Disable trading features
            document.querySelectorAll('[data-requires-wallet]').forEach(el => {
                el.classList.add('disabled', 'opacity-50');
                el.setAttribute('disabled', 'disabled');
            });
        }
    }
    
    showConnectModal() {
        const modal = document.getElementById('wallet-modal');
        if (modal) {
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
        }
    }
    
    setupEventListeners() {
        // Connect button
        const connectBtn = document.getElementById('connect-wallet-btn');
        if (connectBtn) {
            connectBtn.addEventListener('click', () => this.showConnectModal());
        }
        
        // Disconnect button
        const disconnectBtn = document.getElementById('disconnect-wallet-btn');
        if (disconnectBtn) {
            disconnectBtn.addEventListener('click', () => this.disconnect());
        }
        
        // Wallet option buttons
        const phantomBtn = document.getElementById('connect-phantom');
        if (phantomBtn) {
            phantomBtn.addEventListener('click', () => this.connectPhantom());
        }
        
        const wcBtn = document.getElementById('connect-walletconnect');
        if (wcBtn) {
            wcBtn.addEventListener('click', () => this.connectWalletConnect());
        }
    }
    
    // =========================================================================
    // Utilities
    // =========================================================================
    
    loadScript(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }
    
    showNotification(message, type = 'info') {
        // Use existing notification system or create toast
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 5000);
    }
    
    async refreshBalance() {
        if (!this.connected) return;
        
        try {
            const response = await fetch('/api/wallet/balance');
            const data = await response.json();
            
            if (data.balance !== undefined) {
                this.balance = data.balance;
                this.updateUI();
            }
        } catch (error) {
            console.error('Balance refresh error:', error);
        }
    }
}

// Initialize global wallet manager
const walletManager = new WalletConnectManager();

// Auto-refresh balance every 30 seconds
setInterval(() => {
    walletManager.refreshBalance();
}, 30000);
