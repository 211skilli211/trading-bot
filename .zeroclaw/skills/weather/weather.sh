#!/bin/bash
# Weather API Script
CITY="${1:-Basseterre}"  # Default to St. Kitts

if [ -z "$WEATHERAPI_KEY" ]; then
    echo "❌ WEATHERAPI_KEY not set"
    echo ""
    echo "To get weather data:"
    echo "1. Get FREE API key: https://www.weatherapi.com/signup.aspx"
    echo "2. Run: export WEATHERAPI_KEY=your_key_here"
    echo "3. Add to ~/.bashrc to make permanent"
    exit 1
fi

# Make API call
RESPONSE=$(curl -s "https://api.weatherapi.com/v1/current.json?key=$WEATHERAPI_KEY&q=$CITY&aqi=no")

# Check for errors
if echo "$RESPONSE" | grep -q '"error"'; then
    ERROR_MSG=$(echo "$RESPONSE" | grep -o '"message":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo "❌ Weather API Error: $ERROR_MSG"
    exit 1
fi

# Parse JSON response
LOCATION=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['location']['name'])")
REGION=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['location']['region'])")
TEMP_C=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['current']['temp'])")
TEMP_F=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(int(d['current']['temp']*9/5+32))")
CONDITION=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['current']['condition']['text'])")
HUMIDITY=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['current']['humidity'])")
WIND=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(int(d['current']['wind_kph']))")
FEELS_C=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(int(d['current']['feelslike_c']))")

# Get emoji
 case "$CONDITION" in
    *Sunny*|*Clear*) EMOJI="☀️" ;;
    *Cloud*|*Overcast*) EMOJI="☁️" ;;
    *Rain*|*Drizzle*|* shower*) EMOJI="🌧️" ;;
    *Thunder*) EMOJI="⛈️" ;;
    *Snow*) EMOJI="❄️" ;;
    *Fog*|*Mist*) EMOJI="🌫️" ;;
    *) EMOJI="🌡️" ;;
esac

# Output formatted weather
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
