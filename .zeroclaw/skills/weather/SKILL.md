---
name: weather
description: Get current weather for any city. Use when user asks "what's the weather", "weather in [city]", "is it raining", etc.
triggers:
  - weather
  - forecast
  - temperature
  - rain
  - sunny
---

# Weather Skill

Get real-time weather data from WeatherAPI.com

## Setup Required

1. Get free API key: https://www.weatherapi.com/signup.aspx
2. Set environment variable: `export WEATHERAPI_KEY=your_key_here`
3. Add to ~/.bashrc to persist: `echo 'export WEATHERAPI_KEY=your_key' >> ~/.bashrc`

## Execute

```bash
#!/bin/bash
CITY="$1"
[ -z "$CITY" ] && CITY="Basseterre"  # Default to St. Kitts

if [ -z "$WEATHERAPI_KEY" ]; then
    echo "❌ WEATHERAPI_KEY not set"
    echo "Get free key: https://www.weatherapi.com/signup.aspx"
    exit 1
fi

# Call Weather API
RESPONSE=$(curl -s "https://api.weatherapi.com/v1/current.json?key=$WEATHERAPI_KEY&q=$CITY&aqi=no")

# Check for errors
if echo "$RESPONSE" | grep -q "error"; then
    echo "❌ Error: $(echo "$RESPONSE" | grep -o '"message":"[^"]*"' | cut -d'"' -f4)"
    exit 1
fi

# Parse and format
LOCATION=$(echo "$RESPONSE" | grep -o '"name":"[^"]*"' | head -1 | cut -d'"' -f4)
REGION=$(echo "$RESPONSE" | grep -o '"region":"[^"]*"' | cut -d'"' -f4)
TEMP_C=$(echo "$RESPONSE" | grep -o '"temp_c":[^,]*' | cut -d':' -f2)
TEMP_F=$(echo "$RESPONSE" | grep -o '"temp_f":[^,]*' | cut -d':' -f2)
CONDITION=$(echo "$RESPONSE" | grep -o '"text":"[^"]*"' | head -1 | cut -d'"' -f4)
HUMIDITY=$(echo "$RESPONSE" | grep -o '"humidity":[^,]*' | cut -d':' -f2)
WIND=$(echo "$RESPONSE" | grep -o '"wind_kph":[^,]*' | cut -d':' -f2)
FEELS_C=$(echo "$RESPONSE" | grep -o '"feelslike_c":[^,]*' | cut -d':' -f2)

# Get weather emoji
 case "$CONDITION" in
    *Sunny*|*Clear*) EMOJI="☀️" ;;
    *Cloud*|*Overcast*) EMOJI="☁️" ;;
    *Rain*|*Drizzle*) EMOJI="🌧️" ;;
    *Thunder*) EMOJI="⛈️" ;;
    *Snow*) EMOJI="❄️" ;;
    *Fog*|*Mist*) EMOJI="🌫️" ;;
    *) EMOJI="🌡️" ;;
esac

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "$EMOJI Weather in $LOCATION, $REGION"
echo ""
echo "🌡️  Temperature: ${TEMP_C}°C (${TEMP_F}°F)"
echo "🤔 Feels like: ${FEELS_C}°C"
echo "☁️  Condition: $CONDITION"
echo "💧 Humidity: ${HUMIDITY}%"
echo "💨 Wind: ${WIND} km/h"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

## Usage Examples

- `weather` - Weather in default city (Basseterre)
- `weather London` - Weather in London
- `weather in Tokyo` - Weather in Tokyo
- `what's the weather like` - Default city weather
