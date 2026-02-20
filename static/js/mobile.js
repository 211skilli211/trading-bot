/**
 * Mobile-specific JavaScript for Trading Bot Dashboard
 * Handles touch gestures, responsive behavior, and mobile optimizations
 */

(function() {
    'use strict';
    
    // Mobile detection
    const isMobile = window.matchMedia('(max-width: 768px)').matches;
    const isTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    
    // Initialize mobile features
    document.addEventListener('DOMContentLoaded', function() {
        if (isMobile) {
            initMobileFeatures();
        }
        initCommonFeatures();
    });
    
    function initMobileFeatures() {
        // Add mobile class to body
        document.body.classList.add('mobile-device');
        
        // Initialize pull-to-refresh
        initPullToRefresh();
        
        // Initialize swipe gestures
        initSwipeGestures();
        
        // Optimize tables for mobile
        optimizeTables();
        
        // Add touch feedback
        addTouchFeedback();
        
        // Handle viewport changes
        handleViewportChanges();
        
        console.log('[Mobile] Initialized mobile features');
    }
    
    function initCommonFeatures() {
        // Update status indicators
        updateStatusIndicators();
        setInterval(updateStatusIndicators, 30000);
        
        // Check connection status
        checkConnection();
        window.addEventListener('online', () => updateConnectionStatus(true));
        window.addEventListener('offline', () => updateConnectionStatus(false));
    }
    
    // Pull to refresh functionality
    function initPullToRefresh() {
        let startY = 0;
        let currentY = 0;
        let isPulling = false;
        const threshold = 100;
        
        const pullIndicator = document.createElement('div');
        pullIndicator.className = 'pull-indicator text-center py-3 d-none';
        pullIndicator.innerHTML = '<i class="bi bi-arrow-down"></i> Pull to refresh';
        document.body.insertBefore(pullIndicator, document.body.firstChild);
        
        document.addEventListener('touchstart', function(e) {
            if (window.scrollY === 0) {
                startY = e.touches[0].clientY;
                isPulling = true;
            }
        }, { passive: true });
        
        document.addEventListener('touchmove', function(e) {
            if (!isPulling) return;
            
            currentY = e.touches[0].clientY;
            const diff = currentY - startY;
            
            if (diff > 0 && window.scrollY === 0) {
                pullIndicator.classList.remove('d-none');
                
                if (diff > threshold) {
                    pullIndicator.innerHTML = '<i class="bi bi-arrow-up"></i> Release to refresh';
                } else {
                    pullIndicator.innerHTML = '<i class="bi bi-arrow-down"></i> Pull to refresh';
                }
            }
        }, { passive: true });
        
        document.addEventListener('touchend', function() {
            if (!isPulling) return;
            
            const diff = currentY - startY;
            if (diff > threshold && window.scrollY === 0) {
                pullIndicator.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Refreshing...';
                
                // Reload page for fresh data
                setTimeout(() => location.reload(), 500);
            } else {
                pullIndicator.classList.add('d-none');
            }
            
            isPulling = false;
            startY = 0;
            currentY = 0;
        }, { passive: true });
    }
    
    // Swipe gestures for navigation
    function initSwipeGestures() {
        let touchStartX = 0;
        let touchEndX = 0;
        const threshold = 100;
        
        document.addEventListener('touchstart', function(e) {
            touchStartX = e.changedTouches[0].screenX;
        }, { passive: true });
        
        document.addEventListener('touchend', function(e) {
            touchEndX = e.changedTouches[0].screenX;
            handleSwipe();
        }, { passive: true });
        
        function handleSwipe() {
            const diff = touchEndX - touchStartX;
            
            // Swipe right from edge opens sidebar
            if (diff > threshold && touchStartX < 50) {
                const sidebar = document.getElementById('sidebar');
                if (sidebar) {
                    const bsOffcanvas = bootstrap.Offcanvas.getInstance(sidebar) || new bootstrap.Offcanvas(sidebar);
                    bsOffcanvas.show();
                }
            }
            
            // Swipe left closes sidebar
            if (diff < -threshold) {
                const sidebar = document.getElementById('sidebar');
                if (sidebar) {
                    const bsOffcanvas = bootstrap.Offcanvas.getInstance(sidebar);
                    if (bsOffcanvas) bsOffcanvas.hide();
                }
            }
        }
    }
    
    // Optimize tables for mobile
    function optimizeTables() {
        const tables = document.querySelectorAll('.table');
        tables.forEach(table => {
            // Add responsive wrapper if not present
            if (!table.parentElement.classList.contains('table-responsive')) {
                const wrapper = document.createElement('div');
                wrapper.className = 'table-responsive';
                table.parentNode.insertBefore(wrapper, table);
                wrapper.appendChild(table);
            }
            
            // Add data labels for mobile cards view
            if (isMobile) {
                const headers = table.querySelectorAll('thead th');
                const headerTexts = Array.from(headers).map(h => h.textContent);
                
                table.querySelectorAll('tbody tr').forEach(row => {
                    row.querySelectorAll('td').forEach((cell, index) => {
                        if (headerTexts[index]) {
                            cell.setAttribute('data-label', headerTexts[index]);
                        }
                    });
                });
            }
        });
    }
    
    // Add touch feedback for buttons
    function addTouchFeedback() {
        if (!isTouch) return;
        
        const touchElements = document.querySelectorAll('.btn, .nav-link, .dropdown-item');
        touchElements.forEach(el => {
            el.addEventListener('touchstart', function() {
                this.style.transform = 'scale(0.95)';
                this.style.opacity = '0.8';
            }, { passive: true });
            
            el.addEventListener('touchend', function() {
                this.style.transform = '';
                this.style.opacity = '';
            }, { passive: true });
        });
    }
    
    // Handle viewport changes
    function handleViewportChanges() {
        let lastHeight = window.innerHeight;
        
        window.addEventListener('resize', function() {
            const currentHeight = window.innerHeight;
            
            // Handle keyboard open/close on mobile
            if (currentHeight < lastHeight * 0.75) {
                document.body.classList.add('keyboard-open');
            } else {
                document.body.classList.remove('keyboard-open');
            }
            
            lastHeight = currentHeight;
        });
    }
    
    // Update status indicators
    function updateStatusIndicators() {
        // Exchange API status
        fetch('/api/health')
            .then(r => r.json())
            .then(data => {
                updateStatusDot('status-exchange', data.exchange);
                updateStatusDot('mobile-status-exchange', data.exchange);
            })
            .catch(() => {
                updateStatusDot('status-exchange', false);
                updateStatusDot('mobile-status-exchange', false);
            });
        
        // Database status
        fetch('/api/health')
            .then(r => r.json())
            .then(data => {
                updateStatusDot('status-db', data.database);
                updateStatusDot('mobile-status-db', data.database);
            })
            .catch(() => {
                updateStatusDot('status-db', false);
                updateStatusDot('mobile-status-db', false);
            });
        
        // ZeroClaw status
        fetch('/api/zeroclaw/status')
            .then(r => r.json())
            .then(data => {
                const status = data.running;
                updateStatusDot('status-zeroclaw', status);
                updateStatusDot('mobile-status-zeroclaw', status);
            })
            .catch(() => {
                updateStatusDot('status-zeroclaw', false);
                updateStatusDot('mobile-status-zeroclaw', false);
            });
    }
    
    function updateStatusDot(id, isHealthy) {
        const dot = document.getElementById(id);
        if (dot) {
            dot.className = `status-dot ${isHealthy ? 'bg-success' : 'bg-danger'}`;
        }
    }
    
    // Connection status
    function checkConnection() {
        updateConnectionStatus(navigator.onLine);
    }
    
    function updateConnectionStatus(isOnline) {
        const indicator = document.getElementById('connection-status');
        if (indicator) {
            if (isOnline) {
                indicator.className = 'badge bg-success d-none d-sm-inline';
                indicator.innerHTML = '<i class="bi bi-wifi"></i> Online';
            } else {
                indicator.className = 'badge bg-danger d-none d-sm-inline';
                indicator.innerHTML = '<i class="bi bi-wifi-off"></i> Offline';
            }
        }
    }
    
    // Long press for context menu
    function initLongPress() {
        let pressTimer;
        const longPressDuration = 500;
        
        document.querySelectorAll('[data-long-press]').forEach(el => {
            el.addEventListener('touchstart', function(e) {
                pressTimer = setTimeout(() => {
                    this.dispatchEvent(new CustomEvent('longpress'));
                }, longPressDuration);
            }, { passive: true });
            
            el.addEventListener('touchend', function() {
                clearTimeout(pressTimer);
            }, { passive: true });
            
            el.addEventListener('touchmove', function() {
                clearTimeout(pressTimer);
            }, { passive: true });
        });
    }
    
    // Vibration feedback
    function vibrate(pattern = 50) {
        if (navigator.vibrate) {
            navigator.vibrate(pattern);
        }
    }
    
    // Export mobile utilities
    window.MobileUtils = {
        isMobile: isMobile,
        isTouch: isTouch,
        vibrate: vibrate,
        showToast: function(message, type = 'info') {
            if (window.showToast) {
                window.showToast(message, type);
            }
        }
    };
    
})();
