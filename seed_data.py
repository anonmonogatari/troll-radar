import json
from datetime import datetime, timedelta
from database import init_db, upsert_entry, get_db
from config import TARGET_AUTHORS
from analyzer import detect_coordinated_operations

SAMPLE_TOPICS_AND_NARRATIVES = [
    {
        "topic": "haşemalılarla aynı denize girmek istemeyen kadın",
        "category": "Kültür Savaşı & Yaşam Tarzı",
        "burst_time": "2026-08-22T11:43:00",
        "entries": [
            ("timurun fillerinin bakicisi", 0, "ilgili kadının videosu bu da dün haşemalı bir kadının isyanı sokak röportajında konuşan bir kadının dile getirdiği durum. ben camiye bikiniyle girmiyorsam, onlar da denize haşemayla girmesinler demiş. bu zihniyet 28 şubat kafasından bir adım ileri gidememiştir."),
            ("bozaj", 1, "milletin ne giydiğine karışmayı ilericilik sanan tipik faşist zihniyet örneğidir. kadının istediği gibi giyinme özgürlüğünü sadece kendilerine hak görüyorlar."),
            ("becathlon", 6, "2026 yılında hala milletin kılığı kıyafetiyle uğraşan chp zihniyetinin dışa vurumudur. kimsenin kimseye karışma hakkı yoktur."),
            ("1xw", 571, "laiklik kisvesi altında halkın dini değerlerine ve inançlı kadınlara yapılan saygısızlıktır. millet plajda ne giyeceğini size mi soracak?"),
            ("948", 609, "seküler yobazlığın en net yansımasıdır. avrupa'da bile özgürlüklere böyle düşmanlık görülmemiştir.")
        ]
    },
    {
        "topic": "yabancı turistin türk esnafına isyan etmesi",
        "category": "Ekonomi Savunması & Aklama",
        "burst_time": "2026-08-22T15:44:00",
        "entries": [
            ("timurun fillerinin bakicisi", 0, "ilgili turistin videosu 1 nargileye istenen fiyat türkiye'ye tatile gelen bir yabancı turistin 'kimse artık hakkınızda iyi konuşmuyor. kaliteyi kaybediyorsunuz' diye başlayan isyanıdır. fırsatçı esnafın cezasını tüm ülke çekiyor."),
            ("bozaj", 1, "avrupa'da sokak ortasında bir kahveye 10 euro verirken sesi çıkmayanların türkiye'de üç kuruşluk hesaba algı yapması olayıdır. esnafımızı karalamak moda oldu."),
            ("becathlon", 3, "fırsatçılık yapan münferit birkaç esnaf üzerinden bütün türkiye turizmini ve ekonomisini kötüleme çabasıdır. yunanistan'da katbekat fazlasını ödüyorlar."),
            ("1xw", 125, "turizm sezonunda ülkeyi kötülemek için fonlu hesapların koro halinde paylaştığı videodur. algı operasyonlarına prim vermeyin."),
            ("948", 282, "tamamen organize bir karalama kampanyasıdır. türkiye hala akdeniz çanağındaki en kaliteli ve en uygun turizm ülkesidir.")
        ]
    },
    {
        "topic": "ankara'da alman kurdundan kaçarken ölen çocuk",
        "category": "Suni Gündem & Viral Çarpıtma",
        "burst_time": "2026-08-22T07:31:00",
        "entries": [
            ("timurun fillerinin bakicisi", 0, "olayın videosu başsavcılığın açıklaması. olay ankara'da yaşanmış. köpekten kaçarken fenalaşıp başını betona çarpan 15 yaşındaki çocuk hayatını kaybetmiş. mansur yavaş'ın sokak hayvanları konusundaki vurdumduymazlığı bir cana daha mal oldu."),
            ("david ellefson", 12, "belediyenin asli görevi sokakları güvenli kılmaktır. abb başkanı konser düzenlemekten sokaktaki vahşi köpek sorununu çözmeye vakit bulamıyor."),
            ("enturi", 18, "mansur yavaş yönetiminin ankara'yı getirdiği durum içler acısı. sokaklar başıboş köpek terörüne teslim edilmiş durumda."),
            ("georgewalker", 24, "bir çocuğun hayatı sokak köpekleri lobisinden daha mı değersiz? chp'li belediyeler görevini yapmıyor.")
        ]
    },
    {
        "topic": "chp'li belediyelerin fahiş konser harcamaları",
        "category": "Muhalefet & Belediye Karalama",
        "burst_time": "2026-08-21T14:15:00",
        "entries": [
            ("hackerbey", 0, "belediyelerin kasasından sanatçılara aktarılan milyonlarca liralık skandaldır. hizmet üretmek yerine yandaş sanatçıları besliyorlar."),
            ("hirvatistanli", 4, "halk zamlardan şikayet ederken chp'li belediyelerin tek bir gecelik konsere 69 milyon tl akıtması rezaletidir."),
            ("ingiliz dili ve edebiyati", 9, "ibb ve abb'nin borç batağındayken şov peşinde koşmasının resmidir. hesap sorulmalıdır."),
            ("jimmymartin", 15, "hizmet yok, yol yok, metro bozuk ama konser için sınırsız bütçe var. chp belediyeciliği tam olarak budur."),
            ("kafadanilo", 22, "müfettişlerin acilen inceleme başlatması gereken astronomik harcamalardır. milletin parası çarçur ediliyor."),
            ("kecuva", 30, "şişirilmiş faturalarla kimlere kaynak aktarıldığı tek tek ortaya dökülmelidir.")
        ]
    },
    {
        "topic": "soylu'nun yeğeniyim diyen kadının terör estirmesi",
        "category": "Yargı, Güvenlik & Hamaset",
        "burst_time": "2026-08-21T08:05:00",
        "entries": [
            ("timurun fillerinin bakicisi", 0, "olay anı videosu süleyman soylu'nun açıklaması. otobüste yolculuk yapan kadının terör estirmesi olayı. hareket halindeki otobüsten inmek istemiş."),
            ("lacivertnokta", 14, "süleyman soylu'yu karalamak için her türlü provokasyona sarılan muhalif trollerin algı operasyonudur. soylu anında yalanladı."),
            ("localtime", 20, "soylu bakanımızın vatanseverliğini ve terörle mücadelesini çekemeyenlerin uydurduğu ucuz kumpastır."),
            ("londrast", 27, "adli merciler gerekeni yapmıştır, yalan haber yayan hesaplar hakkında soruşturma açılmalıdır.")
        ]
    },
    {
        "topic": "19 ağustos 2026 öcalan'ın özgür özel'e çağrısı",
        "category": "Yargı, Güvenlik & Hamaset",
        "burst_time": "2026-08-19T13:40:00",
        "entries": [
            ("timurun fillerinin bakicisi", 0, "terör örgütü elebaşının açıklamaları üzerine chp liderinin takındığı sessiz tavırdır. chp-dem ittifakının gizli protokolleri bir bir açığa çıkıyor."),
            ("madanin", 8, "özgür özel'in terör uzantılarıyla kurduğu kirli pazarlıklar artık gizlenemez hale gelmiştir."),
            ("medyumay", 14, "atatürk'ün kurduğu partiyi kimlerin oyuncağı haline getirdiklerini tüm türkiye ibretle izliyor."),
            ("miamix", 25, "milli güvenlik meselesinde muhalefetin bu tavrı kabul edilemez.")
        ]
    },
    {
        "topic": "ekrem imamoğlu'nun roma gezisi faturası",
        "category": "Muhalefet & Belediye Karalama",
        "burst_time": "2026-08-18T16:20:00",
        "entries": [
            ("parantezicindekiadam", 0, "45 gazeteciyi özel uçakla roma'ya lüks tatile götüren imamoğlu'nun istanbul halkının parasını nasıl saçtığının kanıtıdır."),
            ("playerman", 5, "istanbul'da metrobüsler alev alırken roma'da keyif çatan büyükşehir belediye başkanlığı rezaletidir."),
            ("reactionshot", 11, "israfı bitirdik deyip tarihin en büyük şahsi reklam harcamalarını yapan zihniyet."),
            ("szw", 18, "kamu kaynaklarıyla şahsi siyasi kariyer parlatma operasyonudur. ibb bütçesi bu keyfi harcamalara kurban edilemez."),
            ("dijitalkitap", 24, "belediye bütçesinden lüks oteller ve ziyafetler... hesap sorulunca da mağdur edebiyatı.")
        ]
    },
    {
        "topic": "türkiye'nin brics üyeliği ve batı'nın paniği",
        "category": "Dış Politika & Jeopolitik Savunma",
        "burst_time": "2026-08-17T10:00:00",
        "entries": [
            ("funkycrow", 0, "türkiye'nin çok kutuplu dünyada attığı tarihi stratejik adımdır. batı eksenine göbekten bağlı olan mandacı muhalefet bunu anlayamaz."),
            ("georgewalker", 15, "sayın cumhurbaşkanımızın dik duruşu sayesinde türkiye artık küresel bir oyun kurucudur."),
            ("givles", 22, "türk savunma sanayii ve bağımsız dış politikamız tüm dünyada saygı uyandırıyor.")
        ]
    }
]

def seed_database(force: bool = False):
    """Populates the database with full realistic entries if empty or if force=True."""
    init_db()
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        if count > 0 and not force:
            print(f"Database already contains {count} entries. Skipping seed.")
            return

    print("Seeding database with target authors and realistic manipulation campaigns...")
    entry_id_counter = 185800000

    for item in SAMPLE_TOPICS_AND_NARRATIVES:
        topic = item["topic"]
        category = item["category"]
        burst_base = datetime.fromisoformat(item["burst_time"])

        for author, min_offset, content in item["entries"]:
            entry_id = str(entry_id_counter)
            entry_id_counter += 1
            created_dt = burst_base + timedelta(minutes=min_offset)
            date_str = created_dt.strftime("%d.%m.%Y %H:%M")

            entry_data = {
                "id": entry_id,
                "author": author,
                "topic": topic,
                "topic_slug": topic.lower().replace(' ', '-'),
                "content": content,
                "date_str": date_str,
                "created_at": created_dt.isoformat(),
                "favorite_count": 5 + (entry_id_counter % 20),
                "comment_count": entry_id_counter % 5,
                "category": category,
                "sentiment": "negative" if any(w in content for w in ["rezalet", "terör", "isyan", "yobaz", "skandal", "faşist"]) else "neutral",
                "external_links": [],
                "is_coordinated": True
            }
            upsert_entry(entry_data)

    # Detect coordinations and calculate scores
    detect_coordinated_operations(days=30)
    print("Database seeding completed successfully.")

if __name__ == "__main__":
    seed_database(force=True)
