import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from manufactured_topic_detector import is_manufactured_troll_topic, is_generic_established_topic
from discovery_engine import TrollDiscoveryEngine

def test_manufactured_topic_system():
    print("=================================================================")
    print("🎯 Kurgu Başlık Açma & İlk Dalga (#1-#5) Tespit Testleri Başladı")
    print("=================================================================\n")

    # 1. TEST GENERIC VS MANUFACTURED TOPICS
    print("[1] Genel Başlık vs. Kurgu Karalama Başlığı Ayrımı...")
    generic_samples = ["ekrem imamoğlu", "mansur yavaş", "chp", "akp", "türkiye ekonomisi", "enflasyon"]
    for gt in generic_samples:
        assert is_generic_established_topic(gt) == True, f"Genel başlık tanınamadı: {gt}"
        is_manuf, _ = is_manufactured_troll_topic(gt)
        assert is_manuf == False, f"Genel başlık yanlışlıkla kurgu sayıldı: {gt}"
    print("  -> Genel/eski başlıklar başarıyla izole edildi (Organik tartışma alanı).")

    manufactured_samples = [
        "chp belediyelerinin konser harcamaları",
        "ekrem imamoğlu roma gezisi faturası",
        "haşemalı kadınların denize sokulmaması skandalı",
        "belediye bütçesinden şahsi reklam vurgunu"
    ]
    for mt in manufactured_samples:
        is_manuf, cell = is_manufactured_troll_topic(mt)
        assert is_manuf == True, f"Kurgu başlık tespit edilemedi: {mt}"
        print(f"  -> Kurgu Başlık Yakalandı: '{mt}' -> Hücre: {cell}")

    # 2. TEST GENERIC TOPIC POSTER (Score MUST be 0)
    print("\n[2] Genel Başlığa Yazan Organik Yazarın Elenmesi Testi...")
    engine = TrollDiscoveryEngine()
    
    generic_entry = {
        "id": "gen_1",
        "author": "organik_vatandas",
        "topic": "ekrem imamoğlu",
        "content": "bence son dönem açıklamaları siyasette etkili oldu.",
        "favorite_count": 25,
        "created_at": "2026-08-22T12:00:00"
    }
    topic_timeline = {"ekrem imamoğlu": [generic_entry]}
    eval_generic = engine.evaluate_author_on_manufactured_topics("organik_vatandas", [generic_entry], [generic_entry], topic_timeline)
    assert eval_generic['troll_score'] == 0.0, f"Genel başlığa yazan hesaba troll skoru verildi: {eval_generic['troll_score']}"
    print("  -> Genel başlığa yazan yazar başarıyla elendi (Troll Skoru = %0.0).")

    # 3. TEST MANUFACTURED TOPIC INITIATOR & EARLY SWARM (Score MUST be >= 80)
    print("\n[3] Kurgu Başlık Açan (Entry #1) ve İlk Dalga (#1-#5) Trollü Testi...")
    troll_topic = "chp belediyelerinin konser harcamaları"
    
    # Simulate first 3 entries created within 10 minutes
    opener_entry = {
        "id": "troll_opener",
        "author": "kurgucu_troll",
        "topic": troll_topic,
        "content": "halkın parasıyla milyonluk konser vurgunu yapıyorlar, liyakatsiz yandaşlara peşkeş çekiliyor.",
        "favorite_count": 15,
        "created_at": "2026-08-22T14:00:00"
    }
    swarm_entry = {
        "id": "troll_swarmer",
        "author": "kopurtucu_troll",
        "topic": troll_topic,
        "content": "şahsi ikbal için belediye bütçesini hortumlayanların rezaleti.",
        "favorite_count": 12,
        "created_at": "2026-08-22T14:03:00"
    }
    
    topic_map = {troll_topic: [opener_entry, swarm_entry]}
    all_mock = [opener_entry, swarm_entry]

    eval_opener = engine.evaluate_author_on_manufactured_topics("kurgucu_troll", [opener_entry], all_mock, topic_map)
    assert eval_opener['troll_score'] >= 80.0, f"Kurgu başlık açan troll hak ettiği skoru alamadı: {eval_opener['troll_score']}"
    print(f"  -> Kurgu Başlık Açan Troll Tespiti: Skor = %{eval_opener['troll_score']} [{eval_opener['risk_level']}]")

    eval_swarmer = engine.evaluate_author_on_manufactured_topics("kopurtucu_troll", [swarm_entry], all_mock, topic_map)
    assert eval_swarmer['troll_score'] >= 50.0, f"İlk dalga köpürtücü troll skoru yetersiz: {eval_swarmer['troll_score']}"
    print(f"  -> İlk Dalga Köpürtücü Swarm Tespiti: Skor = %{eval_swarmer['troll_score']} [{eval_swarmer['risk_level']}]")

    # 4. TEST FULL DISCOVERY SCAN ON DB
    print("\n[4] Canlı Veritabanı Kurgu Başlık Taraması...")
    results = engine.run_auto_discovery_scan(days=30)
    print(f"  -> Değerlendirilen Hedef Yazar: {len(results)}")
    top_trolls = [r for r in results if r['troll_score'] >= 70]
    print(f"  -> Yakalanan Kesin Kurgu Başlık Trolleri: {len(top_trolls)} adet")
    for t in top_trolls[:3]:
        m = t['metrics']
        print(f"     @{t['nick']}: Skor=%{t['troll_score']} -> Kurgu Başlık={m['inception_count']}, İlk Dalga={m['early_swarm_count']}, Beğeni Halkası=%{m['vote_brigading']}")

    print("\n=================================================================")
    print("✅ TÜM KURGU BAŞLIK VE İLK DALGA TESTLERİ %100 BAŞARIYLA GEÇTİ!")
    print("=================================================================")

if __name__ == "__main__":
    test_manufactured_topic_system()
