import math
import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter, defaultdict

from config import TARGET_AUTHORS, NARRATIVE_CATEGORIES, TURKISH_STOPWORDS
from database import get_db
from noise_filter import is_noise_topic
from smear_detector import detect_entry_stance, calculate_narrative_alignment, calculate_vote_brigading_score
from manufactured_topic_detector import is_manufactured_troll_topic, is_generic_established_topic

class TrollDiscoveryEngine:
    """
    High-Precision Troll Inception & Early Swarm Detection Engine.
    Exclusively targets accounts that manufacture new smear/outrage topics
    and the early swarm crew (#1-#5 entries) that coordinates to push them into Sol Frame/Debe.
    """

    def __init__(self):
        pass

    def evaluate_author_on_manufactured_topics(
        self,
        nick: str,
        author_entries: List[Dict[str, Any]],
        all_entries: List[Dict[str, Any]],
        topic_timeline_map: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Evaluates an author on manufactured topic creation, early swarming, and brigading:
        1. Topic Inception (Kurgu Başlık Açma - Entry #1): 40%
        2. Early Swarm (#1-#5 Entry İle Köpürtme): 35%
        3. First-Wave Favoriting Ring (Beğeni Halkası): 15%
        4. Stance & Defamation Alignment (Söylem Uyumu): 10%
        """
        # Filter out noise entries for this author
        relevant_entries = [e for e in author_entries if not is_noise_topic(e['topic'], e.get('content'))]
        
        if not relevant_entries:
            return {
                "nick": nick,
                "troll_score": 0.0,
                "risk_level": "Organik / Gürültü-Spor İçeriği",
                "badge_color": "green",
                "detected_cell": "Gürültü / Spor İçeriği (Elendi)",
                "entry_count": len(author_entries),
                "is_monitored": False,
                "metrics": {
                    "inception_count": 0,
                    "early_swarm_count": 0,
                    "manufactured_focus_ratio": 0.0,
                    "vote_brigading": 0.0,
                    "stance_alignment": 0.0
                },
                "evidence_topics": []
            }

        # Analyze positions on manufactured topics
        inception_count = 0
        early_swarm_count = 0
        manufactured_topics_participated = []
        cell_tags = []

        for e in relevant_entries:
            topic = e['topic']
            is_manuf, cell_type = is_manufactured_troll_topic(topic, e.get('content', ''))
            
            if not is_manuf:
                continue

            manufactured_topics_participated.append(topic)
            cell_tags.append(cell_type)

            # Check entry rank/position in this topic
            topic_entries = topic_timeline_map.get(topic, [])
            # Find index of this entry in the sorted topic entries
            try:
                entry_index = next(idx for idx, te in enumerate(topic_entries) if te['id'] == e['id'])
            except StopIteration:
                entry_index = 0

            # If it's Entry #1 (Topic Starter)
            if entry_index == 0:
                inception_count += 1
                early_swarm_count += 1
            # If it's Entry #2 - #5 (Early Swarm)
            elif entry_index < 5:
                early_swarm_count += 1

        # -------------------------------------------------------------
        # MANDATORY HARD-GATE: MANUFACTURED TOPIC ENGAGEMENT
        # -------------------------------------------------------------
        # If an author NEVER opened a manufactured topic and NEVER participated in the
        # first 5 entries of a smear topic, they are an ORGANIC user (Score = 0.0)!
        if early_swarm_count == 0:
            return {
                "nick": nick,
                "troll_score": 0.0,
                "risk_level": "Organik / Kurgu Başlık Katılımı Yok",
                "badge_color": "green",
                "detected_cell": "Organik Yazar (Kurgu Başlık Yok - Elendi)",
                "entry_count": len(relevant_entries),
                "is_monitored": False,
                "metrics": {
                    "inception_count": 0,
                    "early_swarm_count": 0,
                    "manufactured_focus_ratio": 0.0,
                    "vote_brigading": 0.0,
                    "stance_alignment": 0.0
                },
                "evidence_topics": []
            }

        # Calculate Ratios
        total_relevant = len(relevant_entries)
        inception_ratio = round((inception_count / max(1, total_relevant)) * 100, 1)
        early_swarm_ratio = round((early_swarm_count / max(1, total_relevant)) * 100, 1)
        manufactured_focus_ratio = round((len(manufactured_topics_participated) / max(1, total_relevant)) * 100, 1)

        vote_brigading = calculate_vote_brigading_score(relevant_entries)
        stance_alignment = calculate_narrative_alignment(relevant_entries, all_entries)

        # -------------------------------------------------------------
        # MANDATORY HARD-GATE: VOTE BRIGADING
        # -------------------------------------------------------------
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
                    "inception_count": inception_count,
                    "early_swarm_count": early_swarm_count,
                    "manufactured_focus_ratio": manufactured_focus_ratio,
                    "vote_brigading": vote_brigading,
                    "stance_alignment": stance_alignment
                },
                "evidence_topics": []
            }

        # Weighted Troll Index
        raw_score = (
            (inception_ratio * 0.40) +
            (early_swarm_ratio * 0.35) +
            (vote_brigading * 0.15) +
            (stance_alignment * 0.10)
        )
        troll_score = round(max(0.0, min(100.0, raw_score)), 1)

        # Risk Classification
        if troll_score >= 70:
            risk_level = "Kesin Kurgu Başlık Trollü"
            badge_color = "red"
        elif troll_score >= 50:
            risk_level = "İlk Dalga Köpürtücü Troll"
            badge_color = "orange"
        elif troll_score >= 30:
            risk_level = "Şüpheli Algı Katılımcısı"
            badge_color = "yellow"
        else:
            risk_level = "Düşük Risk / Organik"
            badge_color = "green"

        top_cell = Counter(cell_tags).most_common(1)[0][0] if cell_tags else "Genel Karalama Hücresi"

        return {
            "nick": nick,
            "troll_score": troll_score,
            "risk_level": risk_level,
            "badge_color": badge_color,
            "detected_cell": top_cell,
            "entry_count": len(relevant_entries),
            "metrics": {
                "inception_count": inception_count,
                "early_swarm_count": early_swarm_count,
                "manufactured_focus_ratio": early_swarm_ratio,
                "vote_brigading": vote_brigading,
                "stance_alignment": stance_alignment
            },
            "evidence_topics": list(set(manufactured_topics_participated))[:4]
        }

    def run_auto_discovery_scan(self, days: int = 30, scrape_live: bool = False) -> List[Dict[str, Any]]:
        """
        Scans authors, evaluates them exclusively on newly created manufactured topics and early swarms,
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

            cursor.execute("SELECT * FROM entries WHERE created_at >= ? ORDER BY created_at ASC", (cutoff,))
            all_entries = [dict(r) for r in cursor.fetchall()]
            for e in all_entries:
                try:
                    if isinstance(e.get('external_links'), str):
                        e['external_links'] = json.loads(e.get('external_links') or '[]')
                except Exception:
                    e['external_links'] = []

        # Build topic timeline map (sorted chronological entries per topic)
        topic_timeline_map = defaultdict(list)
        for e in all_entries:
            topic_timeline_map[e['topic']].append(e)

        # Group entries by author
        entries_by_author = defaultdict(list)
        for e in all_entries:
            entries_by_author[e['author']].append(e)

        results = []
        for nick, author_entries in entries_by_author.items():
            evaluation = self.evaluate_author_on_manufactured_topics(
                nick, author_entries, all_entries, topic_timeline_map
            )
            
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
                    evaluation['metrics']['inception_count'],
                    evaluation['metrics']['early_swarm_count'],
                    evaluation['metrics']['manufactured_focus_ratio'],
                    evaluation['metrics']['vote_brigading'],
                    evaluation['metrics']['stance_alignment'],
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
            if ev['troll_score'] >= 40 and "Organik" not in ev['detected_cell'] and "Gürültü" not in ev['detected_cell']:
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
