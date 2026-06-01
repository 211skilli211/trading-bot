FROM python:3.11-slim

LABEL maintainer="211skilli211"
LABEL description="Trading Bot — Multi-exchange crypto trading with ML, Solana DEX, Polymarket"

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash trader
USER trader
WORKDIR /home/trader/app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt || true

# Copy app
COPY --chown=trader:trader . .

# Create directories
RUN mkdir -p logs data models

# Health check
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD python3 -c "import trading_bot; print('OK')" || exit 1

# Expose API port
EXPOSE 8080

# Default: run in paper mode with API
ENTRYPOINT ["python3", "trading_bot.py"]
CMD ["--mode", "paper", "--monitor", "60"]
