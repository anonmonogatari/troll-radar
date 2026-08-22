import re
from typing import Tuple, Optional

# Headline framing patterns specifically engineered for manufactured political smear & outrage
MANUFACTURED_TOPIC_PATTERNS = [
    # Defamation & Corruption Specific Claims
    r'konser\s+(harcama|fatura|vurgun|skandal|para|israf|bütçe)',
    r'roma\s+gezisi\s+(fatura|skandal|şampanya|uçak|maliyet)',
    r'(belediye|ibb|abb)\s+.*(bütçe|vurgun|peşkeş|israf|liyakatsiz|yolsuzluk|konser)',
    r'(ihale|rant|vurgun|hortum|rüşvet)\s+(skandal|ağ|iddia)',
    r'şahsi\s+(reklam|ikbal|servet|uçak|şov)',
    r'terör\s+(iltisak|bağlantı|kadrolaşma)',
    r'gizli\s+(protokol|anlaşma|ortaklık)',
    r'paralar\s+nereye\s+gitti',
    
    # Manufactured Culture War & Lifestyle Outrage
    r'haşemal[ıi]\s+(kadın|teyze|deniz|havuz)',
    r'camiye\s+(bikini|ayakkabı|içki)',
    r'(laik|seküler)\s+(yobaz|faşizm|saldırı|tahammülsüzlük)',
    r'inançlı\s+insanlara\s+(baskı|hakaret|saldırı)',
    r'28\s+şubat\s+(kafa|zihniyet|hortla)',
    
    # Deceptive Spin & Manufactured Defenses
    r'avrupa\'da\s+(daha\s+pahalı|katbekat)',
    r'fırsatçı\s+esnaf',
    r'türkiye\'yi\s+(karalama|çekemeyenler|bölmek)'
]

compiled_manufactured_patterns = [re.compile(p, re.IGNORECASE) for p in MANUFACTURED_TOPIC_PATTERNS]

# Broad/Generic established topics (years old, general public debates - NOT manufactured attack headers)
GENERIC_ESTABLISHED_TOPICS = [
    r'^ekrem imamo[gğ]lu$',
    r'^mansur yava[sş]$',
    r'^recep tayyip erdo[gğ]an$',
    r'^kemal k[ıi]l[ıi][cç]daro[gğ]lu$',
    r'^özgür özel$',
    r'^cumhuriyet halk partisi$',
    r'^adalet ve kalk[ıi]nma partisi$',
    r'^chp$',
    r'^akp$',
    r'^mhp$',
    r'^türkiye ekonomisi$',
    r'^enflasyon$',
    r'^türkiye$',
    r'^istanbul$',
    r'^ankara$',
    r'^izmir$',
    r'^hayat pahal[ıi]l[ıi][gğ][ıi]$',
    r'^asgari ücret$'
]

compiled_generic_patterns = [re.compile(p, re.IGNORECASE) for p in GENERIC_ESTABLISHED_TOPICS]

def is_generic_established_topic(topic_title: str) -> bool:
    """
    Returns True if the topic is a generic, broad, established entity topic
    where thousands of organic users post general commentary.
    """
    if not topic_title:
        return True
    t_clean = topic_title.strip().lower()
    return any(p.match(t_clean) for p in compiled_generic_patterns)

def is_manufactured_troll_topic(topic_title: str, content: str = "") -> Tuple[bool, str]:
    """
    Analyzes whether a newly created topic is a manufactured astroturfing / smear topic.
    Returns: (is_manufactured: bool, detected_cell: str)
    """
    if not topic_title:
        return False, "Bilinmeyen"

    # If it is a generic established entity, it is NOT a manufactured attack topic
    if is_generic_established_topic(topic_title):
        return False, "Genel Başlık (Organik)"

    full_text = f"{topic_title.lower()} {content.lower()}"

    for pattern in compiled_manufactured_patterns:
        if pattern.search(full_text):
            # Classify cell type (short and clean)
            if any(k in full_text for k in ['konser', 'roma', 'belediye', 'ibb', 'abb', 'israf', 'peşkeş', 'vurgun', 'ihale']):
                return True, "Belediye Karalama"
            elif any(k in full_text for k in ['haşema', 'bikini', 'camiye', 'laik yobaz', 'şeriat', '28 şubat']):
                return True, "Kültür Savaşı"
            elif any(k in full_text for k in ['avrupa', 'fırsatçı esnaf', 'pahalılık', 'turist']):
                return True, "Ekonomi Aklama"
            elif any(k in full_text for k in ['terör', 'iltisak', 'protokol', 'gizli']):
                return True, "Yargı / Güvenlik"
            return True, "Algı Operasyonu"

    return False, "Organik"
