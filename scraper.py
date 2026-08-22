import time
import urllib.parse
import re
import uuid
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
from bs4 import BeautifulSoup

try:
    from curl_cffi import requests as c_requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    import requests as c_requests
    CURL_CFFI_AVAILABLE = False

from config import TARGET_AUTHORS, SCRAPER_CONFIG, NARRATIVE_CATEGORIES
from database import upsert_entry, get_db

class EksiScraper:
    def __init__(self, domain: str = None):
        self.domain = domain or SCRAPER_CONFIG["default_domain"]
        self.impersonations = ['chrome120', 'chrome110', 'safari15_3', 'edge101']

    def _fetch_url(self, url: str, headers: Optional[Dict[str, str]] = None) -> Optional[str]:
        req_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': f'https://{self.domain}/'
        }
        if headers:
            req_headers.update(headers)

        for imp in self.impersonations:
            try:
                if CURL_CFFI_AVAILABLE:
                    r = c_requests.get(
                        url,
                        headers=req_headers,
                        impersonate=imp,
                        timeout=SCRAPER_CONFIG["timeout"],
                        verify=False
                    )
                else:
                    r = c_requests.get(url, headers=req_headers, timeout=SCRAPER_CONFIG["timeout"])

                if r.status_code == 200:
                    return r.text
            except Exception as e:
                time.sleep(0.3)
        return None

    def parse_entry_date(self, date_str: str) -> Optional[datetime]:
        """Parses Turkish Eksi Sozluk date formats like '22.08.2026 15:44 ~ 16:24' or '21.08.2026 10:46'."""
        if not date_str:
            return None
        try:
            cleaned = date_str.split('~')[0].strip()
            return datetime.strptime(cleaned, "%d.%m.%Y %H:%M")
        except Exception:
            return None

    def classify_entry(self, topic: str, content: str) -> str:
        """Classifies entry into one of the key manipulation categories based on keywords."""
        full_text = f"{topic.lower()} {content.lower()}"
        
        category_scores = {}
        for cat, data in NARRATIVE_CATEGORIES.items():
            score = 0
            for kw in data["keywords"]:
                if kw in full_text:
                    score += full_text.count(kw) * (2 if kw in topic.lower() else 1)
            category_scores[cat] = score
            
        best_cat = max(category_scores.items(), key=lambda x: x[1])
        return best_cat[0] if best_cat[1] > 0 else "Suni Gündem & Viral Çarpıtma"

    def scrape_author(self, nick: str, lookback_days: int = 7, max_pages: int = 4) -> List[Dict[str, Any]]:
        """Scrapes entries for a single author up to lookback_days."""
        results = []
        encoded_nick = urllib.parse.quote(nick)
        cutoff_date = datetime.now() - timedelta(days=lookback_days)

        for page in range(1, max_pages + 1):
            url = f"https://{self.domain}/son-entryleri?nick={encoded_nick}&p={page}"
            html = self._fetch_url(url)
            if not html:
                break

            soup = BeautifulSoup(html, 'html.parser')
            entries = soup.select('#entry-item-list > li')
            if not entries:
                break

            page_valid_entries = 0
            reached_cutoff = False

            for li in entries:
                entry_id = li.get('data-id')
                author = li.get('data-author', nick)
                content_div = li.select_one('.content')
                date_elem = li.select_one('.entry-date')
                
                if not entry_id or not content_div:
                    continue

                prev_h1 = li.find_previous('h1')
                topic_title = prev_h1.text.strip() if prev_h1 else "Bilinmeyen Başlık"

                raw_date = date_elem.text.strip() if date_elem else ""
                dt_obj = self.parse_entry_date(raw_date)
                
                # Check date cutoff
                if dt_obj and dt_obj < cutoff_date:
                    reached_cutoff = True
                    break

                created_at_iso = dt_obj.isoformat() if dt_obj else datetime.now().isoformat()
                content_text = content_div.text.strip()
                
                # Extract external links
                links = []
                for a in content_div.select('a'):
                    href = a.get('href', '')
                    if href.startswith('http') and 'eksisozluk' not in href:
                        links.append({'text': a.text.strip(), 'url': href})

                fav_count = int(li.get('data-favorite-count', 0) or 0)
                comment_count = int(li.get('data-comment-count', 0) or 0)
                
                category = self.classify_entry(topic_title, content_text)

                entry_record = {
                    "id": str(entry_id),
                    "author": author,
                    "topic": topic_title,
                    "topic_slug": re.sub(r'[^a-zA-Z0-9\-]', '', topic_title.lower().replace(' ', '-')),
                    "content": content_text,
                    "date_str": raw_date,
                    "created_at": created_at_iso,
                    "favorite_count": fav_count,
                    "comment_count": comment_count,
                    "category": category,
                    "sentiment": "negative" if any(w in content_text.lower() for w in ["rezalet", "terör", "ihanet", "skandal", "isyan", "yalan", "suç"]) else "neutral",
                    "external_links": links,
                    "is_coordinated": False
                }
                
                results.append(entry_record)
                upsert_entry(entry_record)
                page_valid_entries += 1

            if reached_cutoff or page_valid_entries == 0:
                break
                
            time.sleep(0.4)

        return results

    def run_full_scan(
        self,
        job_id: str,
        authors: Optional[List[str]] = None,
        lookback_days: int = 7,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """Runs full scraping scan across all authors and records the job in SQLite."""
        target_list = authors or TARGET_AUTHORS
        total_authors = len(target_list)
        total_entries = 0
        logs = []

        with get_db() as conn:
            conn.execute("""
                INSERT INTO scrape_jobs (id, started_at, status, total_authors, authors_processed, entries_found, logs)
                VALUES (?, ?, 'running', ?, 0, 0, '[]')
            """, (job_id, datetime.now().isoformat(), total_authors))
            conn.commit()

        for idx, nick in enumerate(target_list, start=1):
            log_msg = f"[{idx}/{total_authors}] @{nick} taranıyor..."
            logs.append({"time": datetime.now().strftime("%H:%M:%S"), "msg": log_msg, "type": "info"})
            
            if callback:
                callback({"processed": idx - 1, "total": total_authors, "current": nick, "entries": total_entries})

            try:
                entries = self.scrape_author(nick, lookback_days=lookback_days)
                count = len(entries)
                total_entries += count
                
                success_msg = f"@{nick}: {count} yeni entry kaydedildi."
                logs.append({"time": datetime.now().strftime("%H:%M:%S"), "msg": success_msg, "type": "success" if count > 0 else "neutral"})
                
                # Update author last_scraped_at
                with get_db() as conn:
                    conn.execute("UPDATE authors SET last_scraped_at = ? WHERE nick = ?", (datetime.now().isoformat(), nick))
                    conn.commit()
            except Exception as e:
                err_msg = f"@{nick} taranırken hata: {str(e)}"
                logs.append({"time": datetime.now().strftime("%H:%M:%S"), "msg": err_msg, "type": "error"})

            with get_db() as conn:
                conn.execute("""
                    UPDATE scrape_jobs
                    SET authors_processed = ?, entries_found = ?, logs = ?
                    WHERE id = ?
                """, (idx, total_entries, json.dumps(logs), job_id))
                conn.commit()

            time.sleep(0.3)

        # Mark job finished
        with get_db() as conn:
            conn.execute("""
                UPDATE scrape_jobs
                SET finished_at = ?, status = 'completed', authors_processed = ?, entries_found = ?, logs = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), total_authors, total_entries, json.dumps(logs), job_id))
            conn.commit()

        # Trigger automatic coordination recalculation
        from analyzer import detect_coordinated_operations
        detect_coordinated_operations(days=lookback_days)

        if callback:
            callback({"processed": total_authors, "total": total_authors, "current": "Tamamlandı", "entries": total_entries, "status": "completed"})

        return {
            "job_id": job_id,
            "total_authors": total_authors,
            "entries_found": total_entries,
            "status": "completed"
        }

    def scrape_gundem_and_top_entries(self, limit_topics: int = 10, max_entries_per_topic: int = 10) -> Dict[str, Any]:
        """
        Scrapes trending Gündem and Debe (most favorited/popular) topics from Ekşi Sözlük,
        extracts candidate authors, and records entries to database for automated troll discovery.
        """
        discovered_candidates = set()
        new_entries_count = 0
        topics_to_scan = []

        # 1. Fetch Gündem topics
        gundem_html = self._fetch_url(f"https://{self.domain}/basliklar/gundem")
        if gundem_html:
            soup = BeautifulSoup(gundem_html, 'html.parser')
            for a in soup.select('ul.topic-list > li > a')[:limit_topics]:
                href = a.get('href', '')
                title = a.text.strip()
                # Clean entry count badge from title text (e.g. 'fenerbahçe 892' -> 'fenerbahçe')
                clean_title = re.sub(r'\s+\d+$', '', title)
                if href and clean_title:
                    topics_to_scan.append({'title': clean_title, 'href': href})

        # 2. Fetch Debe (Dünün en beğenilen entryleri)
        debe_html = self._fetch_url(f"https://{self.domain}/debe")
        if debe_html:
            soup = BeautifulSoup(debe_html, 'html.parser')
            for a in soup.select('ul.topic-list > li > a, #topic > li > a')[:limit_topics]:
                href = a.get('href', '')
                title = a.text.strip()
                clean_title = re.sub(r'\s+\d+$', '', title)
                if href and clean_title and not any(t['href'] == href for t in topics_to_scan):
                    topics_to_scan.append({'title': clean_title, 'href': href})

        # 3. For each topic, fetch most favorited / popular entries (?a=nice or ?a=popular)
        for t_info in topics_to_scan:
            topic_url = f"https://{self.domain}{t_info['href']}"
            if '?a=' not in topic_url:
                topic_url += "?a=popular"

            topic_html = self._fetch_url(topic_url)
            if not topic_html:
                continue

            soup = BeautifulSoup(topic_html, 'html.parser')
            entries = soup.select('#entry-item-list > li')

            for li in entries[:max_entries_per_topic]:
                entry_id = li.get('data-id')
                author = li.get('data-author')
                content_div = li.select_one('.content')
                date_elem = li.select_one('.entry-date')

                if not entry_id or not author or not content_div:
                    continue

                discovered_candidates.add(author)
                raw_date = date_elem.text.strip() if date_elem else ""
                dt_obj = self.parse_entry_date(raw_date)
                created_at_iso = dt_obj.isoformat() if dt_obj else datetime.now().isoformat()
                content_text = content_div.text.strip()
                fav_count = int(li.get('data-favorite-count', 0) or 0)
                category = self.classify_entry(t_info['title'], content_text)

                links = []
                for a_link in content_div.select('a'):
                    h = a_link.get('href', '')
                    if h.startswith('http') and 'eksisozluk' not in h:
                        links.append({'text': a_link.text.strip(), 'url': h})

                entry_record = {
                    "id": str(entry_id),
                    "author": author,
                    "topic": t_info['title'],
                    "topic_slug": re.sub(r'[^a-zA-Z0-9\-]', '', t_info['title'].lower().replace(' ', '-')),
                    "content": content_text,
                    "date_str": raw_date,
                    "created_at": created_at_iso,
                    "favorite_count": fav_count,
                    "comment_count": 0,
                    "category": category,
                    "sentiment": "negative" if any(w in content_text.lower() for w in ["rezalet", "terör", "ihanet", "skandal", "isyan", "yalan", "suç"]) else "neutral",
                    "external_links": links,
                    "is_coordinated": False
                }
                upsert_entry(entry_record)
                new_entries_count += 1

            time.sleep(0.3)

        return {
            "topics_scanned": len(topics_to_scan),
            "candidates_found": list(discovered_candidates),
            "new_entries_count": new_entries_count
        }
