import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from database import get_db
from config import TARGET_AUTHORS
from manufactured_topic_detector import is_manufactured_troll_topic
from collections import defaultdict

with get_db() as conn:
    cursor = conn.cursor()
    all_entries = [dict(r) for r in cursor.execute("SELECT * FROM entries").fetchall()]

topic_map = defaultdict(list)
for e in all_entries:
    topic_map[e['topic']].append(e)

entries_by_author = defaultdict(list)
for e in all_entries:
    entries_by_author[e['author']].append(e)

print(f"{'Yazar':<30} | {'Skor':<6} | {'Durum':<12} | Incept | Swarm | Coord | Total")
print("-" * 80)

for nick in TARGET_AUTHORS:
    entries = entries_by_author.get(nick, [])
    if not entries:
        continue
        
    inception_count = 0
    early_swarm_count = 0
    coord_count = sum(1 for e in entries if e['is_coordinated'])
    
    for e in entries:
        topic = e['topic']
        is_m, cell = is_manufactured_troll_topic(topic, e.get('content', ''))
        if not is_m:
            continue
        
        t_entries = topic_map.get(topic, [])
        try:
            rank = next(idx for idx, te in enumerate(t_entries) if te['id'] == e['id'])
        except StopIteration:
            rank = 0
            
        if rank == 0:
            inception_count += 1
            early_swarm_count += 1
        elif rank < 5:
            early_swarm_count += 1
            
    # Concentration & Operational Footprint
    total_e = len(entries)
    incept_scale = min(100.0, inception_count * 50.0)
    swarm_scale = min(100.0, (early_swarm_count / max(1, total_e)) * 100.0)
    coord_scale = min(100.0, (coord_count / max(1, total_e)) * 100.0)
    
    # Absolute presence boost (ring leader vs cell foot-soldier)
    volume_boost = min(30.0, coord_count * 5.0 + inception_count * 10.0)
    
    favs = [e['favorite_count'] for e in entries if e['favorite_count'] > 0]
    brig_pts = min(100.0, (len(favs) / max(1, total_e)) * 100.0) if favs else 0.0
    
    if early_swarm_count == 0 and coord_count == 0:
        final_score = 0.0
        status = "Organik (Elendi)"
    else:
        # Base on manufactured topic infiltration ratio & coordination
        raw = (incept_scale * 0.30) + (swarm_scale * 0.30) + (coord_scale * 0.25) + (brig_pts * 0.15)
        # Cap and scale with volume
        final_score = round(max(0.0, min(100.0, raw + (volume_boost if inception_count > 1 or coord_count > 3 else 0.0))), 1)
        
        if final_score >= 70: status = "Kesin Troll"
        elif final_score >= 50: status = "İlk Dalga"
        elif final_score >= 30: status = "Şüpheli"
        else: status = "Organik"
        
    print(f"@{nick:<29} | %{final_score:<5} | {status:<12} | {inception_count:<6} | {early_swarm_count:<5} | {coord_count:<5} | {len(entries)}")
