module.exports = {
  apps: [{
    name: 'cron-poster',
    script: '/root/trading-bot/.zeroclaw/cron_poster.py',
    interpreter: '/usr/bin/python3',
    instances: 1,
    exec_mode: 'fork',
    // Run every 30 seconds using cron pattern via pm2
    cron_restart: '*/1 * * * *',
    // Keep alive settings
    max_restarts: 10,
    min_uptime: '10s',
    // Don't actually restart - let cron pattern handle it
    autorestart: false,
    // Logs
    log_file: '/tmp/cron_poster.log',
    out_file: '/tmp/cron_poster.out.log',
    error_file: '/tmp/cron_poster.error.log',
    // Environment
    env: {
      HOME: '/tmp/trading_zeroclaw',
      TZ: 'America/St_Kitts'
    }
  }]
}
