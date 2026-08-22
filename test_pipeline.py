import sys
import os
import json
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def run_tests():
    print("[*] TrollRadar Test Pipeline Başlatılıyor...")
    
    # 1. Config Test
    from config import TARGET_AUTHORS, NARRATIVE_CATEGORIES
    assert len(TARGET_AUTHORS) == 27, f"Beklenen 27 yazar, bulunan: {len(TARGET_AUTHORS)}"
    print(f"[OK] 27 Yazar Başarıyla Yüklendi: {TARGET_AUTHORS[:3]}...")

    # 2. Database & Seed Test
    from database import init_db, get_db, get_entries, get_all_authors_summary, get_overview_stats
    from seed_data import seed_database
    init_db()
    seed_database(force=True)
    
    with get_db() as conn:
        entry_count = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        assert entry_count > 0, "Veritabanına entry kaydedilemedi!"
    print(f"[OK] Veritabanı ve Tohum Veriler Hazır: {entry_count} entry mevcut.")

    # 3. Analyzer Test
    from analyzer import (
        detect_coordinated_operations, get_coordination_network_data,
        get_posting_heatmap_data, get_top_manipulation_narratives, extract_top_keywords
    )
    coords = detect_coordinated_operations(days=30)
    print(f"[OK] Koordinasyon Analizi: {len(coords)} organize operasyon tespit edildi.")

    narratives = get_top_manipulation_narratives(days=30)
    assert len(narratives) > 0, "Manipülasyon anlatısı üretilemedi!"
    print(f"[OK] Haftalık İstihbarat Bülteni: {len(narratives)} ana tema derlendi.")
    for n in narratives[:3]:
        print(f"   -> #{n['topic']} [{n['category']}] ({n['author_count']} Yazar)")

    network = get_coordination_network_data(days=30)
    assert len(network['nodes']) > 0, "Ağ düğümleri oluşturulamadı!"
    print(f"[OK] Koordinasyon Ağı: {len(network['nodes'])} düğüm, {len(network['links'])} bağlantı.")

    heatmap = get_posting_heatmap_data(days=30)
    assert len(heatmap) == 7 * 24, "Isı haritası boyutu hatalı!"
    print(f"[OK] Mesai Isı Haritası: 7x24 grid matrisi başarıyla hesaplandı.")

    keywords = extract_top_keywords(days=30, top_n=10)
    print(f"[OK] Anahtar Kelime Madenciliği: {[k['word'] for k in keywords[:5]]}")

    # 4. Scraper Unit Tests
    from scraper import EksiScraper
    scraper = EksiScraper()
    dt = scraper.parse_entry_date("22.08.2026 15:44 ~ 16:24")
    assert dt == datetime(2026, 8, 22, 15, 44), f"Tarih ayrıştırma hatası: {dt}"
    cat = scraper.classify_entry("haşemalı kadın plajda tartıştı", "laiklik ve din özgürlüğü")
    assert cat == "Kültür Savaşı & Yaşam Tarzı", f"Kategori sınıflandırma hatası: {cat}"
    print("[OK] Scraper Birim Testleri Geçti.")

    # 5. FastAPI Endpoints Direct Test
    from server import get_stats, get_narratives, get_authors, get_entry_list, get_coordination, get_heatmap
    
    stats_data = get_stats(days=7)
    assert "total_entries" in stats_data, "Stats yanıtında total_entries eksik!"
    print(f"[OK] Stats API: {stats_data['total_entries']} entry, {stats_data['active_authors']} aktif yazar.")

    narr_data = get_narratives(days=7)
    assert len(narr_data["narratives"]) > 0, "Narratives yanıtı boş!"
    print(f"[OK] Narratives API: {len(narr_data['narratives'])} anlatı dosyası.")

    authors_data = get_authors(days=7)
    assert len(authors_data["authors"]) == 27, f"Beklenen 27 yazar, gelen: {len(authors_data['authors'])}"
    print(f"[OK] Authors API: 27/27 yazar bilgisi doğrulandı.")

    entries_data = get_entry_list(days=7, limit=10)
    assert len(entries_data["entries"]) > 0, "Entries API yanıtı boş!"
    print(f"[OK] Entries API: {entries_data['total']} kayıt bulundu.")

    coord_data = get_coordination(days=7)
    assert "network" in coord_data and "coordinations" in coord_data
    print(f"[OK] Coordination API: {len(coord_data['coordinations'])} operasyon.")

    print("\n✅ TÜM TESTLER VE FONKSİYONLAR BAŞARIYLA GEÇTİ!")

if __name__ == "__main__":
    run_tests()
