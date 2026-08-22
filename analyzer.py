import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict, Counter

from database import get_db, upsert_entry
from config import TURKISH_STOPWORDS, NARRATIVE_CATEGORIES

def detect_coordinated_operations(days: int = 7, window_minutes: int = 120) -> List[Dict[str, Any]]:
    """
    Detects coordinated operations where 2 or more target authors posted on the
    same topic within a short time window (e.g. 120 minutes).
    Updates `is_coordinated` flag on entries and populates `coordinations` table.
    """
    cutoff = (datetime.now() - timedelta(days=days)).isoformat() if days > 0 else "1970-01-01"
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Reset current coordinations in window
        cursor.execute("DELETE FROM coordinations WHERE timestamp >= ?", (cutoff,))
        cursor.execute("UPDATE entries SET is_coordinated = 0 WHERE created_at >= ?", (cutoff,))
        conn.commit()

        # Fetch all entries in window grouped by topic
        cursor.execute("""
            SELECT id, author, topic, category, created_at, content
            FROM entries
            WHERE created_at >= ?
            ORDER BY topic, created_at ASC
        """, (cutoff,))
        rows = [dict(r) for r in cursor.fetchall()]

    # Group by topic
    topic_groups = defaultdict(list)
    for r in rows:
        topic_groups[r['topic']].append(r)

    detected_coordinations = []

    for topic, entries in topic_groups.items():
        if len(entries) < 2:
            continue

        # Check clusters within window_minutes
        clusters = []
        current_cluster = [entries[0]]

        for next_entry in entries[1:]:
            try:
                t1 = datetime.fromisoformat(current_cluster[-1]['created_at'])
                t2 = datetime.fromisoformat(next_entry['created_at'])
                diff_minutes = (t2 - t1).total_seconds() / 60.0
            except Exception:
                diff_minutes = 9999

            if diff_minutes <= window_minutes:
                current_cluster.append(next_entry)
            else:
                if len(current_cluster) >= 2:
                    clusters.append(current_cluster)
                current_cluster = [next_entry]

        if len(current_cluster) >= 2:
            clusters.append(current_cluster)

        # Process clusters
        for cluster in clusters:
            authors_in_cluster = list(set(e['author'] for e in cluster))
            if len(authors_in_cluster) >= 2: # At least 2 different authors
                entry_ids = [e['id'] for e in cluster]
                first_ts = cluster[0]['created_at']
                category = cluster[0]['category']

                coord_obj = {
                    "topic": topic,
                    "timestamp": first_ts,
                    "author_count": len(authors_in_cluster),
                    "authors_involved": json.dumps(authors_in_cluster),
                    "entry_ids": json.dumps(entry_ids),
                    "time_window_minutes": window_minutes,
                    "category": category
                }
                detected_coordinations.append(coord_obj)

                # Update in DB
                with get_db() as conn:
                    conn.execute("""
                        INSERT INTO coordinations (topic, timestamp, author_count, authors_involved, entry_ids, time_window_minutes, category)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        topic, first_ts, len(authors_in_cluster),
                        json.dumps(authors_in_cluster), json.dumps(entry_ids),
                        window_minutes, category
                    ))
                    # Mark entries as coordinated
                    placeholders = ','.join('?' for _ in entry_ids)
                    conn.execute(f"UPDATE entries SET is_coordinated = 1 WHERE id IN ({placeholders})", entry_ids)
                    conn.commit()

    return detected_coordinations

def get_coordination_network_data(days: int = 7) -> Dict[str, Any]:
    """Generates graph nodes (authors) and edges (shared coordinated topics)."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat() if days > 0 else "1970-01-01"
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM coordinations WHERE timestamp >= ?", (cutoff,))
        coordinations = [dict(r) for r in cursor.fetchall()]

        cursor.execute("""
            SELECT a.nick, COUNT(e.id) as total_entries,
                   SUM(CASE WHEN e.is_coordinated = 1 THEN 1 ELSE 0 END) as coord_entries
            FROM authors a
            LEFT JOIN entries e ON a.nick = e.author AND e.created_at >= ?
            GROUP BY a.nick
        """, (cutoff,))
        authors_stats = {r['nick']: dict(r) for r in cursor.fetchall()}

    # Pairwise co-occurrence
    pair_weights = defaultdict(int)
    pair_topics = defaultdict(list)

    for c in coordinations:
        try:
            auths = json.loads(c['authors_involved'])
        except Exception:
            auths = []
        for i in range(len(auths)):
            for j in range(i + 1, len(auths)):
                a1, a2 = sorted([auths[i], auths[j]])
                pair_weights[(a1, a2)] += 1
                if c['topic'] not in pair_topics[(a1, a2)]:
                    pair_topics[(a1, a2)].append(c['topic'])

    nodes = []
    for nick, stat in authors_stats.items():
        pe = stat['total_entries'] or 0
        ce = stat['coord_entries'] or 0
        if pe > 0 or ce > 0:
            nodes.append({
                "id": nick,
                "label": nick,
                "entries": pe,
                "coordinated": ce,
                "radius": max(8, min(24, 8 + (ce * 2)))
            })

    links = []
    for (source, target), weight in pair_weights.items():
        links.append({
            "source": source,
            "target": target,
            "weight": weight,
            "topics": pair_topics[(source, target)][:3]
        })

    return {"nodes": nodes, "links": links}

def get_posting_heatmap_data(days: int = 7) -> List[Dict[str, Any]]:
    """Calculates entry counts by Day of Week (0=Monday..6=Sunday) and Hour (0..23)."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat() if days > 0 else "1970-01-01"
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT created_at FROM entries WHERE created_at >= ?", (cutoff,))
        rows = cursor.fetchall()

    grid = [[0 for _ in range(24)] for _ in range(7)]
    
    for r in rows:
        try:
            dt = datetime.fromisoformat(r['created_at'])
            dow = dt.weekday() # 0 = Monday
            hour = dt.hour
            grid[dow][hour] += 1
        except Exception:
            pass

    day_names = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    formatted = []
    for d_idx, day_name in enumerate(day_names):
        for h in range(24):
            formatted.append({
                "day_index": d_idx,
                "day_name": day_name,
                "hour": h,
                "hour_label": f"{h:02d}:00",
                "count": grid[d_idx][h]
            })

    return formatted

def get_top_manipulation_narratives(days: int = 7) -> List[Dict[str, Any]]:
    """
    Groups top targeted manipulation topics and constructs detailed briefing cards.
    """
    cutoff = (datetime.now() - timedelta(days=days)).isoformat() if days > 0 else "1970-01-01"
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                topic,
                category,
                COUNT(*) as entry_count,
                COUNT(DISTINCT author) as author_count,
                SUM(CASE WHEN is_coordinated = 1 THEN 1 ELSE 0 END) as coord_count,
                MIN(created_at) as first_seen,
                MAX(created_at) as last_seen
            FROM entries
            WHERE created_at >= ?
            GROUP BY topic
            ORDER BY author_count DESC, coord_count DESC, entry_count DESC
            LIMIT 15
        """, (cutoff,))
        top_topics = [dict(r) for r in cursor.fetchall()]

        briefing = []
        for t in top_topics:
            # Fetch sample entries for this topic
            cursor.execute("""
                SELECT author, content, date_str, created_at, is_coordinated, id
                FROM entries
                WHERE topic = ? AND created_at >= ?
                ORDER BY created_at ASC
                LIMIT 5
            """, (t['topic'], cutoff))
            samples = [dict(s) for s in cursor.fetchall()]

            # Determine coordination level
            authors_involved = list(set(s['author'] for s in samples))
            is_high_coordination = t['author_count'] >= 3 or t['coord_count'] >= 2
            
            # Formulate narrative summary insight
            summary_desc = ""
            cat = t['category']
            if "Kültür Savaşı" in cat:
                summary_desc = f"Toplumsal kutuplaşma ve yaşam tarzı tartışması üzerinden {t['author_count']} hesap tarafından eşzamanlı gündeme taşındı."
            elif "Ekonomi" in cat:
                summary_desc = f"Pahalılık/turist/esnaf algısını çarpıtma ve ekonomik tepkileri hafifletme amacıyla {t['author_count']} hesap tarafından organize paylaşıldı."
            elif "Muhalefet" in cat:
                summary_desc = f"Muhalefet partileri ve belediyeleri hedef alan organize dezenformasyon/eleştiri dalgası."
            elif "Yargı" in cat:
                summary_desc = f"Yargı ve güvenlik süreçlerini meşrulaştırma veya karşıt figürleri itibarsızlaştırma operasyonu."
            else:
                summary_desc = f"Gündem değiştirme ve dikkat dağıtma amaçlı viral içerik pompalaması."

            briefing.append({
                "topic": t['topic'],
                "category": t['category'],
                "entry_count": t['entry_count'],
                "author_count": t['author_count'],
                "coord_count": t['coord_count'],
                "is_coordinated": is_high_coordination,
                "first_seen": t['first_seen'],
                "last_seen": t['last_seen'],
                "summary": summary_desc,
                "authors": authors_involved,
                "sample_entries": samples
            })

    return briefing

def extract_top_keywords(days: int = 7, top_n: int = 30) -> List[Dict[str, Any]]:
    """Extracts top words and 2-grams across all entries excluding Turkish stopwords."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat() if days > 0 else "1970-01-01"
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT topic, content FROM entries WHERE created_at >= ?", (cutoff,))
        rows = cursor.fetchall()

    word_counts = Counter()
    for r in rows:
        text = f"{r['topic']} {r['content']}".lower()
        import re
        words = re.findall(r'[a-zA-ZçğıöşüÇĞİÖŞÜ]{3,}', text)
        for w in words:
            if w not in TURKISH_STOPWORDS:
                word_counts[w] += 1

    return [{"word": word, "count": count} for word, count in word_counts.most_common(top_n)]
