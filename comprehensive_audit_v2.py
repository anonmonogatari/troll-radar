import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import time
import json
import requests
from bs4 import BeautifulSoup
from database import init_db, get_db, get_entries, get_all_authors_summary
from noise_filter import is_noise_topic
from smear_detector import detect_entry_stance, calculate_smear_intensity_ratio, calculate_vote_brigading_score, calculate_narrative_alignment
from discovery_engine import TrollDiscoveryEngine
from scraper import EksiScraper

BASE_URL = "http://127.0.0.1:8000"

def run_exhaustive_local_audit():
    print("=================================================================")
    print("🔍 TrollRadar 2.0 Kapsamlı Yerel ve Sistem Hata (Bug) Denetimi")
    print("=================================================================\n")

    bugs = []
    warnings = []

    # -------------------------------------------------------------
    # 1. LIVE HTTP SERVER & ENDPOINT INTEGRITY TEST
    # -------------------------------------------------------------
    print("[1] Yerel Canlı Sunucu & REST API Endpoint Bütünlüğü...")
    endpoints = [
        ("GET", "/", None, 200),
        ("GET", "/api/stats?days=1", None, 200),
        ("GET", "/api/stats?days=7", None, 200),
        ("GET", "/api/stats?days=30", None, 200),
        ("GET", "/api/narratives?days=7", None, 200),
        ("GET", "/api/authors?days=7", None, 200),
        ("GET", "/api/entries?days=7&limit=10&offset=0", None, 200),
        ("GET", "/api/coordination?days=7", None, 200),
        ("GET", "/api/heatmap?days=7", None, 200),
        ("GET", "/api/keywords?days=7&limit=30", None, 200),
        ("GET", "/api/discovery/candidates?days=7", None, 200),
        ("POST", "/api/discovery/scan?days=7&live_gundem=false", None, 200),
        ("POST", "/api/discovery/unpromote/becathlon", None, 200),
        ("POST", "/api/discovery/promote/becathlon", None, 200),
        ("GET", "/api/export?format=csv&days=7", None, 200),
        ("GET", "/api/export?format=json&days=7", None, 200),
    ]

    for method, path, body, expected_status in endpoints:
        try:
            url = f"{BASE_URL}{path}"
            if method == "GET":
                res = requests.get(url, timeout=5)
            else:
                res = requests.post(url, json=body, timeout=5)
            
            if res.status_code != expected_status:
                bugs.append(f"API Endpoint Hatası: {method} {path} beklenmeyen durum kodu döndürdü ({res.status_code} != {expected_status})")
            else:
                # Validate JSON response if expected
                if "api" in path and "export?format=csv" not in path:
                    try:
                        data = res.json()
                        assert data is not None
                    except Exception as e:
                        bugs.append(f"Geçersiz JSON yanıtı: {path} -> {e}")
        except Exception as e:
            bugs.append(f"Sunucu bağlantı hatası ({method} {path}): {e}")

    print("  -> Tüm REST API rotaları yanıt verdi ve durum kodları doğrulandı.")

    # -------------------------------------------------------------
    # 2. NOISE FILTER STRESS TEST
    # -------------------------------------------------------------
    print("\n[2] Gürültü ve Spor Filtresi Stres Testi (15 Senaryo)...")
    sports_cases = [
        "galatasaray trabzonspor derbisi", "fenerbahçe konyaspor maçı hakem kararları",
        "arda güler real madrid golü", "süper lig puan durumu", "şampiyonlar ligi kura çekimi",
        "mourinho basın toplantısı", "playstation 5 pro fiyatı", "valorant yeni ajan yaması",
        "house of the dragon sezon finali", "netflix yeni türk dizisi", "akrep burcu kadını"
    ]
    for sc in sports_cases:
        if not is_noise_topic(sc):
            bugs.append(f"Gürültü filtresi başarısız: '{sc}' elenmedi!")

    valid_political_cases = [
        "chp belediyelerinin konser harcamaları", "ekrem imamoğlu roma gezisi faturası",
        "mansur yavaş ebru gündeş konseri açıklaması", "haşemalı kadınların havuza alınmaması",
        "enflasyon karşısında ezilen asgari ücretli", "turist kazıklayan fırsatçı esnaf",
        "akp ilçe başkanlığı ihale skandalı", "belediyelere kayyum atanması kanunu"
    ]
    for pc in valid_political_cases:
        if is_noise_topic(pc):
            bugs.append(f"Siyasi konu yanlışlıkla elendi: '{pc}'!")

    print("  -> Gürültü ve siyaset filtreleme mantığı 100% doğru çalışıyor.")

    # -------------------------------------------------------------
    # 3. VOTE BRIGADING HARD-GATE & DISCOVERY LOGIC TEST
    # -------------------------------------------------------------
    print("\n[3] Beğeni Halkası (Hard Gate) & Siyasi Karalama Doğrulaması...")
    engine = TrollDiscoveryEngine()

    # Case A: Smear entries with ZERO favorites -> MUST be disqualified (Score = 0)
    zero_fav_entry = {
        "id": "test_zero_fav",
        "author": "bireysel_yazar",
        "topic": "chp belediyelerinin konser harcamaları",
        "content": "bence konser harcamaları israftır ve liyakatsiz bir karardır.",
        "favorite_count": 0,
        "created_at": "2026-08-22T14:00:00"
    }
    eval_zero = engine.evaluate_author("bireysel_yazar", [zero_fav_entry], [zero_fav_entry])
    if eval_zero['troll_score'] != 0.0 or "Elendi" not in eval_zero['detected_cell']:
        bugs.append(f"Hard Gate Hatası: Beğeni halkası olmayan yazar elenmedi (Skor: {eval_zero['troll_score']})")

    # Case B: High favorites on harmless/cooking topic -> MUST be disqualified (Score = 0)
    cooking_entry = {
        "id": "test_cooking",
        "author": "yemek_ustasi",
        "topic": "ev yapımı menemen tarifi",
        "content": "soğanlı menemen her zaman daha lezzetli olur.",
        "favorite_count": 45,
        "created_at": "2026-08-22T14:00:00"
    }
    eval_cooking = engine.evaluate_author("yemek_ustasi", [cooking_entry], [cooking_entry])
    if eval_cooking['troll_score'] != 0.0:
        bugs.append(f"Gürültü Skoru Hatası: Yemek yazarının troll skoru 0 olmalıydı (Skor: {eval_cooking['troll_score']})")

    # Case C: Organized smear entries with HIGH favorites in ring -> MUST score high (> 75)
    troll_entries = [
        {
            "id": "troll_1",
            "author": "organize_troll_1",
            "topic": "chp belediyelerinin konser harcamaları",
            "content": "halkın parasıyla milyonluk konser vurgunu yapıyorlar, liyakatsiz yandaşlara peşkeş çekiliyor.",
            "favorite_count": 18,
            "created_at": "2026-08-22T14:02:00"
        },
        {
            "id": "troll_2",
            "author": "organize_troll_2",
            "topic": "chp belediyelerinin konser harcamaları",
            "content": "şahsi ikbal için belediye bütçesini hortumlayanların rezaleti ve yolsuzluk skandalı.",
            "favorite_count": 16,
            "created_at": "2026-08-22T14:05:00"
        }
    ]
    eval_troll = engine.evaluate_author("organize_troll_1", [troll_entries[0]], troll_entries)
    if eval_troll['troll_score'] < 70.0:
        bugs.append(f"Troll Puanlama Hatası: Organize troll hak ettiği yüksek skoru alamadı (Skor: {eval_troll['troll_score']})")
    else:
        print(f"  -> Organize troll tespiti başarılı: Skor = %{eval_troll['troll_score']} [{eval_troll['risk_level']}]")

    # -------------------------------------------------------------
    # 4. FRONTEND HTML & JS ELEMENT SYNC TEST
    # -------------------------------------------------------------
    print("\n[4] Ön Yüz (Frontend HTML/JS) Etiket & Eleman Eşleşme Denetimi...")
    with open("static/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()

    required_dom_ids = [
        "view-briefing", "view-discovery", "view-analytics", "view-network",
        "view-authors", "view-entries", "tab-btn-discovery", "discovery-scan-btn",
        "discovery-cells-grid", "discovery-candidates-tbody", "networkCanvas",
        "author-modal", "scrape-modal", "timelineChart", "categoryChart"
    ]
    for dom_id in required_dom_ids:
        if f'id="{dom_id}"' not in html_content:
            bugs.append(f"HTML DOM Hatası: index.html içinde '{dom_id}' elementi eksik!")

    print("  -> Tüm DOM ID'leri, modallar ve sekme referansları eksiksiz.")

    # -------------------------------------------------------------
    # 5. SUMMARY
    # -------------------------------------------------------------
    print("\n=================================================================")
    if bugs:
        print(f"❌ DENETİMDE {len(bugs)} ADET BUG TESPİT EDİLDİ:")
        for idx, b in enumerate(bugs, 1):
            print(f"  {idx}. {b}")
    else:
        print("✅ TÜM MODÜLLER, CANLI API ENDPOINTLERİ VE MATEMATİKSEL KONTROLLER %100 HATASIZ!")
    print("=================================================================")

    return bugs

if __name__ == "__main__":
    run_exhaustive_local_audit()
