#!/bin/bash
# ZeroClaw Emergency Recovery Script
# Applies fixes for OpenRouter, rate limits, context compression, and Obsidian memory

echo "🔧 Applying ZeroClaw fixes..."

ZEROCLAW_DIR="/sdcard/zeroclaw-workspace/trading-bot/.zeroclaw"

# Backup current configs
cp $ZEROCLAW_DIR/config.toml $ZEROCLAW_DIR/config.toml.bak.$(date +%s)
cp $ZEROCLAW_DIR/config_personal.toml $ZEROCLAW_DIR/config_personal.toml.bak.$(date +%s)

echo "✅ Backups created"

# Fix 1: OpenRouter model
sed -i 's/default_model = "arcee-ai\/trinity-large-preview:free"/default_model = "openrouter\/openrouter\/auto"/g' $ZEROCLAW_DIR/config.toml
sed -i 's/default_model = "arcee-ai\/trinity-large-preview:free"/default_model = "openrouter\/openrouter\/auto"/g' $ZEROCLAW_DIR/config_personal.toml

# Fix 2: Rate limits
sed -i 's/max_actions_per_hour = 20/max_actions_per_hour = 200/g' $ZEROCLAW_DIR/config_personal.toml
sed -i 's/max_cost_per_day_cents = 500/max_cost_per_day_cents = 2500/g' $ZEROCLAW_DIR/config_personal.toml

# Fix 3: Context compression
sed -i 's/compact_context = false/compact_context = true/g' $ZEROCLAW_DIR/config_personal.toml
sed -i 's/max_history_messages = 50/max_history_messages = 20/g' $ZEROCLAW_DIR/config_personal.toml

# Fix 4: Memory backend to markdown
sed -i 's/backend = "sqlite"/backend = "markdown"/g' $ZEROCLAW_DIR/config_personal.toml

# Add Obsidian vault config if not present
if ! grep -q 'vault_path' $ZEROCLAW_DIR/config_personal.toml; then
    cat >> $ZEROCLAW_DIR/config_personal.toml << 'MEMORY'

[memory.markdown]
vault_path = "/storage/emulated/0/Obsidian_notes/211"
memory_subfolder = "zeroclaw-memory"
sync_on_write = true
MEMORY
fi

# Fix ai_agent.py model
sed -i "s/'arcee-ai\/trinity-large-preview:free'/'openrouter\/openrouter\/auto'/g" $ZEROCLAW_DIR/ai_agent.py

echo "✅ All fixes applied"
echo ""
echo "📋 Summary of changes:"
echo "   - OpenRouter model: openrouter/openrouter/auto"
echo "   - Rate limits: 200 actions/hr, \$25/day"
echo "   - Context: compact_context=true, max_history=20"
echo "   - Memory: markdown backend with Obsidian vault"
echo ""
echo "📁 Configs backed up to:"
echo "   $ZEROCLAW_DIR/config.toml.bak.*"
echo "   $ZEROCLAW_DIR/config_personal.toml.bak.*"
