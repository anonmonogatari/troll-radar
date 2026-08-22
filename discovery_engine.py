import math
import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter, defaultdict

from config import TARGET_AUTHORS, NARRATIVE_CATEGORIES, TURKISH_STOPWORDS
from database import get_db

class TrollDiscoveryEngine:
    """
    Automated Inauthentic Behavior & Troll Cell Detection Engine.
    Evaluates accounts across 5 mathematical and behavioral dimensions:
    1. Topic Entropy (Shannon Entropy)
    2. Temporal Co-posting Synchronicity
    3. Political / Propaganda Focus Ratio
    4. Work-Shift Regularity (Posting schedule footprint)
    5. Semantic & External Link Bias
    """

    def __init__(self):
        self.propaganda_keywords = set()
        for cat, data in NARRATIVE_CATEGORIES.items():
            for kw in data["keywords"]:
                self.propaganda_keywords.add(kw.lower())

    def calculate_topic_entropy(self, topics: List[str]) -> float:
        """
        Calculates Shannon Entropy of an author's topic distribution:
        H(X) = - sum(p(x) * log2(p(x)))
        Normal users: high entropy (> 3.0), diverse interests.
        Troll accounts: very low entropy (< 1.5), focused on targeted topics.
        """
        if not topics:
            return 0.0
        
        total = len(topics)
        counts = Counter(topics)
        entropy = 0.0
        
        for count in counts.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)
                
        return round(entropy, 2)

    def calculate_political_focus_ratio(self, topics: List[str], contents: List[str]) -> float:
        """
        Calculates the ratio of entries that match political / polarization / propaganda keywords.
        """
        if not topics:
            return 0.0

        total = len(topics)
        political_count = 0

        for topic, content in zip(topics, contents):
            full_text = f"{topic.lower()} {content.lower()}"
            if any(kw in full_text for kw in self.propaganda_keywords):
                political_count += 1

        return round((political_count / total) * 100, 1)

    def calculate_shift_regularity(self, timestamps: List[str]) -> float:
        """
        Calculates the concentration of postings within standard work/shift hours (09:00 - 18:00 on weekdays).
        Organic users post organically around the clock, while troll teams often follow shift schedules.
        """
        if not timestamps:
            return 0.0

        work_shift_posts = 0
        total_valid = 0

        for ts in timestamps:
            try:
                dt = datetime.fromisoformat(ts)
                total_valid += 1
                # Weekdays (0=Mon .. 4=Fri) and 09:00 - 18:00
                if dt.weekday() < 5 and (9 <= dt.hour <= 18):
                    work_shift_posts += 1
            except Exception:
                pass

        if total_valid == 0:
            return 0.0

        return round((work_shift_posts / total_valid) * 100, 1)

    def calculate_temporal_synchronicity(self, author_entries: List[Dict[str, Any]], all_entries: List[Dict[str, Any]], window_minutes: int = 45) -> float:
        """
        Calculates how frequently this author posts on the exact same topic
        within 'window_minutes' of other suspected/target authors.
        """
        if not author_entries:
            return 0.0

        author_entry_ids = set(e['id'] for e in author_entries)
        other_entries = [e for e in all_entries if e['id'] not in author_entry_ids]

        # Group other entries by topic
        other_by_topic = defaultdict(list)
        for e in other_entries:
            try:
                other_by_topic[e['topic']].append(datetime.fromisoformat(e['created_at']))
            except Exception:
                pass

        synchronized_posts = 0
        for e in author_entries:
            topic = e['topic']
            if topic not in other_by_topic:
                continue
            try:
                author_dt = datetime.fromisoformat(e['created_at'])
                for other_dt in other_by_topic[topic]:
                    diff_mins = abs((author_dt - other_dt).total_seconds()) / 60.0
                    if diff_mins <= window_minutes:
                        synchronized_posts += 1
                        break
            except Exception:
                pass

        return round((synchronized_posts / len(author_entries)) * 100, 1)

    def calculate_link_bias(self, external_links_list: List[List[Dict[str, str]]]) -> float:
        """
        Measures reliance on specific video/news links commonly pushed by troll rings.
        """
        total_links = 0
        biased_links = 0
        for links in external_links_list:
            if not links:
                continue
            for l in links:
                url = l.get('url', '').lower() if isinstance(l, dict) else str(l).lower()
                total_links += 1
                if any(domain in url for domain in ['turkinform', 'ensonhaber', 'yeniakit', 'sabah', 'ahaber', 'twitter.com', 'x.com']):
                    biased_links += 1

        if total_links == 0:
            return 0.0
        return round((biased_links / total_links) * 100, 1)

    def evaluate_author(self, nick: str, author_entries: List[Dict[str, Any]], all_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluates a candidate author and returns composite Troll Score (0-100) and feature vector.
        """
        topics = [e['topic'] for e in author_entries]
        contents = [e['content'] for e in author_entries]
        timestamps = [e['created_at'] for e in author_entries]
        links = [e.get('external_links', []) for e in author_entries]

        entropy = self.calculate_topic_entropy(topics)
        political_ratio = self.calculate_political_focus_ratio(topics, contents)
        shift_regularity = self.calculate_shift_regularity(timestamps)
        synchronicity = self.calculate_temporal_synchronicity(author_entries, all_entries)
        link_bias = self.calculate_link_bias(links)

        # Inverted entropy score: lower entropy -> higher troll probability
        # Normal user: entropy ~ 3.5 -> score = 0
        # Troll: entropy ~ 0.5 -> score = 100
        entropy_troll_score = max(0.0, min(100.0, (3.5 - entropy) * 33.3)) if len(topics) >= 3 else 50.0

        # Weighted Ensemble Troll Index (0 - 100)
        # Weights:
        # - Synchronicity (Eşzamanlılık): 30%
        # - Topic Narrowness / Entropy (Konu Darlığı): 25%
        # - Political Focus (Siyasi Odak): 20%
        # - Shift Regularity (Mesai Düzeni): 15%
        # - Link Bias (Link Tercihi): 10%
        raw_score = (
            (synchronicity * 0.30) +
            (entropy_troll_score * 0.25) +
            (political_ratio * 0.20) +
            (shift_regularity * 0.15) +
            (link_bias * 0.10)
        )
        troll_score = round(max(0.0, min(100.0, raw_score)), 1)

        # Determine risk classification
        if troll_score >= 80:
            risk_level = "Kesin Troll Hücresi"
            badge_color = "red"
        elif troll_score >= 60:
            risk_level = "Yüksek Olasılıklı Troll"
            badge_color = "orange"
        elif troll_score >= 40:
            risk_level = "Şüpheli / Polarize Hesap"
            badge_color = "yellow"
        else:
            risk_level = "Organik / Düşük Risk"
            badge_color = "green"

        # Detect cell / specialty group
        cell_tags = []
        top_cats = Counter([e.get('category', 'Genel') for e in author_entries]).most_common(2)
        if top_cats:
            for cat, cnt in top_cats:
                if cat != "Genel" and cat != "Suni Gündem & Viral Çarpıtma":
                    cell_tags.append(cat)
        detected_cell = cell_tags[0] if cell_tags else "Genel Algı Hücresi"

        return {
            "nick": nick,
            "troll_score": troll_score,
            "risk_level": risk_level,
            "badge_color": badge_color,
            "detected_cell": detected_cell,
            "entry_count": len(author_entries),
            "metrics": {
                "topic_entropy": entropy,
                "topic_entropy_score": round(entropy_troll_score, 1),
                "synchronicity_score": synchronicity,
                "political_ratio": political_ratio,
                "shift_regularity": shift_regularity,
                "link_bias": link_bias
            },
            "evidence_topics": list(set(topics))[:4]
        }

    def run_auto_discovery_scan(self, days: int = 30, scrape_live: bool = False) -> List[Dict[str, Any]]:
        """
        Scans authors, evaluates their metrics, optionally scrapes current Gündem/Debe,
        and saves discovered troll classifications into SQLite.
        """
        if scrape_live:
            try:
                from scraper import EksiScraper
                scraper = EksiScraper()
                scraper.scrape_gundem_and_top_entries(limit_topics=10, max_entries_per_topic=10)
            except Exception as e:
                print(f"Live gündem scrape warning: {e}")

        cutoff = (datetime.now() - timedelta(days=days)).isoformat() if days > 0 else "1970-01-01"
        
        with get_db() as conn:
            cursor = conn.cursor()
            # Fetch active monitored authors
            active_rows = cursor.execute("SELECT nick FROM authors WHERE is_active = 1").fetchall()
            active_monitored_set = set(r['nick'] for r in active_rows)

            cursor.execute("SELECT * FROM entries WHERE created_at >= ?", (cutoff,))
            all_entries = [dict(r) for r in cursor.fetchall()]
            for e in all_entries:
                try:
                    if isinstance(e.get('external_links'), str):
                        e['external_links'] = json.loads(e.get('external_links') or '[]')
                except Exception:
                    e['external_links'] = []

        # Group entries by author
        entries_by_author = defaultdict(list)
        for e in all_entries:
            entries_by_author[e['author']].append(e)

        results = []
        for nick, author_entries in entries_by_author.items():
            evaluation = self.evaluate_author(nick, author_entries, all_entries)
            is_monitored = nick in active_monitored_set
            evaluation['is_monitored'] = is_monitored
            results.append(evaluation)

            # Persist evaluation to database
            with get_db() as conn:
                conn.execute("""
                    INSERT INTO discovered_trolls (
                        nick, troll_score, risk_level, detected_cell,
                        topic_entropy, synchronicity_score, political_ratio,
                        shift_regularity, link_bias, entry_count, evidence_topics,
                        discovered_at, is_monitored
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(nick) DO UPDATE SET
                        troll_score=excluded.troll_score,
                        risk_level=excluded.risk_level,
                        detected_cell=excluded.detected_cell,
                        topic_entropy=excluded.topic_entropy,
                        synchronicity_score=excluded.synchronicity_score,
                        political_ratio=excluded.political_ratio,
                        shift_regularity=excluded.shift_regularity,
                        link_bias=excluded.link_bias,
                        entry_count=excluded.entry_count,
                        evidence_topics=excluded.evidence_topics,
                        discovered_at=excluded.discovered_at,
                        is_monitored=excluded.is_monitored
                """, (
                    nick,
                    evaluation['troll_score'],
                    evaluation['risk_level'],
                    evaluation['detected_cell'],
                    evaluation['metrics']['topic_entropy'],
                    evaluation['metrics']['synchronicity_score'],
                    evaluation['metrics']['political_ratio'],
                    evaluation['metrics']['shift_regularity'],
                    evaluation['metrics']['link_bias'],
                    evaluation['entry_count'],
                    json.dumps(evaluation['evidence_topics'], ensure_ascii=False),
                    datetime.now().isoformat(),
                    1 if is_monitored else 0
                ))
                conn.commit()

        # Sort by troll score descending
        results.sort(key=lambda x: x['troll_score'], reverse=True)
        return results

    def cluster_troll_cells(self, evaluations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Groups discovered trolls into coordinated operational cells.
        """
        cells = defaultdict(list)
        for ev in evaluations:
            if ev['troll_score'] >= 50:
                cell_name = ev['detected_cell']
                cells[cell_name].append(ev)

        cell_clusters = []
        for cell_name, members in cells.items():
            avg_score = round(sum(m['troll_score'] for m in members) / len(members), 1)
            cell_clusters.append({
                "cell_name": cell_name,
                "member_count": len(members),
                "average_troll_score": avg_score,
                "members": [m['nick'] for m in members],
                "top_evidence_topics": list(set([t for m in members for t in m['evidence_topics']]))[:5]
            })

        cell_clusters.sort(key=lambda x: x['member_count'], reverse=True)
        return cell_clusters
