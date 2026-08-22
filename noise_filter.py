import re
from typing import Optional

# Keywords that indicate pure sports, matches, entertainment, gaming, or casual trivia
SPORTS_AND_ENTERTAINMENT_BLACKLIST = [
    # Football & Sports
    r'\bmaçı\b', r'\bmaç\b', r'\bderbi\b', r'\bfenerbahçe\b', r'\bgalatasaray\b', r'\bbeşiktaş\b',
    r'\btrabzonspor\b', r'\bsüper lig\b', r'\bşampiyonlar ligi\b', r'\buefa\b', r'\bkonferans ligi\b',
    r'\bhakem\b', r'\bpenaltı\b', r'\bofsayt\b', r'\bkırmızı kart\b', r'\bsarı kart\b',
    r'\btransfer\b', r'\bfutbol\b', r'\bbasketbol\b', r'\bvoleybol\b', r'\beuroleague\b',
    r'\bpremier lig\b', r'\bla liga\b', r'\bserie a\b', r'\bbundesliga\b', r'\bforma\b',
    r'\bgol\b', r'\basist\b', r'\bvardar\b', r'\barda güler\b', r'\bcoutinho\b', r'\bicardi\b',
    r'\bdzeko\b', r'\btadic\b', r'\bokan buruk\b', r'\bferdi kadıoğlu\b', r'\bmourinho\b',
    r'\bformula 1\b', r'\bmotogp\b', r'\bolimpiyat\b',
    
    # Gaming & Tech Casual
    r'\bsteam\b', r'\bplaystation\b', r'\bxbox\b', r'\bvalorant\b', r'\bcs:go\b', r'\bcounter strike\b',
    r'\bleague of legends\b', r'\bgta\b', r'\brdr2\b', r'\bminecraft\b', r'\bpubg\b',
    
    # Series, Movies, Anime & Entertainment
    r'\bdizisi\b', r'\bfilmi\b', r'\banime\b', r'\bmanga\b', r'\bnetflix\b', r'\bdisney\+\b',
    r'\bmarvel\b', r'\bdc comics\b', r'\bgame of thrones\b', r'\bhouse of the dragon\b',
    r'\bbölüm incelemesi\b', r'\bfragman\b', r'\bimdb\b',
    
    # Casual Lifestyle & Astrological
    r'\bburç', r'\bburcu\b', r'\bastroloji', r'\byemek tarifi\b', r'\btarif\b', r'\bparfüm\b'
]

# Political / Municipality / Disinformation Whitelist override
POLITICAL_OVERRIDE_KEYWORDS = [
    'chp', 'akp', 'mhp', 'iyi parti', 'dem parti', 'zafer partisi',
    'imamoğlu', 'yavaş', 'erdoğan', 'özgür özel', 'kılıçdaroğlu', 'soylu',
    'belediye', 'ibb', 'abb', 'konser', 'ihale', 'yolsuzluk', 'kayyum',
    'enflasyon', 'zam', 'dolar', 'asgari ücret', 'faiz', 'mehmet şimşek',
    'terör', 'öcalan', 'pkk', 'fetö', 'israil', 'filistin', 'gazze',
    'haşema', 'bikini', 'şeriat', 'laiklik', 'tarikat', 'cemaat',
    'sokak köpekleri', 'uyutma', 'turist', 'esnaf'
]

compiled_blacklist = [re.compile(pattern, re.IGNORECASE) for pattern in SPORTS_AND_ENTERTAINMENT_BLACKLIST]

def is_noise_topic(topic_title: str, content: Optional[str] = None) -> bool:
    """
    Returns True if topic is pure sports, match banter, casual entertainment, or non-political noise.
    Returns False if it is a political, economic, legal, social polarization or smear topic.
    """
    if not topic_title:
        return True
        
    title_lower = topic_title.lower()
    content_lower = (content or "").lower()
    full_text = f"{title_lower} {content_lower}"

    # If it contains core political / municipal / crisis keywords, do not treat as noise
    if any(pk in full_text for pk in POLITICAL_OVERRIDE_KEYWORDS):
        return False

    # Check blacklist patterns
    for pattern in compiled_blacklist:
        if pattern.search(title_lower):
            return True

    return False
