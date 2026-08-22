import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from discovery_engine import TrollDiscoveryEngine
from database import init_db, get_db
from seed_data import seed_database

def test_auto_discovery():
    print("[*] Otomatik Troll Keşif Motoru Testleri Başlatılıyor...")
    
    init_db()
    seed_database(force=True)

    engine = TrollDiscoveryEngine()

    # 1. Test Shannon Entropy
    diverse_topics = ["rock müzik", "sinema", "türk mutfağı", "kitap önerileri", "futbol"]
    narrow_topics = ["haşema", "haşema", "haşema", "chp konser", "chp konser"]
    
    entropy_diverse = engine.calculate_topic_entropy(diverse_topics)
    entropy_narrow = engine.calculate_topic_entropy(narrow_topics)
    
    assert entropy_diverse > entropy_narrow, f"Entropi testi başarısız: {entropy_diverse} vs {entropy_narrow}"
    print(f"[OK] Shannon Entropisi: Doğal Dağılım={entropy_diverse} H(x) > Troll Dağılım={entropy_narrow} H(x)")

    # 2. Test Full Discovery Scan
    evaluations = engine.run_auto_discovery_scan(days=30)
    assert len(evaluations) > 0, "Aday değerlendirmesi yapılamadı!"
    print(f"[OK] Otomatik Değerlendirilen Hesap Sayısı: {len(evaluations)}")

    # Ground Truth Verification
    high_scoring_trolls = [e for e in evaluations if e['troll_score'] >= 65]
    assert len(high_scoring_trolls) > 0, "Bilinen troll hesaplar yüksek skor alamadı!"
    print(f"[OK] Yüksek Riskli/Kesin Troll Olarak Keşfedilen Hesaplar: {len(high_scoring_trolls)} adet")
    for t in high_scoring_trolls[:3]:
        print(f"   -> @{t['nick']}: Skor=%{t['troll_score']} [{t['risk_level']}] -> Hücre: {t['detected_cell']}")

    # 3. Test Cell Clustering
    cells = engine.cluster_troll_cells(evaluations)
    assert len(cells) > 0, "Troll hücreleri ayrıştırılamadı!"
    print(f"[OK] Ayrıştırılan Operasyonel Hücre Sayısı: {len(cells)}")
    for c in cells:
        print(f"   -> Hücre '{c['cell_name']}': {c['member_count']} Üye (Ortalama Skor: %{c['average_troll_score']})")

    print("\n✅ TÜM OTOMATİK KEŞİF TESTLERİ BAŞARIYLA GEÇTİ!")

if __name__ == "__main__":
    test_auto_discovery()
