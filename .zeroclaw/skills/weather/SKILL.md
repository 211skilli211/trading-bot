---
name: weather
description: Get current weather for any city using OpenWeatherMap API.
triggers:
  - weather
  - temperature
  - forecast
---

# Weather Skill

Get real-time weather data from OpenWeatherMap API.

## Setup Required

1. **Sign up FREE:** https://home.openweathermap.org/users/sign_up
   - No credit card required
   - 1000 API calls/day free
   - Key activates instantly

2. **Get API Key:**
   - Log in → Go to "API Keys" tab
   - Copy your default key (32 characters)

3. **Set Environment Variable:**
   ```bash
   export OPENWEATHER_API_KEY=your_key_here
   echo 'export OPENWEATHER_API_KEY=your_key' >> ~/.bashrc
   ```

## Usage

- `weather` - Weather in Basseterre (default)
- `weather London` - Weather in London
- `weather in Tokyo` - Weather in Tokyo
- `weather New York` - Weather in New York

## Output Format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

☀️ Weather in Basseterre, KN

🌡️  Temperature: 28°C (82°F)
🤔 Feels like: 30°C
☁️  Condition: Partly cloudy
💧 Humidity: 65%
💨 Wind: 5 m/s

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## API Limits

- Free tier: 1000 calls/day
- Rate limit: 60 calls/minute
- More than enough for personal use!
