/**
 * Real-Time Dashboard Module
 * Handles WebSocket connections, live updates, and animations
 */

class RealtimeDashboard {
    constructor() {
        this.socket = null;
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.subscriptions = new Set();
        this.animationQueue = [];
        this.lastPrices = {};
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.currentSwipe = null;
        
        this.init();
    }
    
    init() {
        this.connectWebSocket();
        this.setupTouchGestures();
        this.setupAnimations();
        this.startHeartbeat();
    }
    
    // WebSocket Connection
    connectWebSocket() {
        if (typeof io === 'undefined') {
            console.log('[Realtime] Socket.IO not available, using polling fallback');
            this.startPolling();
            return;
        }
        
        try {
            this.socket = io({
                transports: ['websocket', 'polling'],
                reconnection: true,
                reconnectionDelay: 1000,
                reconnectionAttempts: this.maxReconnectAttempts
            });
            
            this.socket.on('connect', () => {
                this.connected = true;
                this.reconnectAttempts = 0;
                this.updateConnectionStatus(true);
                console.log('[Realtime] Connected via WebSocket');
                
                this.socket.emit('subscribe', { 
                    channels: ['prices', 'trades', 'positions', 'alerts'] 
                });
            });
            
            this.socket.on('disconnect', () => {
                this.connected = false;
                this.updateConnectionStatus(false);
                console.log('[Realtime] Disconnected');
            });
            
            this.socket.on('price_update', (data) => this.handlePriceUpdate(data));
            this.socket.on('trade_update', (data) => this.handleTradeUpdate(data));
            this.socket.on('position_update', (data) => this.handlePositionUpdate(data));
            this.socket.on('alert', (data) => this.handleAlert(data));
            this.socket.on('data_update', (data) => this.handleFullUpdate(data));
            
        } catch (e) {
            console.error('[Realtime] WebSocket error:', e);
            this.startPolling();
        }
    }
    
    startPolling() {
        setInterval(() => {
            if (!document.hidden) {
                this.fetchUpdate();
            }
        }, 5000);
    }
    
    async fetchUpdate() {
        try {
            const response = await fetch('/api/data');
            const data = await response.json();
            this.handleFullUpdate(data);
        } catch (e) {
            console.error('[Realtime] Polling error:', e);
        }
    }
    
    updateConnectionStatus(connected) {
        const statusEl = document.getElementById('connection-status');
        const liveIndicator = document.querySelector('.live-indicator');
        
        if (statusEl) {
            statusEl.className = `badge ${connected ? 'bg-success' : 'bg-danger'}`;
            statusEl.innerHTML = `<i class="bi bi-wifi"></i> ${connected ? 'Online' : 'Offline'}`;
        }
        
        if (liveIndicator) {
            liveIndicator.classList.toggle('offline', !connected);
        }
        
        // Connection status bar
        const statusBar = document.querySelector('.connection-status');
        if (statusBar) {
            statusBar.classList.toggle('disconnected', !connected);
        }
    }
    
    // Price Updates with Animation
    handlePriceUpdate(data) {
        if (!data.prices) return;
        
        data.prices.forEach(price => {
            const symbol = price.symbol || 'BTC/USDT';
            const newPrice = price.price;
            const oldPrice = this.lastPrices[symbol];
            
            // Update price display
            const priceEl = document.querySelector(`[data-price="${symbol}"]`);
            if (priceEl) {
                priceEl.textContent = this.formatPrice(newPrice);
                
                // Animate price change
                if (oldPrice && oldPrice !== newPrice) {
                    priceEl.classList.remove('price-up', 'price-down');
                    void priceEl.offsetWidth; // Trigger reflow
                    priceEl.classList.add(newPrice > oldPrice ? 'price-up' : 'price-down');
                }
            }
            
            this.lastPrices[symbol] = newPrice;
        });
    }
    
    handleTradeUpdate(trade) {
        // Add new trade row with animation
        const tradesTable = document.querySelector('#trades-table tbody');
        if (tradesTable) {
            const row = this.createTradeRow(trade);
            row.classList.add('trade-row-new');
            tradesTable.insertBefore(row, tradesTable.firstChild);
            
            // Remove old rows if too many
            while (tradesTable.children.length > 20) {
                tradesTable.removeChild(tradesTable.lastChild);
            }
        }
        
        // Show notification
        this.showToast(`New ${trade.side} trade: ${trade.symbol}`, trade.net_pnl >= 0 ? 'success' : 'danger');
    }
    
    handlePositionUpdate(position) {
        const positionsContainer = document.querySelector('#positions-container');
        if (positionsContainer) {
            this.refreshPositions();
        }
    }
    
    handleAlert(alert) {
        this.showToast(alert.message, alert.type || 'info');
        
        // Update alert count
        const alertCount = document.getElementById('alert-count');
        if (alertCount) {
            const count = parseInt(alertCount.textContent) + 1;
            alertCount.textContent = count;
            alertCount.classList.add('animate-bounce-in');
        }
    }
    
    handleFullUpdate(data) {
        // Update KPIs
        this.updateKPIs(data);
        
        // Update prices
        if (data.prices_list) {
            this.handlePriceUpdate({ prices: data.prices_list });
        }
        
        // Update balance
        const balanceEl = document.querySelector('[data-kpi="balance"]');
        if (balanceEl && data.balance) {
            this.animateValue(balanceEl, parseFloat(balanceEl.dataset.value || 0), data.balance, 'currency');
            balanceEl.dataset.value = data.balance;
        }
    }
    
    updateKPIs(data) {
        const kpis = {
            'mode': data.mode,
            'trades': data.trades?.length || 0,
            'positions': data.positions?.length || 0
        };
        
        Object.entries(kpis).forEach(([key, value]) => {
            const el = document.querySelector(`[data-kpi="${key}"]`);
            if (el) {
                if (key === 'mode') {
                    el.textContent = value;
                    el.className = `h4 mb-0 ${value === 'LIVE' ? 'text-danger' : 'text-success'}`;
                } else {
                    this.animateValue(el, parseInt(el.textContent) || 0, value, 'number');
                }
            }
        });
    }
    
    // Animation Helpers
    animateValue(element, start, end, format = 'number') {
        const duration = 500;
        const startTime = performance.now();
        
        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            const easeOutQuad = progress * (2 - progress);
            const current = start + (end - start) * easeOutQuad;
            
            if (format === 'currency') {
                element.textContent = '$' + current.toFixed(2);
            } else if (format === 'percent') {
                element.textContent = current.toFixed(1) + '%';
            } else {
                element.textContent = Math.round(current);
            }
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        
        requestAnimationFrame(animate);
    }
    
    createTradeRow(trade) {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="small">${trade.timestamp?.substring(0, 16) || 'N/A'}</td>
            <td><span class="badge ${trade.side === 'SELL' ? 'bg-danger' : 'bg-success'}">${trade.side}</span></td>
            <td>${trade.symbol}</td>
            <td class="text-end">${trade.amount}</td>
            <td class="text-end">$${this.formatPrice(trade.price)}</td>
            <td class="text-end ${trade.net_pnl >= 0 ? 'text-success' : 'text-danger'}">
                $${trade.net_pnl?.toFixed(2) || '0.00'}
            </td>
        `;
        return row;
    }
    
    // Touch Gestures
    setupTouchGestures() {
        const container = document.querySelector('main');
        if (!container) return;
        
        // Swipe navigation
        container.addEventListener('touchstart', (e) => {
            this.touchStartX = e.touches[0].clientX;
            this.touchStartY = e.touches[0].clientY;
        }, { passive: true });
        
        container.addEventListener('touchend', (e) => {
            const touchEndX = e.changedTouches[0].clientX;
            const touchEndY = e.changedTouches[0].clientY;
            
            const deltaX = touchEndX - this.touchStartX;
            const deltaY = touchEndY - this.touchStartY;
            
            // Horizontal swipe (more horizontal than vertical)
            if (Math.abs(deltaX) > 50 && Math.abs(deltaX) > Math.abs(deltaY)) {
                if (deltaX > 0) {
                    this.handleSwipeRight();
                } else {
                    this.handleSwipeLeft();
                }
            }
            
            // Pull to refresh
            if (deltaY > 100 && window.scrollY === 0) {
                this.handlePullToRefresh();
            }
        }, { passive: true });
        
        // Long press
        let longPressTimer;
        container.addEventListener('touchstart', (e) => {
            longPressTimer = setTimeout(() => {
                this.handleLongPress(e.target);
            }, 500);
        }, { passive: true });
        
        container.addEventListener('touchend', () => {
            clearTimeout(longPressTimer);
        }, { passive: true });
        
        // Edge swipe for menu
        document.addEventListener('touchstart', (e) => {
            if (e.touches[0].clientX < 20) {
                this.openSidebar();
            }
        }, { passive: true });
    }
    
    handleSwipeRight() {
        // Open sidebar or go back
        this.openSidebar();
    }
    
    handleSwipeLeft() {
        // Close sidebar or go forward
        this.closeSidebar();
    }
    
    handlePullToRefresh() {
        const indicator = document.querySelector('.pull-refresh-indicator');
        if (indicator) {
            indicator.classList.add('pulling');
        }
        
        this.fetchUpdate().finally(() => {
            setTimeout(() => {
                indicator?.classList.remove('pulling');
            }, 500);
        });
    }
    
    handleLongPress(target) {
        target.classList.add('long-press-active');
        setTimeout(() => target.classList.remove('long-press-active'), 600);
        
        // Show context menu if applicable
        const contextMenu = target.querySelector('.context-menu');
        if (contextMenu) {
            contextMenu.classList.add('show');
        }
    }
    
    openSidebar() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            const bsOffcanvas = new bootstrap.Offcanvas(sidebar);
            bsOffcanvas.show();
        }
    }
    
    closeSidebar() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar && sidebar.classList.contains('show')) {
            bootstrap.Offcanvas.getInstance(sidebar)?.hide();
        }
    }
    
    handlePullToRefresh() {
        this.showToast('Refreshing data...', 'info');
        this.fetchUpdate();
    }
    
    // Animations Setup
    setupAnimations() {
        // Intersection Observer for scroll animations
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-fade-in-up');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });
        
        document.querySelectorAll('.animate-on-scroll').forEach(el => {
            observer.observe(el);
        });
        
        // Stagger animations for lists
        document.querySelectorAll('.stagger-children').forEach(container => {
            Array.from(container.children).forEach((child, i) => {
                child.style.animationDelay = `${i * 0.1}s`;
                child.classList.add('animate-fade-in-up');
            });
        });
    }
    
    // Heartbeat
    startHeartbeat() {
        setInterval(() => {
            if (this.connected && this.socket) {
                this.socket.emit('request_update');
            }
        }, 10000);
    }
    
    // Toast Notifications
    showToast(message, type = 'info') {
        const container = document.querySelector('.toast-container');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = `toast-enhanced toast-${type}`;
        toast.innerHTML = `
            <div class="d-flex align-items-center p-3">
                <i class="bi bi-${this.getToastIcon(type)} me-2"></i>
                <div class="toast-body">${message}</div>
                <button class="btn-close btn-close-white ms-auto" onclick="this.parentElement.parentElement.remove()"></button>
            </div>
        `;
        
        container.appendChild(toast);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            toast.style.animation = 'slideInFromRight 0.3s ease-out reverse';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }
    
    getToastIcon(type) {
        const icons = {
            success: 'check-circle',
            danger: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || 'bell';
    }
    
    // Utility Functions
    formatPrice(price) {
        if (price >= 1000) {
            return price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        } else if (price >= 1) {
            return price.toFixed(4);
        } else {
            return price.toFixed(8);
        }
    }
    
    // Skeleton Loading
    showSkeleton(container, type = 'card') {
        const skeletons = {
            card: `<div class="skeleton skeleton-card"></div>`,
            table: `<div class="skeleton-row"><div class="skeleton skeleton-cell"></div><div class="skeleton skeleton-cell"></div><div class="skeleton skeleton-cell"></div></div>`,
            text: `<div class="skeleton skeleton-text"></div>`
        };
        
        container.innerHTML = skeletons[type] || skeletons.card;
    }
    
    hideSkeleton(container, content) {
        container.innerHTML = content;
        container.classList.add('animate-fade-in-up');
    }
}

// Skeleton Loader Component
class SkeletonLoader {
    static show(element, count = 1) {
        const type = element.dataset.skeletonType || 'text';
        let html = '';
        
        for (let i = 0; i < count; i++) {
            if (type === 'table') {
                html += `<tr class="skeleton-row"><td colspan="100%"><div class="skeleton skeleton-text"></div></td></tr>`;
            } else if (type === 'card') {
                html += `<div class="skeleton skeleton-card"></div>`;
            } else {
                html += `<div class="skeleton skeleton-text"></div>`;
            }
        }
        
        element.innerHTML = html;
        element.dataset.loading = 'true';
    }
    
    static hide(element, content) {
        element.innerHTML = content;
        delete element.dataset.loading;
        element.classList.add('animate-fade-in-up');
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.realtimeDashboard = new RealtimeDashboard();
    
    // Remove loading state from body
    document.body.removeAttribute('js-loading');
});

// Export for use in other scripts
window.RealtimeDashboard = RealtimeDashboard;
window.SkeletonLoader = SkeletonLoader;
