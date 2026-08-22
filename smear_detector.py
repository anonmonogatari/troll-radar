import re
from typing import List, Dict, Any, Tuple
from collections import defaultdict

# Smear & Defamation Lexicon (İftira ve Karalama Göstergeleri)
SMEAR_KEYWORDS = [
    'yolsuzluk', 'vurgun', 'peşkeş', 'roma faturası', 'konser skandalı', 'israf',
    'halkın parası', 'şahsi reklam', 'şahsi ikbal', 'terör iltisakı', 'fonlu', 'yandaş',
    'ajan', 'ihanet', 'liyakatsiz', 'belediye bütçesi', 'şaibe', 'skandal', 'rezalet',
    'rant', 'hortum', 'hırsızlık', 'yalan', 'sahte', 'tarihin en büyük', 'faşist', 'yobaz'
]

# Deceptive Spin & White-washing Lexicon (Aklama ve Çarpıtma Göstergeleri)
SPIN_KEYWORDS = [
    'avrupa\'da daha pahalı', 'yunanistan\'da katbekat', 'fırsatçı esnaf', '28 şubat zihniyeti',
    'şükür', 'şükürsüz', 'münferit olay', 'algı operasyonu', 'kurgu video', 'provokasyon',
    'kumpas', 'çekemeyenler', 'karalama kampanyası', 'büyük oyun', 'dik duruş', 'tarihi başarı',
    'küresel güç', 'koro halinde', 'fonlanan hesaplar'
]

# Culture War & Manufactured Polarization Lexicon (Suni Kutuplaştırma)
CULTURE_WAR_KEYWORDS = [
    'haşema', 'bikini', 'camiye bikiniyle', 'laik yobaz', 'şeriat', 'edep',
    'ahlak', 'çarşaf', 'tesettür düşmanlığı', 'inançlı insanlara', 'din düşmanlığı',
    'seküler faşizm', 'sokakta sevişen', 'köpek terörü'
]

ALL_MANIPULATION_KEYWORDS = set(SMEAR_KEYWORDS + SPIN_KEYWORDS + CULTURE_WAR_KEYWORDS)

def detect_entry_stance(topic: str, content: str) -> Dict[str, Any]:
    """
    Analyzes an entry to detect its stance:
    - 'smear': Karalama / İftira odaklı
    - 'spin': Aklama / Savunma odaklı
    - 'culture_war': Suni Kutuplaştırma odaklı
    - 'neutral': Doğal / Nötr içerik
    """
    text = f"{topic.lower()} {content.lower()}"
    
    smear_count = sum(text.count(kw) for kw in SMEAR_KEYWORDS)
    spin_count = sum(text.count(kw) for kw in SPIN_KEYWORDS)
    cw_count = sum(text.count(kw) for kw in CULTURE_WAR_KEYWORDS)

    total_hits = smear_count + spin_count + cw_count
    
    if total_hits == 0:
        return {"stance": "neutral", "intensity": 0, "smear_hits": 0, "spin_hits": 0, "cw_hits": 0}

    primary_stance = "smear"
    if spin_count > smear_count and spin_count > cw_count:
        primary_stance = "spin"
    elif cw_count > smear_count and cw_count > spin_count:
        primary_stance = "culture_war"

    return {
        "stance": primary_stance,
        "intensity": total_hits,
        "smear_hits": smear_count,
        "spin_hits": spin_count,
        "cw_hits": cw_count
    }

def calculate_smear_intensity_ratio(author_entries: List[Dict[str, Any]]) -> float:
    """
    Calculates the proportion of an author's entries that exhibit active smear, deceptive spin, or culture-war tactics.
    """
    if not author_entries:
        return 0.0

    manipulation_entries = 0
    for e in author_entries:
        analysis = detect_entry_stance(e['topic'], e['content'])
        if analysis['stance'] != 'neutral' or analysis['intensity'] > 0:
            manipulation_entries += 1

    return round((manipulation_entries / len(author_entries)) * 100, 1)

def calculate_narrative_alignment(author_entries: List[Dict[str, Any]], all_entries: List[Dict[str, Any]]) -> float:
    """
    Measures if this author writes with the SAME political talking points and attack stance
    as other suspected actors on the same topics.
    If two authors argue opposite views on a topic, their alignment is 0 (Organic debate).
    """
    if not author_entries or not all_entries:
        return 0.0

    author_entry_ids = set(e['id'] for e in author_entries)
    other_entries_by_topic = defaultdict(list)
    
    for e in all_entries:
        if e['id'] not in author_entry_ids:
            other_entries_by_topic[e['topic']].append(e)

    aligned_topics_count = 0
    total_shared_topics = 0

    for e in author_entries:
        topic = e['topic']
        if topic not in other_entries_by_topic:
            continue

        total_shared_topics += 1
        my_stance = detect_entry_stance(e['topic'], e['content'])
        
        if my_stance['stance'] == 'neutral':
            continue

        # Check stances of other authors on this topic
        for other_e in other_entries_by_topic[topic]:
            other_stance = detect_entry_stance(other_e['topic'], other_e['content'])
            # If both are attacking or both are spinning with same narrative stance
            if my_stance['stance'] == other_stance['stance'] and other_stance['stance'] != 'neutral':
                aligned_topics_count += 1
                break

    if total_shared_topics == 0:
        return 0.0

    return round((aligned_topics_count / total_shared_topics) * 100, 1)

def calculate_vote_brigading_score(author_entries: List[Dict[str, Any]]) -> float:
    """
    Measures vote-brigading / favoriting ring behavior:
    Trolls artificially boost each other's smear entries into 'Şükela/Debe'.
    High favorited counts strictly on smear/polarization topics indicates organized boost ring.
    """
    if not author_entries:
        return 0.0

    manipulation_favs = []
    normal_favs = []

    for e in author_entries:
        fav_count = int(e.get('favorite_count', 0) or 0)
        stance = detect_entry_stance(e['topic'], e['content'])
        if stance['stance'] != 'neutral':
            manipulation_favs.append(fav_count)
        else:
            normal_favs.append(fav_count)

    if not manipulation_favs or sum(manipulation_favs) == 0:
        return 0.0

    avg_manipulation_fav = sum(manipulation_favs) / len(manipulation_favs)
    
    # If manipulation entries consistently receive organized favoriting in ring
    if avg_manipulation_fav >= 15:
        return 95.0
    elif avg_manipulation_fav >= 8:
        return 80.0
    elif avg_manipulation_fav >= 4:
        return 65.0
    elif avg_manipulation_fav >= 1:
        return 50.0
    return 0.0
