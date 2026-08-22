import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from noise_filter import is_noise_topic
from smear_detector import detect_entry_stance, calculate_smear_intensity_ratio, calculate_narrative_alignment
from discovery_engine import TrollDiscoveryEngine

def test_refined_engine():
    print("==========================================================")
    print("🎯 Siyasi Troll, İftira & Gürültü Filtresi Testleri Başladı")
    print("==========================================================\n")

    # 1. TEST NOISE & SPORTS FILTER
    print("[1] Futbol, Spor ve Magazin Gürültüsü Filtreleme Testi...")
    noise_topics = [
        "22 ağustos 2026 fenerbahçe konyaspor maçı",
        "arda güler",
        "galatasaray beşiktaş derbisi hakem skandalı",
        "steam yaz indirimleri",
        "house of the dragon 2. sezon 5. bölüm",
        "başak burcu erkeği özellikleri"
    ]
    for nt in noise_topics:
        assert is_noise_topic(nt) == True, f"Futbol/gürültü başlığı filtrelenemedi: {nt}"
    print("  -> Tüm futbol, maç, dizi ve magazin başlıkları başarıyla filtrelendi.")

    political_topics = [
        "chp belediyelerinin konser harcamaları",
        "ekrem imamoğlu roma gezisi faturası",
        "haşemalı kadınların plaja alınmaması",
        "enflasyon ve pahalılık karşısında esnaf",
        "belediyeye kayyum atanması iddiaları"
    ]
    for pt in political_topics:
        assert is_noise_topic(pt) == False, f"Siyasi başlık yanlışlıkla filtrelendi: {pt}"
    print("  -> Tüm siyasi, belediye ve kutuplaştırma başlıkları analiz havuzuna alındı.")

    # 2. TEST SMEAR & STANCE DETECTION
    print("\n[2] İftira, Karalama ve Söylem Polaritesi Testi...")
    smear_entry = {
        "id": "1",
        "topic": "chp belediyelerinin konser harcamaları",
        "content": "halkın parasıyla milyonluk konser vurgunu yapıyorlar, liyakatsiz yandaşlara peşkeş çekiliyor."
    }
    stance = detect_entry_stance(smear_entry['topic'], smear_entry['content'])
    assert stance['stance'] == 'smear', f"Karalama stance hatalı: {stance}"
    print(f"  -> İftira/Karalama tespiti: {stance['stance']} (Vurgun, Peşkeş, Liyakatsiz)")

    # 3. TEST OPPOSING ORGANIC DEBATERS (Should NOT align)
    print("\n[3] Zıt Kutuplu Organik Tartışmacıların Elenmesi Testi...")
    defender_entry = {
        "id": "2",
        "topic": "chp belediyelerinin konser harcamaları",
        "content": "tüm harcamalar sayıştay denetiminden geçiyor, karalama kampanyalarına inanmayın."
    }
    attacker_entry = {
        "id": "3",
        "topic": "chp belediyelerinin konser harcamaları",
        "content": "şahsi ikbal için belediye bütçesini hortumlayanların rezaleti."
    }
    
    # When author posts neutral/defense vs attacker
    alignment = calculate_narrative_alignment([defender_entry], [attacker_entry])
    assert alignment == 0.0, f"Zıt görüşlü organik yazarlar eşleşti! Skor: {alignment}"
    print("  -> Karşıt görüşlü organik yazarlar başarıyla ayrıştırıldı (Söylem Uyumu = %0).")

    # 4. TEST FULL TROLL DISCOVERY ENGINE
    print("\n[4] Gelişmiş Troll Motoru Taraması...")
    engine = TrollDiscoveryEngine()
    evaluations = engine.run_auto_discovery_scan(days=30)
    
    print(f"  -> Değerlendirilen Hedef Yazar: {len(evaluations)}")
    high_trolls = [e for e in evaluations if e['troll_score'] >= 65]
    print(f"  -> Yüksek Siyasi Troll Skoru Alanlar: {len(high_trolls)}")
    
    for t in high_trolls[:3]:
        m = t['metrics']
        print(f"     @{t['nick']}: Skor=%{t['troll_score']} -> Söylem Uyumu=%{m['stance_alignment']}, Karalama=%{m['smear_intensity']}, Beğeni Halkası=%{m['vote_brigading']}")

    print("\n==========================================================")
    print("✅ TÜM GELİŞMİŞ SİYASİ TROLL VE GÜRÜLTÜ TESTLERİ BAŞARILI!")
    print("==========================================================")

if __name__ == "__main__":
    test_refined_engine()
