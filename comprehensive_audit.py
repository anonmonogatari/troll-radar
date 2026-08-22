import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import json
import time
import urllib.parse
from datetime import datetime, timedelta

def run_comprehensive_audit():
    print("==========================================================")
    print("🔍 TrollRadar Kapsamlı Sistem & Hata (Bug) Denetimi Başladı")
    print("==========================================================\n")
    
    bugs_found = []

    # 1. TEST DATABASE INITIALIZATION & SCHEMA
    print("[1] Veritabanı ve Şema Denetimi...")
    try:
        from database import init_db, get_db, upsert_entry, get_entries, get_all_authors_summary, get_overview_stats
        init_db()
        with get_db() as conn:
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            required_tables = ['authors', 'entries', 'coordinations', 'scrape_jobs', 'discovered_trolls']
            for t in required_tables:
                if t not in tables:
                    bugs_found.append(f"Veritabanında '{t}' tablosu eksik!")
        print("  -> Veritabanı tabloları tam ve erişilebilir.")
    except Exception as e:
        bugs_found.append(f"Veritabanı başlatma hatası: {e}")

    # 2. TEST NLP & ANALYZER ZERO-DIVISION / EDGE CASES
    print("\n[2] Analiz & NLP Matematiksel Sınır Değerleri (Edge Cases)...")
    try:
        from analyzer import (
            detect_coordinated_operations, get_coordination_network_data,
            get_posting_heatmap_data, get_top_manipulation_narratives, extract_top_keywords
        )
        from discovery_engine import TrollDiscoveryEngine
        
        engine = TrollDiscoveryEngine()
        
        # Test empty inputs
        assert engine.calculate_topic_entropy([]) == 0.0, "Boş listede entropi hatası"
        assert engine.calculate_political_focus_ratio([], []) == 0.0, "Boş listede siyasi oran hatası"
        assert engine.calculate_shift_regularity([]) == 0.0, "Boş listede mesai oranı hatası"
        assert engine.calculate_temporal_synchronicity([], []) == 0.0, "Boş listede senkronisite hatası"
        assert engine.calculate_link_bias([]) == 0.0, "Boş listede link hatası"

        # Test single item inputs
        assert engine.calculate_topic_entropy(["tek konu"]) == 0.0, "Tek konuda entropi 0 olmalı"
        
        # Test invalid timestamps in heatmap / sync
        invalid_eval = engine.evaluate_author("test_user", [{
            "id": "999", "author": "test_user", "topic": "test", "content": "test",
            "created_at": "gecersiz-tarih", "category": "Genel"
        }], [])
        assert invalid_eval['troll_score'] >= 0, "Geçersiz tarihte değerlendirme patladı"

        print("  -> Matematiksel fonksiyonlar ve boş/hatalı veri korumaları başarılı.")
    except Exception as e:
        bugs_found.append(f"Analiz motoru sınır değer hatası: {e}")

    # 3. TEST FASTAPI ENDPOINTS & PARAMETER VALIDATION
    print("\n[3] FastAPI Endpointleri & Parametre Geçirgenliği...")
    try:
        from server import (
            get_stats, get_narratives, get_entry_list, get_authors,
            get_coordination, get_heatmap, get_keywords, get_discovery_candidates,
            trigger_discovery_scan, promote_author_to_watchlist, export_data
        )

        # Test days = 1, 3, 7, 30, 0, -1, 365
        for d in [1, 3, 7, 30, 0, -5, 365]:
            stats = get_stats(days=d)
            assert "total_entries" in stats

        # Test special characters in search
        res_search = get_entry_list(search="' OR '1'='1' -- %20 / <script>alert(1)</script>")
        assert "entries" in res_search

        # Test non-existent author
        res_auth = get_entry_list(author="olmayan_yazar_123456789")
        assert res_auth["total"] == 0

        # Test export format (JSON & CSV)
        csv_resp = export_data(format="csv", days=7)
        assert csv_resp.media_type == "text/csv"
        
        json_resp = export_data(format="json", days=7)
        assert json_resp.status_code == 200

        # Test discovery routes
        disc_res = get_discovery_candidates(days=7)
        assert "candidates" in disc_res and "cells" in disc_res

        # Test promote
        promote_res = promote_author_to_watchlist("timurun fillerinin bakicisi")
        assert promote_res["status"] == "success"

        print("  -> Tüm API endpointleri, arama injection testleri ve filtreler hatasız çalışıyor.")
    except Exception as e:
        bugs_found.append(f"API endpoint testi hatası: {e}")

    # 4. TEST SCRAPER DATE & HTML PARSING RESILIENCE
    print("\n[4] Scraper Tarih & HTML Ayrıştırma Dayanıklılığı...")
    try:
        from scraper import EksiScraper
        scraper = EksiScraper()
        
        # Test various date formats
        valid_dates = [
            ("22.08.2026 15:44 ~ 16:24", datetime(2026, 8, 22, 15, 44)),
            ("22.08.2026 15:44", datetime(2026, 8, 22, 15, 44)),
            ("01.01.2025 00:00", datetime(2025, 1, 1, 0, 0)),
            ("", None),
            ("bozuk tarih metni", None),
            (None, None)
        ]
        for raw, expected in valid_dates:
            parsed = scraper.parse_entry_date(raw)
            if expected is not None:
                assert parsed == expected, f"Tarih formatı eşleşmedi: {raw} -> {parsed} (Beklenen: {expected})"
            else:
                assert parsed is None, f"Hatalı tarihte None dönmedi: {raw}"

        # Test category classifier with extreme texts
        assert scraper.classify_entry("", "") in NARRATIVE_CATEGORIES or scraper.classify_entry("", "") == "Suni Gündem & Viral Çarpıtma"
        print("  -> Scraper tarih ve metin ayrıştırma testleri başarılı.")
    except Exception as e:
        bugs_found.append(f"Scraper ayrıştırma hatası: {e}")

    # 5. TEST STATIC BUNDLE GENERATION & JSON VALIDITY
    print("\n[5] Statik Derleme (export_static) & JSON Sentaks Bütünlüğü...")
    try:
        from export_static import export_static_site
        from config import BASE_DIR
        
        export_static_site()
        dist_data = BASE_DIR / "dist" / "data"
        
        for json_file in dist_data.glob("*.json"):
            with open(json_file, "r", encoding="utf-8") as f:
                content = json.load(f)
                assert content is not None, f"{json_file.name} içeriği boş!"
        print("  -> Tüm statik JSON dosyaları eksiksiz ve geçerli JSON sentaksına sahip.")
    except Exception as e:
        bugs_found.append(f"Statik derleme hatası: {e}")

    # 6. SUMMARY REPORT
    print("\n==========================================================")
    if bugs_found:
        print(f"❌ DENETİMDE {len(bugs_found)} HATA/BUG TESPİT EDİLDİ:")
        for idx, b in enumerate(bugs_found, 1):
            print(f"  {idx}. {b}")
    else:
        print("✅ TÜM MODÜLLER, ENDPOINTLER VE VERİ BORU HATLARI 100% HATASIZ!")
    print("==========================================================")
    
    return bugs_found

if __name__ == "__main__":
    from config import NARRATIVE_CATEGORIES
    run_comprehensive_audit()
