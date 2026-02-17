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

// Auto-refresh every 7 seconds for live feel
setInterval(() => {
    if (!document.hidden) location.reload();
}, 7000);
