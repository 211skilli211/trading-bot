// Trading Bot Dashboard - JavaScript

// Auto-refresh every 5 seconds
setInterval(() => {
  // Only reload if not interacting with forms
  if (!document.querySelector('input:focus, select:focus, textarea:focus')) {
    location.reload();
  }
}, 5000);

// Manual Jupiter Swap
async function executeManualSwap() {
  const inputMint = document.getElementById('inputToken').value;
  const outputMint = document.getElementById('outputToken').value;
  const amount = document.getElementById('swapAmount').value;
  
  if (!amount || amount <= 0) {
    alert('Please enter a valid amount');
    return;
  }
  
  const confirmSwap = confirm(
    `Execute swap?\n${amount} tokens\n${inputMint.slice(0, 8)}... → ${outputMint.slice(0, 8)}...`
  );
  
  if (!confirmSwap) return;
  
  try {
    const response = await fetch('/api/manual_swap', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ inputMint, outputMint, amount: parseFloat(amount) })
    });
    
    const result = await response.json();
    
    if (result.success) {
      alert(`✅ Swap executed!\nTx: ${result.signature.slice(0, 20)}...`);
      location.reload();
    } else {
      alert(`❌ Swap failed: ${result.error}`);
    }
  } catch (error) {
    alert(`❌ Error: ${error.message}`);
  }
}

// Test Alert
async function testAlert() {
  try {
    const response = await fetch('/api/test_alert', { method: 'POST' });
    const result = await response.json();
    alert(result.message);
  } catch (error) {
    alert('Failed to send test alert');
  }
}

// Export trades to CSV
function exportTrades() {
  const table = document.getElementById('tradesTable');
  if (!table) return;
  
  let csv = 'Trade ID,Time,Mode,Buy,Sell,Qty,P&L,Status\n';
  
  table.querySelectorAll('tbody tr').forEach(row => {
    const cells = row.querySelectorAll('td');
    const rowData = Array.from(cells).map(cell => `"${cell.textContent.trim()}"`).join(',');
    csv += rowData + '\n';
  });
  
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `trades_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
}

// Update config
async function saveConfig() {
  const config = {
    mode: document.getElementById('tradingMode').value,
    minSpread: parseFloat(document.getElementById('minSpread').value),
    maxPosition: parseFloat(document.getElementById('maxPosition').value),
    stopLoss: parseFloat(document.getElementById('stopLoss').value)
  };
  
  try {
    const response = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    
    const result = await response.json();
    alert(result.message || 'Config saved!');
  } catch (error) {
    alert('Failed to save config');
  }
}

// Close position
async function closePosition(positionId) {
  if (!confirm(`Close position ${positionId}?`)) return;
  
  try {
    const response = await fetch(`/api/close_position/${positionId}`, {
      method: 'POST'
    });
    
    const result = await response.json();
    
    if (result.success) {
      alert('✅ Position closed');
      location.reload();
    } else {
      alert(`❌ Failed: ${result.error}`);
    }
  } catch (error) {
    alert('Error closing position');
  }
}

// Format numbers
function formatNumber(num, decimals = 2) {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(num);
}

// Format currency
function formatCurrency(num) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(num);
}

// Initialize tooltips
document.addEventListener('DOMContentLoaded', function() {
  const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltipTriggerList.forEach(tooltipTriggerEl => {
    new bootstrap.Tooltip(tooltipTriggerEl);
  });
});

// Chart configuration defaults
Chart.defaults.color = '#8b949e';
Chart.defaults.borderColor = '#30363d';
Chart.defaults.backgroundColor = '#21262d';
