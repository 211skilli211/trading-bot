#!/bin/bash
# Weather API Script - OpenWeatherMap
CITY="${1:-Basseterre}"

if [ -z "$OPENWEATHER_API_KEY" ]; then
    echo "❌ OPENWEATHER_API_KEY not set"
    echo ""
    echo "To get weather data:"
    echo "1. Get FREE API key: https://home.openweathermap.org/users/sign_up"
    echo "2. Run: export OPENWEATHER_API_KEY=your_key_here"
    echo "3. Add to ~/.bashrc to make permanent"
    exit 1
fi

# Make API call
RESPONSE=$(curl -s "https://api.openweathermap.org/data/2.5/weather?q=$CITY&appid=$OPENWEATHER_API_KEY&units=metric")

# Check for errors
if echo "$RESPONSE" | grep -q '"cod":"401"'; then
    echo "❌ Invalid API key"
    exit 1
fi

if echo "$RESPONSE" | grep -q '"cod":"404"'; then
    echo "❌ City not found: $CITY"
    exit 1
fi

# Parse JSON response
CITY_NAME=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['name'])")
COUNTRY=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['sys']['country'])")
TEMP=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(int(d['main']['temp']))")
FEELS=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(int(d['main']['feels_like']))")
HUMIDITY=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['main']['humidity'])")
WIND=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(int(d['wind']['speed']))")
CONDITION=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['weather'][0]['description'].title())")

# Convert to Fahrenheit
TEMP_F=$((TEMP * 9/5 + 32))

# Get emoji based on condition
 case "$CONDITION" in
    *Clear*|*Sunny*) EMOJI="☀️" ;;
    *Cloud*) EMOJI="☁️" ;;
    *Rain*|*Drizzle*) EMOJI="🌧️" ;;
    *Thunder*) EMOJI="⛈️" ;;
    *Snow*) EMOJI="❄️" ;;
    *Fog*|*Mist*|*Haze*) EMOJI="🌫️" ;;
    *) EMOJI="🌡️" ;;
esac

# Output formatted weather
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "$EMOJI Weather in $CITY_NAME, $COUNTRY"
echo ""
echo "🌡️  Temperature: ${TEMP}°C (${TEMP_F}°F)"
echo "🤔 Feels like: ${FEELS}°C"
echo "☁️  Condition: $CONDITION"
echo "💧 Humidity: ${HUMIDITY}%"
echo "💨 Wind: ${WIND} m/s"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
