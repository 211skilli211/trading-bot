#!/usr/bin/env python3
"""
Trading Memory System
====================
Persistent Git-style memory for learning from trades.

Features:
- Log trades to strategy-specific branches
- Query historical patterns
- Track bot performance over time
- Store news for Catalyst strategy
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


class TradingMemory:
    """Persistent trading memory system"""
    
    def __init__(self, root_path: str = "./memory"):
        self.root = root_path
        self.main_file = f"{root_path}/main.md"
        self.metadata_file = f"{root_path}/metadata.json"
        self.news_db = f"{root_path}/news_db.json"
        self._init_structure()
    
    def _init_structure(self):
        """Create memory directory structure"""
        # Create root directories
        os.makedirs(f"{self.root}/branches", exist_ok=True)
        
        # Create strategy branches
        branches = ["arbitrage", "sniper", "catalyst", "multi_agent", "general"]
        for branch in branches:
            os.makedirs(f"{self.root}/branches/{branch}", exist_ok=True)
        
        # Initialize main.md if not exists
        if not os.path.exists(self.main_file):
            with open(self.main_file, 'w') as f:
                f.write("""# Global Strategy Rules

## Risk Management
- Risk 1% per trade
- Circuit breaker: 3 consecutive losses
- Max position: 10% of capital
- No trading during major news (Fed, SEC)

## Strategy Rules

### Binary Arbitrage
- Only trade when YES + NO < $0.99
- Min profit threshold: 1%
- Max position: $10 per arb

### 15-Minute Sniper
- Momentum threshold: 10%
- Entry window: last 60 seconds
- Max concurrent: 3 trades

### Multi-Agent
- Kill bottom 20% after 3 losses
- Scale top 20% winners by 25%
- Daily evaluation cycle

## Lessons Learned
- (Add lessons as they are discovered)

---
*Last Updated: {last_updated}*
""".format(last_updated=datetime.now(timezone.utc).isoformat()))
        
        # Initialize metadata.json
        if not os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'w') as f:
                json.dump({
                    "total_pnl": 0.0,
                    "total_trades": 0,
                    "win_rate": 0.0,
                    "wins": 0,
                    "losses": 0,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "strategies": {}
                }, f, indent=2)
        
        # Initialize news_db.json
        if not os.path.exists(self.news_db):
            with open(self.news_db, 'w') as f:
                json.dump([], f)
    
    def log_trade(self, strategy: str, pnl: float, notes: str, 
                  metadata: Dict = None, trade_type: str = "trade") -> int:
        """
        Log a trade to strategy branch.
        
        Args:
            strategy: Strategy name (arbitrage, sniper, catalyst, etc.)
            pnl: Profit/loss amount
            notes: Trade notes
            metadata: Additional metadata
            trade_type: Type of log (trade, error, lesson)
        
        Returns:
            commit_id: Number of this commit
        """
        branch_path = f"{self.root}/branches/{strategy}"
        os.makedirs(branch_path, exist_ok=True)
        
        # Count existing commits
        existing = [f for f in os.listdir(branch_path) if f.startswith("log_")]
        commit_id = len(existing) + 1
        
        # Format timestamp
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Determine file extension based on type
        ext = ".md"
        
        log_data = {
            "commit_id": commit_id,
            "strategy": strategy,
            "timestamp": timestamp,
            "pnl": pnl,
            "notes": notes,
            "metadata": metadata or {}
        }
        
        # Write log file
        filename = f"{branch_path}/log_{commit_id:04d}{ext}"
        with open(filename, 'w') as f:
            f.write(f"""# {strategy.title()} Log #{commit_id}

**Date:** {timestamp}
**PnL:** ${pnl:+.2f}
**Type:** {trade_type}

## Notes
{notes}

## Metadata
```json
{json.dumps(metadata or {}, indent=2)}
```
""")
        
        # Update metadata
        self._update_metadata(pnl, strategy)
        
        return commit_id
    
    def log_lesson(self, strategy: str, lesson: str, context: str = "") -> int:
        """
        Log a learned lesson.
        
        Args:
            strategy: Strategy name
            lesson: What was learned
            context: Additional context
        
        Returns:
            commit_id
        """
        branch_path = f"{self.root}/branches/{strategy}"
        os.makedirs(branch_path, exist_ok=True)
        
        existing = [f for f in os.listdir(branch_path) if f.startswith("lesson_")]
        commit_id = len(existing) + 1
        
        filename = f"{branch_path}/lesson_{commit_id:04d}.md"
        with open(filename, 'w') as f:
            f.write(f"""# Lesson #{commit_id}

**Strategy:** {strategy}
**Date:** {datetime.now(timezone.utc).isoformat()}

## Lesson
{lesson}

## Context
{context}
""")
        
        # Also update main.md with important lessons
        self._add_to_main(lesson)
        
        return commit_id
    
    def _update_metadata(self, pnl: float, strategy: str):
        """Update overall bot statistics"""
        with open(self.metadata_file, 'r') as f:
            meta = json.load(f)
        
        # Update totals
        meta["total_pnl"] += pnl
        meta["total_trades"] += 1
        meta["last_updated"] = datetime.now(timezone.utc).isoformat()
        
        if pnl > 0:
            meta["wins"] = meta.get("wins", 0) + 1
        else:
            meta["losses"] = meta.get("losses", 0) + 1
        
        # Update win rate
        total = meta["wins"] + meta["losses"]
        meta["win_rate"] = (meta["wins"] / total * 100) if total > 0 else 0
        
        # Update strategy-specific stats
        if "strategies" not in meta:
            meta["strategies"] = {}
        
        if strategy not in meta["strategies"]:
            meta["strategies"][strategy] = {"trades": 0, "pnl": 0, "wins": 0}
        
        meta["strategies"][strategy]["trades"] += 1
        meta["strategies"][strategy]["pnl"] += pnl
        if pnl > 0:
            meta["strategies"][strategy]["wins"] += 1
        
        with open(self.metadata_file, 'w') as f:
            json.dump(meta, f, indent=2)
    
    def _add_to_main(self, lesson: str):
        """Add important lesson to main.md"""
        with open(self.main_file, 'r') as f:
            content = f.read()
        
        # Find Lessons Learned section
        if "## Lessons Learned" in content:
            # Append to lessons section
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("## Lessons Learned"):
                    insert_pos = i + 2
                    break
            
            new_lines = lines[:insert_pos] + [f"- {lesson}"] + lines[insert_pos:]
            content = "\n".join(new_lines)
        else:
            content += f"\n\n## Lessons Learned\n- {lesson}"
        
        with open(self.main_file, 'w') as f:
            f.write(content)
    
    def add_news(self, articles: List[Dict]) -> int:
        """
        Add Ground News articles to news_db.
        
        Args:
            articles: List of article dicts with title, sentiment, bias, sources
        
        Returns:
            Number of articles added
        """
        with open(self.news_db, 'r') as f:
            news = json.load(f)
        
        for article in articles:
            news.append({
                "date": datetime.now(timezone.utc).isoformat(),
                "headline": article.get("title", ""),
                "sentiment": article.get("sentiment", 0),
                "bias": article.get("bias", "unknown"),
                "sources": article.get("sources", []),
                "url": article.get("url", ""),
                "keywords": article.get("keywords", [])
            })
        
        # Keep only last 30 days (storage optimization)
        cutoff = datetime.now(timezone.utc).timestamp() - (30 * 24 * 60 * 60)
        news = [n for n in news if datetime.fromisoformat(n["date"]).timestamp() > cutoff]
        
        with open(self.news_db, 'w') as f:
            json.dump(news, f, indent=2)
        
        return len(articles)
    
    def query_history(self, strategy: str = None, keyword: str = None, 
                     limit: int = 10) -> List[Dict]:
        """
        Query past trades for patterns.
        
        Args:
            strategy: Filter by strategy (optional)
            keyword: Search keyword (optional)
            limit: Max results
        
        Returns:
            List of matching log entries
        """
        results = []
        
        # Determine search path
        if strategy:
            search_paths = [f"{self.root}/branches/{strategy}"]
        else:
            search_paths = [
                f"{self.root}/branches/{b}" 
                for b in os.listdir(f"{self.root}/branches")
            ]
        
        for search_path in search_paths:
            if not os.path.exists(search_path):
                continue
            
            for file in os.listdir(search_path):
                if not file.startswith(("log_", "lesson_")):
                    continue
                
                filepath = os.path.join(search_path, file)
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                        
                        if keyword and keyword.lower() not in content.lower():
                            continue
                        
                        results.append({
                            "file": file,
                            "path": filepath,
                            "strategy": os.path.basename(search_path),
                            "content": content
                        })
                except Exception:
                    continue
        
        return results[:limit]
    
    def get_news_sentiment(self, hours: int = 24, keywords: List[str] = None) -> Dict:
        """
        Get aggregated sentiment from recent news.
        
        Args:
            hours: Look back period
            keywords: Filter by keywords
        
        Returns:
            Dict with sentiment, count, bias
        """
        with open(self.news_db, 'r') as f:
            news = json.load(f)
        
        cutoff = datetime.now(timezone.utc).timestamp() - (hours * 60 * 60)
        recent = [n for n in news if datetime.fromisoformat(n["date"]).timestamp() > cutoff]
        
        if keywords:
            recent = [
                n for n in recent 
                if any(k.lower() in n.get("headline", "").lower() for k in keywords)
            ]
        
        if not recent:
            return {"sentiment": 0, "count": 0, "bias": "unknown", "bias_distribution": {}}
        
        # Calculate average sentiment
        sentiments = [n.get("sentiment", 0) for n in recent]
        avg_sentiment = sum(sentiments) / len(sentiments)
        
        # Calculate bias distribution
        bias_counts = {"left": 0, "center": 0, "right": 0}
        for n in recent:
            bias = n.get("bias", "unknown")
            if bias in bias_counts:
                bias_counts[bias] += 1
        
        dominant_bias = max(bias_counts, key=bias_counts.get)
        
        return {
            "sentiment": avg_sentiment,
            "count": len(recent),
            "bias": dominant_bias,
            "bias_distribution": bias_counts
        }
    
    def get_stats(self) -> Dict:
        """Get overall bot statistics"""
        with open(self.metadata_file, 'r') as f:
            return json.load(f)
    
    def get_strategy_stats(self, strategy: str) -> Dict:
        """Get strategy-specific statistics"""
        meta = self.get_stats()
        return meta.get("strategies", {}).get(strategy, {})


# CLI test
if __name__ == "__main__":
    print("Testing TradingMemory...")
    
    memory = TradingMemory()
    
    # Test logging a trade
    commit_id = memory.log_trade(
        strategy="sniper",
        pnl=2.50,
        notes="SOL momentum trade - 10% upward momentum detected",
        metadata={"pair": "SOL", "side": "YES", "confidence": 0.85}
    )
    print(f"Logged trade #{commit_id}")
    
    # Test querying
    results = memory.query_history(strategy="sniper", keyword="SOL")
    print(f"Found {len(results)} matching logs")
    
    # Test stats
    stats = memory.get_stats()
    print(f"\nTotal P&L: ${stats['total_pnl']:.2f}")
    print(f"Win Rate: {stats['win_rate']:.1f}%")
    print(f"Total Trades: {stats['total_trades']}")
