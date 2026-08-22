import math
import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter, defaultdict

from config import TARGET_AUTHORS, NARRATIVE_CATEGORIES, TURKISH_STOPWORDS
from database import get_db
from noise_filter import is_noise_topic
from smear_detector import (
    detect_entry_stance, calculate_smear_intensity_ratio,
    calculate_narrative_alignment, calculate_vote_brigading_score
)

class TrollDiscoveryEngine:
    """
    Refined Targeted Political Astroturfing, Smear Campaign,
    Vote-Brigading, and Stance Alignment Detection Engine.
    Filters out football/sports/entertainment noise completely.
    """

    def __init__(self):
        pass

    def calculate_topic_entropy(self, topics: List[str]) -> float:
        """
        Calculates Shannon Entropy of an author's topic distribution:
        H(X) = - sum(p(x) * log2(p(x)))
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

    def calculate_shift_regularity(self, timestamps: List[str]) -> float:
        """
        Calculates the concentration of postings within standard work/shift hours (09:00 - 18:00 on weekdays).
        """
        if not timestamps:
            return 0.0

        work_shift_posts = 0
        total_valid = 0

        for ts in timestamps:
            try:
                dt = datetime.fromisoformat(ts)
                total_valid += 1
                if dt.weekday() < 5 and (9 <= dt.hour <= 18):
                    work_shift_posts += 1
            except Exception:
                pass

        if total_valid == 0:
            return 0.0

        return round((work_shift_posts / total_valid) * 100, 1)

    def calculate_temporal_synchronicity(self, author_entries: List[Dict[str, Any]], all_entries: List[Dict[str, Any]], window_minutes: int = 45) -> float:
        """
        Calculates how frequently this author posts on the exact same political topic
        within 'window_minutes' of other suspected/target authors.
        """
        if not author_entries:
            return 0.0

        author_entry_ids = set(e['id'] for e in author_entries)
        other_entries = [e for e in all_entries if e['id'] not in author_entry_ids and not is_noise_topic(e['topic'])]

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

    def evaluate_author(self, nick: str, author_entries: List[Dict[str, Any]], all_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluates an author across targeted political astroturfing criteria:
        1. Stance & Narrative Alignment (Aynı Tez & Söylem Birliği): 30%
        2. Smear & Defamation Intensity (İftira/Karalama/Aklama Odaklılığı): 25%
        3. Vote Brigading / Favoriting Ring (Organize Beğeni & Şükela Halkası): 20%
        4. Temporal Synchronicity (Zamansal Eşzamanlılık): 15%
        5. Topic Narrowness / Entropy (Konu Darlığı / Entropi): 10%
        """
        # Filter out noise entries for this author
        relevant_entries = [e for e in author_entries if not is_noise_topic(e['topic'], e.get('content'))]
        
        # If author ONLY posts about football/sports/casual noise -> NOT a political troll!
        if not relevant_entries:
            return {
                "nick": nick,
                "troll_score": 0.0,
                "risk_level": "Organik / Spor-Genel Yazar",
                "badge_color": "green",
                "detected_cell": "Gürültü / Spor İçeriği (Elendi)",
                "entry_count": len(author_entries),
                "is_monitored": False,
                "metrics": {
                    "topic_entropy": 0.0,
                    "stance_alignment": 0.0,
                    "smear_intensity": 0.0,
                    "vote_brigading": 0.0,
                    "synchronicity_score": 0.0,
                    "shift_regularity": 0.0
                },
                "evidence_topics": []
            }

        topics = [e['topic'] for e in relevant_entries]
        timestamps = [e['created_at'] for e in relevant_entries]

        # 1. Calculate Core Metrics
        entropy = self.calculate_topic_entropy(topics)
        entropy_troll_score = max(0.0, min(100.0, (3.2 - entropy) * 35.0)) if len(topics) >= 2 else 50.0

        stance_alignment = calculate_narrative_alignment(relevant_entries, all_entries)
        smear_intensity = calculate_smear_intensity_ratio(relevant_entries)
        vote_brigading = calculate_vote_brigading_score(relevant_entries)
        synchronicity = self.calculate_temporal_synchronicity(relevant_entries, all_entries)
        shift_regularity = self.calculate_shift_regularity(timestamps)

        # -------------------------------------------------------------
        # MANDATORY HARD-GATE: VOTE BRIGADING / FAVORITING RING
        # -------------------------------------------------------------
        # An organized troll network CANNOT operate without an upvote/fav ring to push
        # smear entries into Debe/Şükela. If no vote-brigading ring exists, immediately disqualify!
        if vote_brigading < 30.0:
            return {
                "nick": nick,
                "troll_score": 0.0,
                "risk_level": "Organik / Beğeni Halkası Yok",
                "badge_color": "green",
                "detected_cell": "Bireysel (Beğeni Halkası Yok - Elendi)",
                "entry_count": len(relevant_entries),
                "is_monitored": False,
                "metrics": {
                    "topic_entropy": entropy,
                    "stance_alignment": stance_alignment,
                    "smear_intensity": smear_intensity,
                    "vote_brigading": vote_brigading,
                    "synchronicity_score": synchronicity,
                    "shift_regularity": shift_regularity
                },
                "evidence_topics": []
            }

        # 2. Weighted Political Astroturfing Troll Index (0 - 100)
        raw_score = (
            (stance_alignment * 0.30) +
            (smear_intensity * 0.25) +
            (vote_brigading * 0.20) +
            (synchronicity * 0.15) +
            (entropy_troll_score * 0.10)
        )
        troll_score = round(max(0.0, min(100.0, raw_score)), 1)

        # 3. Determine Risk Classification
        if troll_score >= 75:
            risk_level = "Kesin Organize Troll"
            badge_color = "red"
        elif troll_score >= 55:
            risk_level = "Yüksek Olasılıklı Troll"
            badge_color = "orange"
        elif troll_score >= 35:
            risk_level = "Şüpheli / Polarize Hesap"
            badge_color = "yellow"
        else:
            risk_level = "Organik / Düşük Risk"
            badge_color = "green"

        # 4. Cell Categorization
        cell_tags = []
        top_cats = Counter([e.get('category', 'Genel') for e in relevant_entries]).most_common(2)
        if top_cats:
            for cat, cnt in top_cats:
                if cat != "Genel" and cat != "Suni Gündem & Viral Çarpıtma":
                    cell_tags.append(cat)
        detected_cell = cell_tags[0] if cell_tags else "Genel Karalama & Algı Hücresi"

        return {
            "nick": nick,
            "troll_score": troll_score,
            "risk_level": risk_level,
            "badge_color": badge_color,
            "detected_cell": detected_cell,
            "entry_count": len(relevant_entries),
            "metrics": {
                "topic_entropy": entropy,
                "stance_alignment": stance_alignment,
                "smear_intensity": smear_intensity,
                "vote_brigading": vote_brigading,
                "synchronicity_score": synchronicity,
                "shift_regularity": shift_regularity
            },
            "evidence_topics": list(set(topics))[:4]
        }

    def run_auto_discovery_scan(self, days: int = 30, scrape_live: bool = False) -> List[Dict[str, Any]]:
        """
        Scans authors, evaluates their metrics against political manipulation criteria,
        and saves discovered troll classifications into SQLite.
        """
        if scrape_live:
            try:
                from scraper import EksiScraper
                scraper = EksiScraper()
                scraper.scrape_gundem_and_top_entries(limit_topics=15, max_entries_per_topic=10)
            except Exception as e:
                print(f"Live gündem scrape warning: {e}")

        cutoff = (datetime.now() - timedelta(days=days)).isoformat() if days > 0 else "1970-01-01"
        
        with get_db() as conn:
            cursor = conn.cursor()
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
            
            # If author has score 0 because they only post sports/noise, omit or rank at bottom
            is_monitored = nick in active_monitored_set
            evaluation['is_monitored'] = is_monitored
            
            if evaluation['troll_score'] > 0 or is_monitored:
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
                    evaluation['metrics']['smear_intensity'],
                    evaluation['metrics']['shift_regularity'],
                    evaluation['metrics']['vote_brigading'],
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
        Groups discovered political trolls into coordinated operational cells.
        """
        cells = defaultdict(list)
        for ev in evaluations:
            if ev['troll_score'] >= 45 and "Gürültü" not in ev['detected_cell']:
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
