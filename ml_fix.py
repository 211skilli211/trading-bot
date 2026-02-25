# ML Prediction Routes - Add these to dashboard.py before if __name__ block

@app.route("/api/ml-predictions")
def api_ml_predictions():
    """Get ML predictions for tracked symbols."""
    try:
        # Mock data for now - replace with real analysis
        predictions = [
            {
                "symbol": "BTC/USDT",
                "signal": "BUY",
                "confidence": 78.5,
                "current_price": 64250.00,
                "target_price": 66500.00,
                "stop_loss": 62500.00,
                "timeframe": "1h",
                "reasoning": "RSI oversold bounce, bullish divergence on MACD, strong support at 62k",
                "indicators": {"rsi": 32, "trend": "bullish", "momentum": 2.4, "support": 62000, "resistance": 68000, "volatility": 3.2, "volume_trend": "increasing"},
                "generated_at": "2026-02-25T00:00:00"
            },
            {
                "symbol": "ETH/USDT", 
                "signal": "BUY",
                "confidence": 72.0,
                "current_price": 3450.00,
                "target_price": 3600.00,
                "stop_loss": 3350.00,
                "timeframe": "1h",
                "reasoning": "Breaking above 20EMA, momentum building, volume increasing",
                "indicators": {"rsi": 45, "trend": "neutral", "momentum": 1.2, "support": 3300, "resistance": 3600, "volatility": 2.8, "volume_trend": "increasing"},
                "generated_at": "2026-02-25T00:00:00"
            },
            {
                "symbol": "SOL/USDT",
                "signal": "SELL",
                "confidence": 68.5,
                "current_price": 148.00,
                "target_price": 140.00,
                "stop_loss": 155.00,
                "timeframe": "1h",
                "reasoning": "Overbought RSI, bearish divergence, resistance at 150",
                "indicators": {"rsi": 72, "trend": "bearish", "momentum": -1.8, "support": 140, "resistance": 155, "volatility": 4.1, "volume_trend": "decreasing"},
                "generated_at": "2026-02-25T00:00:00"
            },
        ]
        
        return jsonify({
            "success": True,
            "count": len(predictions),
            "market_summary": {
                "bullish_signals": 2,
                "bearish_signals": 1,
                "neutral_signals": 0,
                "avg_confidence": 73.0
            },
            "predictions": predictions
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/ml/status")
def api_ml_status():
    return jsonify({
        "mlActive": True,
        "agentCount": 6,
        "regime": "trending",
        "regimeConfidence": 72,
        "modelVersion": "ZeroClaw-v2.4.1"
    })
