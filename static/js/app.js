function toggleMode() {
    if (confirm("Switch to LIVE? Real money will be used!")) {
        fetch('/api/set_mode', {
            method: 'POST', 
            headers: {'Content-Type': 'application/json'}, 
            body: JSON.stringify({mode: 'LIVE'})
        }).then(() => location.reload());
    }
}

function stopBot() {
    if (confirm("Stop bot now?")) {
        fetch('/api/stop', {method: 'POST'})
        .then(() => alert("Bot stop signal sent"));
    }
}

function executeSwap() {
    const input = document.getElementById('swapInput').value;
    const output = document.getElementById('swapOutput').value;
    const amount = document.getElementById('swapAmount').value;
    
    fetch('/api/manual_swap', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({input, output, amount})
    })
    .then(r => r.json())
    .then(data => alert(data.status || data.message));
}

// Refresh data without full page reload
async function refreshAllData() {
    try {
        const resp = await fetch('/api/data');
        const data = await resp.json();
        
        // Update price displays if they exist
        if (data.prices) {
            document.querySelectorAll('[data-price]').forEach(el => {
                const symbol = el.getAttribute('data-price');
                if (data.prices[symbol]) {
                    el.textContent = '$' + data.prices[symbol].toFixed(2);
                }
            });
        }
        
        // Update status indicators
        if (data.mode) {
            const modeBadge = document.getElementById('mode-badge');
            if (modeBadge) modeBadge.textContent = data.mode;
        }
        
        return data;
    } catch (e) {
        console.error('Refresh error:', e);
    }
}

// Auto-refresh data via API every 30 seconds (not full page reload)
setInterval(() => {
    if (!document.hidden) refreshAllData();
}, 30000);
