import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from config import DB_PATH, TARGET_AUTHORS, DATA_DIR

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes SQLite database schemas and indices."""
    DATA_DIR.mkdir(exist_ok=True)
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Authors Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS authors (
                nick TEXT PRIMARY KEY,
                display_name TEXT,
                total_entries INTEGER DEFAULT 0,
                last_scraped_at TEXT,
                last_entry_at TEXT,
                risk_score REAL DEFAULT 0.0,
                is_active INTEGER DEFAULT 1,
                notes TEXT DEFAULT ''
            )
        """)
        
        # Entries Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id TEXT PRIMARY KEY,
                author TEXT NOT NULL,
                topic TEXT NOT NULL,
                topic_slug TEXT,
                content TEXT NOT NULL,
                date_str TEXT,
                created_at TEXT NOT NULL,
                favorite_count INTEGER DEFAULT 0,
                comment_count INTEGER DEFAULT 0,
                category TEXT DEFAULT 'Genel',
                sentiment TEXT DEFAULT 'neutral',
                external_links TEXT DEFAULT '[]',
                is_coordinated INTEGER DEFAULT 0,
                FOREIGN KEY (author) REFERENCES authors(nick)
            )
        """)
        
        # Coordinated Operations Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS coordinations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                author_count INTEGER NOT NULL,
                authors_involved TEXT NOT NULL,
                entry_ids TEXT NOT NULL,
                time_window_minutes INTEGER DEFAULT 60,
                category TEXT DEFAULT 'Genel'
            )
        """)

        # Scrape Logs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scrape_jobs (
                id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                total_authors INTEGER DEFAULT 0,
                authors_processed INTEGER DEFAULT 0,
                entries_found INTEGER DEFAULT 0,
                logs TEXT DEFAULT '[]'
            )
        """)
        
        # Indices for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entries_author ON entries(author)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entries_created_at ON entries(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entries_topic ON entries(topic)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entries_category ON entries(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entries_coordinated ON entries(is_coordinated)")

        # Ensure all 27 target authors are registered in authors table
        for nick in TARGET_AUTHORS:
            cursor.execute("""
                INSERT OR IGNORE INTO authors (nick, display_name, is_active)
                VALUES (?, ?, 1)
            """, (nick, nick))
            
        conn.commit()

def upsert_entry(entry_data: Dict[str, Any]) -> bool:
    """Inserts or updates an entry and updates author stats."""
    with get_db() as conn:
        cursor = conn.cursor()
        ext_links = json.dumps(entry_data.get('external_links', [])) if isinstance(entry_data.get('external_links'), list) else entry_data.get('external_links', '[]')
        
        cursor.execute("""
            INSERT INTO entries (
                id, author, topic, topic_slug, content, date_str, created_at,
                favorite_count, comment_count, category, sentiment, external_links, is_coordinated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                author=excluded.author,
                topic=excluded.topic,
                topic_slug=excluded.topic_slug,
                content=excluded.content,
                date_str=excluded.date_str,
                created_at=excluded.created_at,
                favorite_count=excluded.favorite_count,
                comment_count=excluded.comment_count,
                category=excluded.category,
                sentiment=excluded.sentiment,
                external_links=excluded.external_links,
                is_coordinated=excluded.is_coordinated
        """, (
            str(entry_data['id']),
            entry_data['author'],
            entry_data['topic'],
            entry_data.get('topic_slug', ''),
            entry_data['content'],
            entry_data.get('date_str', ''),
            entry_data['created_at'],
            entry_data.get('favorite_count', 0),
            entry_data.get('comment_count', 0),
            entry_data.get('category', 'Genel'),
            entry_data.get('sentiment', 'neutral'),
            ext_links,
            1 if entry_data.get('is_coordinated') else 0
        ))
        
        # Update author metadata
        cursor.execute("""
            UPDATE authors
            SET total_entries = (SELECT COUNT(*) FROM entries WHERE author = ?),
                last_entry_at = MAX(COALESCE(last_entry_at, ''), ?)
            WHERE nick = ?
        """, (entry_data['author'], entry_data['created_at'], entry_data['author']))
        
        conn.commit()
        return True

def get_entries(
    days: int = 7,
    author: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    coordinated_only: bool = False,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """Retrieves paginated and filtered entries."""
    query = "SELECT * FROM entries WHERE 1=1"
    params = []

    if days > 0:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        query += " AND created_at >= ?"
        params.append(cutoff)

    if author:
        query += " AND author = ?"
        params.append(author)

    if category and category != "Tümü":
        query += " AND category = ?"
        params.append(category)

    if search:
        query += " AND (topic LIKE ? OR content LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term])

    if coordinated_only:
        query += " AND is_coordinated = 1"

    # Count query
    count_query = query.replace("SELECT *", "SELECT COUNT(*)")
    with get_db() as conn:
        cursor = conn.cursor()
        total = cursor.execute(count_query, params).fetchone()[0]

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = cursor.execute(query, params).fetchall()
        entries = [dict(r) for r in rows]
        for e in entries:
            try:
                e['external_links'] = json.loads(e.get('external_links', '[]'))
            except Exception:
                e['external_links'] = []

    return {"total": total, "entries": entries, "limit": limit, "offset": offset}

def get_all_authors_summary(days: int = 7) -> List[Dict[str, Any]]:
    """Gets all 27 target authors with recent metrics and risk scoring."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat() if days > 0 else "1970-01-01"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                a.nick,
                a.display_name,
                a.last_scraped_at,
                a.last_entry_at,
                a.is_active,
                COUNT(e.id) as period_entries,
                SUM(CASE WHEN e.is_coordinated = 1 THEN 1 ELSE 0 END) as coordinated_entries,
                COUNT(DISTINCT e.topic) as distinct_topics
            FROM authors a
            LEFT JOIN entries e ON a.nick = e.author AND e.created_at >= ?
            GROUP BY a.nick
            ORDER BY period_entries DESC, a.nick ASC
        """, (cutoff,))
        rows = cursor.execute("""
            SELECT 
                a.nick,
                a.display_name,
                a.last_scraped_at,
                a.last_entry_at,
                a.is_active,
                COUNT(e.id) as period_entries,
                SUM(CASE WHEN e.is_coordinated = 1 THEN 1 ELSE 0 END) as coordinated_entries,
                COUNT(DISTINCT e.topic) as distinct_topics
            FROM authors a
            LEFT JOIN entries e ON a.nick = e.author AND e.created_at >= ?
            GROUP BY a.nick
            ORDER BY period_entries DESC, a.nick ASC
        """, (cutoff,)).fetchall()
        
        result = []
        for r in rows:
            d = dict(r)
            pe = d['period_entries'] or 0
            ce = d['coordinated_entries'] or 0
            # Calculate dynamic risk score (0 to 100)
            risk = 0.0
            if pe > 0:
                risk = min(100.0, (pe * 4.0) + (ce * 15.0))
            d['risk_score'] = round(risk, 1)
            
            # Fetch top 3 topics for this author in period
            top_topics = cursor.execute("""
                SELECT topic, COUNT(*) as cnt
                FROM entries
                WHERE author = ? AND created_at >= ?
                GROUP BY topic
                ORDER BY cnt DESC
                LIMIT 3
            """, (d['nick'], cutoff)).fetchall()
            d['top_topics'] = [t['topic'] for t in top_topics]
            result.append(d)
            
        return result

def get_overview_stats(days: int = 7) -> Dict[str, Any]:
    """Overview statistics for dashboard KPI cards."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat() if days > 0 else "1970-01-01"
    with get_db() as conn:
        cursor = conn.cursor()
        
        total_entries = cursor.execute("SELECT COUNT(*) FROM entries WHERE created_at >= ?", (cutoff,)).fetchone()[0]
        total_coordinated = cursor.execute("SELECT COUNT(*) FROM entries WHERE created_at >= ? AND is_coordinated = 1", (cutoff,)).fetchone()[0]
        active_authors = cursor.execute("SELECT COUNT(DISTINCT author) FROM entries WHERE created_at >= ?", (cutoff,)).fetchone()[0]
        total_topics = cursor.execute("SELECT COUNT(DISTINCT topic) FROM entries WHERE created_at >= ?", (cutoff,)).fetchone()[0]
        total_operations = cursor.execute("SELECT COUNT(*) FROM coordinations WHERE timestamp >= ?", (cutoff,)).fetchone()[0]
        
        # Category breakdown
        cat_rows = cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM entries
            WHERE created_at >= ?
            GROUP BY category
            ORDER BY count DESC
        """, (cutoff,)).fetchall()
        categories = {r['category']: r['count'] for r in cat_rows}

        # Daily timeline
        timeline_rows = cursor.execute("""
            SELECT substr(created_at, 1, 10) as day, 
                   COUNT(*) as total,
                   SUM(CASE WHEN is_coordinated = 1 THEN 1 ELSE 0 END) as coordinated
            FROM entries
            WHERE created_at >= ?
            GROUP BY day
            ORDER BY day ASC
        """, (cutoff,)).fetchall()
        timeline = [dict(r) for r in timeline_rows]

    return {
        "period_days": days,
        "total_entries": total_entries,
        "coordinated_entries": total_coordinated,
        "active_authors": active_authors,
        "total_monitored_authors": len(TARGET_AUTHORS),
        "total_topics": total_topics,
        "total_operations": total_operations,
        "categories": categories,
        "timeline": timeline
    }
