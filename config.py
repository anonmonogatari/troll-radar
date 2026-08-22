import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "troll_radar.db"

# The 27 target authors provided by the user
TARGET_AUTHORS = [
    "timurun fillerinin bakicisi",
    "948",
    "1xw",
    "becathlon",
    "bozaj",
    "david ellefson",
    "dijitalkitap",
    "enturi",
    "funkycrow",
    "georgewalker",
    "givles",
    "hackerbey",
    "hirvatistanli",
    "ingiliz dili ve edebiyati",
    "jimmymartin",
    "kafadanilo",
    "kecuva",
    "lacivertnokta",
    "localtime",
    "londrast",
    "madanin",
    "medyumay",
    "miamix",
    "parantezicindekiadam",
    "playerman",
    "reactionshot",
    "szw"
]

# Primary manipulation categories & detection keywords
NARRATIVE_CATEGORIES = {
    "Kültür Savaşı & Yaşam Tarzı": {
        "color": "#ef4444", # Red
        "icon": "flame",
        "keywords": ["haşema", "bikini", "şeriat", "seküler", "cami", "alkol", "deniz", "edep", "ahlak", "çarşaf", "tesettür", "kadın", "laik", "seviş"]
    },
    "Muhalefet & Belediye Karalama": {
        "color": "#f97316", # Orange
        "icon": "target",
        "keywords": ["chp", "imamoğlu", "özel", "özgür özel", "belediye", "konser", "ibb", "abb", "yavaş", "mansur", "dem", "kayyum", "yolsuzluk", "heykel", "otobüs"]
    },
    "Ekonomi Savunması & Aklama": {
        "color": "#eab308", # Yellow
        "icon": "trending-up",
        "keywords": ["enflasyon", "turist", "fiyat", "pahalı", "nargile", "avrupa", "almanya", "şükür", "esnaf", "market", "fırsatçı", "ekonomi", "maaş", "asgari"]
    },
    "Yargı, Güvenlik & Hamaset": {
        "color": "#3b82f6", # Blue
        "icon": "shield-alert",
        "keywords": ["öcalan", "terör", "kuytul", "gözaltı", "savcı", "hakim", "soylu", "süleyman soylu", "polis", "tutuklama", "mahkeme", "vatan", "hain", "operasyon"]
    },
    "Suni Gündem & Viral Çarpıtma": {
        "color": "#a855f7", # Purple
        "icon": "sparkles",
        "keywords": ["köpek", "alman kurdu", "sokak köpeği", "kedi", "tiktok", "fenomen", "video", "skandal", "rezalet", "otobüs", "dehşet", "kavga", "çift"]
    },
    "Dış Politika & Jeopolitik Savunma": {
        "color": "#06b6d4", # Cyan
        "icon": "globe",
        "keywords": ["israil", "gazze", "abd", "nato", "yunanistan", "suriye", "brics", "bayraktar", "kağan", "togg", "savunma"]
    }
}

# Stopwords for Turkish NLP
TURKISH_STOPWORDS = set([
    "ve", "veya", "ile", "de", "da", "ki", "bir", "bu", "şu", "o", "için", "gibi", "kadar",
    "daha", "çok", "en", "ama", "fakat", "lakin", "çünkü", "ise", "diye", "olan", "olarak",
    "her", "hiç", "ne", "ya", "hem", "mi", "mı", "mu", "mü", "bunu", "buna", "bunun", "şunu",
    "onun", "onu", "ona", "ben", "sen", "biz", "siz", "onlar", "tarafından", "şeklinde",
    "üzere", "sonra", "önce", "kendi", "aynı", "tüm", "bazı", "göre", "eden", "edilen",
    "ancak", "zaten", "artık", "şey", "diğer", "yine", "böyle", "şöyle", "öyle", "bile",
    "var", "yok", "vs", "vb", "yani", "oldu", "olmuş", "olacak", "etti", "ettiği", "yapan"
])

SCRAPER_CONFIG = {
    "default_domain": "eksisozluk.com",
    "mirror_domains": ["eksisozluk.com", "eksisozluk111.com", "eksisozluk1923.com"],
    "request_delay_min": 0.4,
    "request_delay_max": 1.0,
    "timeout": 10,
    "max_pages_per_author": 5,
    "default_days_lookback": 7
}
