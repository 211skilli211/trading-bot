#!/usr/bin/env python3
"""
Visual Dashboard Generator for ZeroClaw Personal Bot
Creates ASCII/text-based dashboard showing projects, activities, and stats
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any

class VisualDashboard:
    def __init__(self):
        self.workspace = os.path.expanduser("~/.zeroclaw")
        self.memory_db = f"{self.workspace}/memory/enhanced_memory.db"
    
    def generate_dashboard(self) -> str:
        """Generate visual dashboard"""
        lines = []
        
        # Header
        lines.append("╔══════════════════════════════════════════════════════════════╗")
        lines.append("║          🤖 ZEROCLAW PERSONAL BOT DASHBOARD                  ║")
        lines.append(f"║          {datetime.now().strftime('%Y-%m-%d %H:%M')}".ljust(63) + "║")
        lines.append("╚══════════════════════════════════════════════════════════════╝")
        lines.append("")
        
        # Get stats
        stats = self._get_stats()
        
        # Today's Activity Box
        lines.append("┌────────────────────── 📅 TODAY'S ACTIVITY ─────────────────────┐")
        lines.append(f"│  📝 Notes Captured: {stats['total_notes']:<4}  (Auto: {stats['auto_notes']}, Manual: {stats['manual_notes']})  │")
        lines.append(f"│  💾 Memory Entries: {stats['memory_entries']:<4}  🏷️  Unique Tags: {stats['unique_tags']:<4}         │")
        lines.append(f"│  ⛓️  Active Chains:  {stats['active_chains']:<4}  💾 Contexts: {stats['contexts']:<4}              │")
        lines.append("└────────────────────────────────────────────────────────────────┘")
        lines.append("")
        
        # Categories Distribution
        lines.append("┌────────────────────── 📂 CATEGORY BREAKDOWN ───────────────────┐")
        cats = stats['categories']
        if cats:
            max_val = max(cats.values()) if cats else 1
            for cat, count in sorted(cats.items(), key=lambda x: x[1], reverse=True)[:5]:
                bar_len = int((count / max_val) * 25)
                bar = "█" * bar_len + "░" * (25 - bar_len)
                lines.append(f"│  {cat:12} │{bar}│ {count:3}  │")
        else:
            lines.append("│  No categories yet. Start capturing notes!                    │")
        lines.append("└────────────────────────────────────────────────────────────────┘")
        lines.append("")
        
        # Recent Entries
        lines.append("┌────────────────────── 🕐 RECENT ENTRIES ──────────────────────┐")
        recent = self._get_recent_entries(4)
        if recent:
            for entry in recent:
                content = entry['content'][:45] + "..." if len(entry['content']) > 45 else entry['content']
                tags = ", ".join(entry['tags'][:2]) if entry['tags'] else "none"
                lines.append(f"│  • {content:48} │")
                lines.append(f"│    🏷️ {tags:20} 📂 {entry['category']:12} │")
                lines.append("│                                                                  │")
        else:
            lines.append("│  No recent entries. Type 'menu' to get started!                 │")
        lines.append("└────────────────────────────────────────────────────────────────┘")
        lines.append("")
        
        # Quick Actions
        lines.append("┌────────────────────── ⚡ QUICK ACTIONS ───────────────────────┐")
        lines.append("│                                                                  │")
        lines.append("│  📝 note [text]     - Quick note          📊 menu    - Dashboard │")
        lines.append("│  🔍 search [query]  - Search memory       ⏰ capture - Auto-save │")
        lines.append("│  ⛓️  taskchain      - Create workflow     🏷️  tag     - Tag entry │")
        lines.append("│                                                                  │")
        lines.append("└────────────────────────────────────────────────────────────────┘")
        lines.append("")
        
        # Footer tip
        lines.append("💡 <i>Tip: Long messages or those with keywords auto-save to memory!</i>")
        
        return "\n".join(lines)
    
    def _get_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics"""
        stats = {
            'total_notes': 0,
            'auto_notes': 0,
            'manual_notes': 0,
            'memory_entries': 0,
            'unique_tags': 0,
            'active_chains': 0,
            'contexts': 0,
            'categories': {}
        }
        
        try:
            conn = sqlite3.connect(self.memory_db)
            cursor = conn.cursor()
            
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Daily notes stats
            cursor.execute("SELECT COUNT(*), SUM(auto_captured) FROM daily_notes WHERE date = ?", (today,))
            row = cursor.fetchone()
            if row:
                stats['total_notes'] = row[0] or 0
                stats['auto_notes'] = row[1] or 0
                stats['manual_notes'] = stats['total_notes'] - stats['auto_notes']
            
            # Memory entries
            cursor.execute("SELECT COUNT(*) FROM memory_entries WHERE timestamp LIKE ?", (f'{today}%',))
            stats['memory_entries'] = cursor.fetchone()[0] or 0
            
            # Unique tags
            cursor.execute("SELECT tags FROM memory_entries")
            all_tags = set()
            for row in cursor.fetchall():
                if row[0]:
                    tags = json.loads(row[0])
                    all_tags.update(tags)
            stats['unique_tags'] = len(all_tags)
            
            # Active chains
            cursor.execute("SELECT COUNT(*) FROM task_chains WHERE status = 'active'")
            stats['active_chains'] = cursor.fetchone()[0] or 0
            
            # Contexts
            cursor.execute("SELECT COUNT(*) FROM context_snapshots")
            stats['contexts'] = cursor.fetchone()[0] or 0
            
            # Categories
            cursor.execute("SELECT category, COUNT(*) FROM memory_entries GROUP BY category")
            stats['categories'] = {row[0]: row[1] for row in cursor.fetchall()}
            
            conn.close()
        except Exception as e:
            pass
        
        return stats
    
    def _get_recent_entries(self, limit: int = 5) -> List[Dict]:
        """Get recent memory entries"""
        entries = []
        
        try:
            conn = sqlite3.connect(self.memory_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT content, tags, category, timestamp 
                FROM memory_entries 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            for row in cursor.fetchall():
                entries.append({
                    'content': row[0],
                    'tags': json.loads(row[1]) if row[1] else [],
                    'category': row[2],
                    'timestamp': row[3]
                })
            
            conn.close()
        except:
            pass
        
        return entries
    
    def generate_project_view(self) -> str:
        """Generate project-focused view"""
        lines = []
        
        lines.append("╔══════════════════════════════════════════════════════════════╗")
        lines.append("║                   📊 PROJECT OVERVIEW                        ║")
        lines.append("╚══════════════════════════════════════════════════════════════╝")
        lines.append("")
        
        # Get projects from categories
        try:
            conn = sqlite3.connect(self.memory_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT category, COUNT(*) as count, 
                       GROUP_CONCAT(content, '|||') as contents
                FROM memory_entries 
                GROUP BY category 
                ORDER BY count DESC
            ''')
            
            for row in cursor.fetchall():
                cat, count, contents = row
                lines.append(f"┌────────────────── {cat.upper()} ({count} items) ──────────────────┐")
                
                # Show top 3 items
                items = contents.split('|||')[:3]
                for item in items:
                    short = item[:50] + "..." if len(item) > 50 else item
                    lines.append(f"│  • {short:56} │")
                
                if count > 3:
                    lines.append(f"│  ... and {count - 3} more{' ' * 45} │")
                
                lines.append("└────────────────────────────────────────────────────────────────┘")
                lines.append("")
            
            conn.close()
        except:
            lines.append("No projects found yet. Start capturing notes to build your project dashboard!")
        
        return "\n".join(lines)


def main():
    import sys
    
    dashboard = VisualDashboard()
    
    if len(sys.argv) > 1 and sys.argv[1] == "projects":
        print(dashboard.generate_project_view())
    else:
        print(dashboard.generate_dashboard())


if __name__ == "__main__":
    main()
