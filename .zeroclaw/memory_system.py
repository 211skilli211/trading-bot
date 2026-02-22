#!/usr/bin/env python3
"""
Enhanced Memory System for ZeroClaw Personal Bot
Auto-capture, tagging, context-aware recall, and memory vault
"""

import json
import os
import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import re

class MemorySystem:
    def __init__(self):
        self.workspace = os.path.expanduser("~/.zeroclaw")
        self.db_path = f"{self.workspace}/memory/enhanced_memory.db"
        self.vault_path = f"{self.workspace}/memory/vault"
        
        # Ensure directories exist
        os.makedirs(f"{self.workspace}/memory", exist_ok=True)
        os.makedirs(self.vault_path, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for enhanced memory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main memory entries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_entries (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                source TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                tags TEXT,
                category TEXT,
                importance INTEGER DEFAULT 5,
                context_snapshot TEXT,
                related_entries TEXT,
                access_count INTEGER DEFAULT 0,
                last_accessed TEXT
            )
        ''')
        
        # Daily notes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                content TEXT NOT NULL,
                auto_captured BOOLEAN DEFAULT FALSE,
                tags TEXT,
                timestamp TEXT NOT NULL
            )
        ''')
        
        # Context snapshots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS context_snapshots (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                context_data TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                resume_count INTEGER DEFAULT 0
            )
        ''')
        
        # Task chains table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_chains (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                tasks TEXT NOT NULL,
                current_step INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # File categorization table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                project TEXT,
                tags TEXT,
                last_accessed TEXT
            )
        ''')
        
        # Create indexes for faster searching
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_memory_tags ON memory_entries(tags)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_memory_category ON memory_entries(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_memory_timestamp ON memory_entries(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_notes_date ON daily_notes(date)')
        
        conn.commit()
        conn.close()
    
    def generate_id(self, content: str) -> str:
        """Generate unique ID for memory entry"""
        timestamp = datetime.now().isoformat()
        return hashlib.md5(f"{content}{timestamp}".encode()).hexdigest()[:12]
    
    def auto_capture_note(self, content: str, source: str = "conversation", 
                         tags: List[str] = None) -> Dict[str, Any]:
        """Automatically capture a note from conversation"""
        entry_id = self.generate_id(content)
        timestamp = datetime.now().isoformat()
        
        # Auto-extract tags from content
        auto_tags = self._extract_tags(content)
        if tags:
            auto_tags.extend(tags)
        auto_tags = list(set(auto_tags))  # Remove duplicates
        
        # Determine category
        category = self._categorize_content(content)
        
        # Calculate importance based on keywords
        importance = self._calculate_importance(content)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO memory_entries 
            (id, content, source, timestamp, tags, category, importance, access_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry_id, content, source, timestamp, 
            json.dumps(auto_tags), category, importance, 0
        ))
        
        conn.commit()
        conn.close()
        
        # Also save to daily notes
        self._add_to_daily_notes(content, auto_captured=True, tags=auto_tags)
        
        return {
            "success": True,
            "id": entry_id,
            "tags": auto_tags,
            "category": category,
            "importance": importance,
            "message": f"🧠 Auto-captured to {category}"
        }
    
    def _extract_tags(self, content: str) -> List[str]:
        """Auto-extract tags from content"""
        tags = []
        content_lower = content.lower()
        
        # Tag patterns
        tag_patterns = {
            "idea": ["idea", "thought", "concept", "proposal"],
            "task": ["todo", "task", "need to", "should", "must"],
            "decision": ["decided", "decision", "choose", "selected"],
            "important": ["important", "critical", "crucial", "key"],
            "reminder": ["remember", "don't forget", "remind"],
            "question": ["question", "wonder", "curious", "how to"],
            "learning": ["learned", "discovered", "found out", "read that"],
            "meeting": ["meeting", "discussed", "talked", "call"],
            "project": ["project", "working on", "building", "creating"],
            "bug": ["bug", "error", "issue", "problem", "broken"],
            "feature": ["feature", "enhancement", "improvement", "add"]
        }
        
        for tag, keywords in tag_patterns.items():
            if any(kw in content_lower for kw in keywords):
                tags.append(tag)
        
        return tags
    
    def _categorize_content(self, content: str) -> str:
        """Auto-categorize content"""
        content_lower = content.lower()
        
        categories = {
            "work": ["work", "job", "project", "client", "meeting", "deadline"],
            "personal": ["personal", "family", "home", "life", "hobby"],
            "learning": ["learn", "study", "course", "book", "article", "research"],
            "ideas": ["idea", "thought", "concept", "brainstorm", "innovation"],
            "tasks": ["todo", "task", "need to", "should do", "remind me"],
            "decisions": ["decided", "decision", "choose", "option", "plan"]
        }
        
        scores = {}
        for category, keywords in categories.items():
            score = sum(1 for kw in keywords if kw in content_lower)
            if score > 0:
                scores[category] = score
        
        if scores:
            return max(scores, key=scores.get)
        return "general"
    
    def _calculate_importance(self, content: str) -> int:
        """Calculate importance score (1-10)"""
        score = 5  # Base score
        content_lower = content.lower()
        
        # Increase for important keywords
        important_keywords = ["critical", "urgent", "important", "deadline", "decided", "key"]
        score += sum(1 for kw in important_keywords if kw in content_lower)
        
        # Decrease for casual phrases
        casual_phrases = ["maybe", "perhaps", "not sure", "thinking about"]
        score -= sum(1 for ph in casual_phrases if ph in content_lower)
        
        return max(1, min(10, score))
    
    def _add_to_daily_notes(self, content: str, auto_captured: bool = False, 
                           tags: List[str] = None):
        """Add entry to daily notes"""
        today = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO daily_notes (date, content, auto_captured, tags, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (today, content, auto_captured, json.dumps(tags or []), timestamp))
        
        conn.commit()
        conn.close()
    
    def tag_memory(self, entry_id: str, tags: List[str]) -> Dict[str, Any]:
        """Tag an existing memory entry"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get existing tags
        cursor.execute("SELECT tags FROM memory_entries WHERE id = ?", (entry_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return {"success": False, "error": "Entry not found"}
        
        existing_tags = json.loads(row[0]) if row[0] else []
        all_tags = list(set(existing_tags + tags))
        
        cursor.execute('''
            UPDATE memory_entries 
            SET tags = ?, last_accessed = ?
            WHERE id = ?
        ''', (json.dumps(all_tags), datetime.now().isoformat(), entry_id))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "entry_id": entry_id,
            "tags": all_tags,
            "message": f"🏷️ Tagged with: {', '.join(tags)}"
        }
    
    def summarize_conversation(self, conversation_text: str) -> Dict[str, Any]:
        """Auto-summarize a long conversation into key points"""
        lines = conversation_text.strip().split('\n')
        
        # Extract key sentences (those with important markers)
        key_points = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for key indicators
            indicators = [
                "decided", "decision", "conclusion", "important", "key",
                "remember", "note", "action item", "todo", "task",
                "idea", "suggestion", "recommendation", "plan"
            ]
            
            if any(ind in line.lower() for ind in indicators) and len(line) > 20:
                key_points.append(line)
        
        # If no key points found, take first and last meaningful sentences
        if not key_points:
            for line in lines:
                if len(line.strip()) > 30:
                    key_points.append(line.strip())
                    break
            for line in reversed(lines):
                if len(line.strip()) > 30:
                    key_points.append(line.strip())
                    break
        
        summary = "\n".join([f"• {point}" for point in key_points[:5]])
        
        # Store the summary
        result = self.auto_capture_note(
            f"📝 Conversation Summary:\n{summary}",
            source="auto_summary",
            tags=["summary", "conversation"]
        )
        
        return {
            "success": True,
            "summary": summary,
            "key_points": len(key_points),
            "entry_id": result.get("id"),
            "message": f"📝 Summarized {len(lines)} lines into {len(key_points)} key points"
        }
    
    def find_connections(self, entry_id: str) -> Dict[str, Any]:
        """Find related memory entries"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get the source entry
        cursor.execute("SELECT content, tags, category FROM memory_entries WHERE id = ?", (entry_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return {"success": False, "error": "Entry not found"}
        
        content, tags_json, category = row
        tags = json.loads(tags_json) if tags_json else []
        
        # Find related entries
        related = []
        
        # Search by tags
        for tag in tags:
            cursor.execute('''
                SELECT id, content, timestamp FROM memory_entries 
                WHERE tags LIKE ? AND id != ?
                ORDER BY timestamp DESC
                LIMIT 3
            ''', (f'%"{tag}"%', entry_id))
            
            for r in cursor.fetchall():
                related.append({
                    "id": r[0],
                    "content": r[1][:100] + "..." if len(r[1]) > 100 else r[1],
                    "timestamp": r[2],
                    "connection": f"tag:{tag}"
                })
        
        # Search by category
        cursor.execute('''
            SELECT id, content, timestamp FROM memory_entries 
            WHERE category = ? AND id != ?
            ORDER BY timestamp DESC
            LIMIT 3
        ''', (category, entry_id))
        
        for r in cursor.fetchall():
            related.append({
                "id": r[0],
                "content": r[1][:100] + "..." if len(r[1]) > 100 else r[1],
                "timestamp": r[2],
                "connection": f"category:{category}"
            })
        
        conn.close()
        
        # Remove duplicates
        seen_ids = set()
        unique_related = []
        for r in related:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                unique_related.append(r)
        
        return {
            "success": True,
            "entry_id": entry_id,
            "related_count": len(unique_related),
            "related_entries": unique_related[:5],
            "message": f"🔗 Found {len(unique_related)} related entries"
        }
    
    def smart_search(self, query: str) -> Dict[str, Any]:
        """Search across memory, files, and content"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        results = {
            "memory": [],
            "daily_notes": [],
            "files": []
        }
        
        query_lower = query.lower()
        
        # Search memory entries
        cursor.execute('''
            SELECT id, content, tags, category, timestamp, importance 
            FROM memory_entries 
            WHERE content LIKE ? OR tags LIKE ?
            ORDER BY importance DESC, timestamp DESC
            LIMIT 10
        ''', (f'%{query}%', f'%{query}%'))
        
        for row in cursor.fetchall():
            results["memory"].append({
                "id": row[0],
                "content": row[1][:150] + "..." if len(row[1]) > 150 else row[1],
                "tags": json.loads(row[2]) if row[2] else [],
                "category": row[3],
                "timestamp": row[4],
                "importance": row[5]
            })
        
        # Search daily notes
        cursor.execute('''
            SELECT date, content, tags FROM daily_notes 
            WHERE content LIKE ?
            ORDER BY date DESC
            LIMIT 5
        ''', (f'%{query}%',))
        
        for row in cursor.fetchall():
            results["daily_notes"].append({
                "date": row[0],
                "content": row[1][:100] + "..." if len(row[1]) > 100 else row[1],
                "tags": json.loads(row[2]) if row[2] else []
            })
        
        conn.close()
        
        total = len(results["memory"]) + len(results["daily_notes"])
        
        return {
            "success": True,
            "query": query,
            "total_results": total,
            "results": results,
            "message": f"🔍 Found {total} results for '{query}'"
        }
    
    def save_context_snapshot(self, name: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save current working context to resume later"""
        snapshot_id = self.generate_id(name)
        timestamp = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO context_snapshots (id, name, context_data, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (snapshot_id, name, json.dumps(context_data), timestamp))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "snapshot_id": snapshot_id,
            "name": name,
            "message": f"💾 Context snapshot saved: '{name}'"
        }
    
    def list_context_snapshots(self) -> List[Dict[str, Any]]:
        """List all saved context snapshots"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, timestamp, resume_count 
            FROM context_snapshots 
            ORDER BY timestamp DESC
        ''')
        
        snapshots = []
        for row in cursor.fetchall():
            snapshots.append({
                "id": row[0],
                "name": row[1],
                "created": row[2],
                "resumed": row[3]
            })
        
        conn.close()
        return snapshots
    
    def create_task_chain(self, name: str, tasks: List[str]) -> Dict[str, Any]:
        """Create a chain of related tasks"""
        chain_id = self.generate_id(name)
        timestamp = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO task_chains (id, name, tasks, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (chain_id, name, json.dumps(tasks), timestamp, timestamp))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "chain_id": chain_id,
            "name": name,
            "total_tasks": len(tasks),
            "message": f"⛓️ Task chain created: '{name}' ({len(tasks)} tasks)"
        }
    
    def get_task_chain(self, chain_id: str) -> Dict[str, Any]:
        """Get task chain status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT name, tasks, current_step, status FROM task_chains WHERE id = ?
        ''', (chain_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {"success": False, "error": "Task chain not found"}
        
        tasks = json.loads(row[1])
        current = row[2]
        
        return {
            "success": True,
            "chain_id": chain_id,
            "name": row[0],
            "tasks": tasks,
            "current_step": current,
            "status": row[3],
            "progress": f"{current}/{len(tasks)}",
            "current_task": tasks[current] if current < len(tasks) else "Complete"
        }
    
    def get_daily_summary(self, date: str = None) -> Dict[str, Any]:
        """Get summary of a day's activities"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get daily notes
        cursor.execute('''
            SELECT content, auto_captured, tags FROM daily_notes WHERE date = ?
        ''', (date,))
        
        notes = []
        auto_count = 0
        for row in cursor.fetchall():
            notes.append({
                "content": row[0][:80] + "..." if len(row[0]) > 80 else row[0],
                "auto": row[1],
                "tags": json.loads(row[2]) if row[2] else []
            })
            if row[1]:
                auto_count += 1
        
        # Get memory entries for the day
        cursor.execute('''
            SELECT category, COUNT(*) FROM memory_entries 
            WHERE timestamp LIKE ?
            GROUP BY category
        ''', (f'{date}%',))
        
        categories = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            "success": True,
            "date": date,
            "total_notes": len(notes),
            "auto_captured": auto_count,
            "manual_notes": len(notes) - auto_count,
            "categories": categories,
            "recent_notes": notes[:5],
            "message": f"📅 {date}: {len(notes)} notes ({auto_count} auto)"
        }


def main():
    import sys
    
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No action specified"}))
        return
    
    action = sys.argv[1]
    memory = MemorySystem()
    
    if action == "capture":
        content = sys.argv[2] if len(sys.argv) > 2 else ""
        result = memory.auto_capture_note(content)
        
    elif action == "tag":
        entry_id = sys.argv[2] if len(sys.argv) > 2 else ""
        tags = sys.argv[3].split(",") if len(sys.argv) > 3 else []
        result = memory.tag_memory(entry_id, tags)
        
    elif action == "summarize":
        text = sys.argv[2] if len(sys.argv) > 2 else ""
        result = memory.summarize_conversation(text)
        
    elif action == "connect":
        entry_id = sys.argv[2] if len(sys.argv) > 2 else ""
        result = memory.find_connections(entry_id)
        
    elif action == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        result = memory.smart_search(query)
        
    elif action == "snapshot":
        name = sys.argv[2] if len(sys.argv) > 2 else "Unnamed"
        context = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        result = memory.save_context_snapshot(name, context)
        
    elif action == "snapshots":
        result = {"success": True, "snapshots": memory.list_context_snapshots()}
        
    elif action == "taskchain":
        name = sys.argv[2] if len(sys.argv) > 2 else "Task Chain"
        tasks = sys.argv[3].split(",") if len(sys.argv) > 3 else []
        result = memory.create_task_chain(name, tasks)
        
    elif action == "daily":
        date = sys.argv[2] if len(sys.argv) > 2 else None
        result = memory.get_daily_summary(date)
        
    else:
        result = {"error": f"Unknown action: {action}"}
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    import json
    main()
