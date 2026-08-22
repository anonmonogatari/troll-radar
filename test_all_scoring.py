import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from database import get_db
from manufactured_topic_detector import is_manufactured_troll_topic
from collections import defaultdict, Counter

with get_db() as conn:
    cursor = conn.cursor()
    all_entries = [dict(r) for r in cursor.execute("SELECT * FROM entries").fetchall()]

topic_map = defaultdict(list)
for e in all_entries:
    topic_map[e['topic']].append(e)

entries_by_author = defaultdict(list)
for e in all_entries:
    entries_by_author[e['author']].append(e)

print(f"Total authors in database: {len(entries_by_author)}")

for nick, entries in sorted(entries_by_author.items(), key=lambda x: len(x[1]), reverse=True):
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
            
    # Calculate scores
    incept_pts = min(100.0, inception_count * 50.0)
    swarm_pts = min(100.0, early_swarm_count * 25.0)
    coord_pts = min(100.0, coord_count * 20.0)
    
    # Brigading
    favs = [e['favorite_count'] for e in entries if e['favorite_count'] > 0]
    brig_pts = min(100.0, len(favs) * 20.0) if favs else 0.0
    
    if early_swarm_count == 0 and coord_count == 0:
        final_score = 0.0
        status = "Organik (Elendi)"
    else:
        raw = (incept_pts * 0.35) + (swarm_pts * 0.25) + (coord_pts * 0.25) + (brig_pts * 0.15)
        final_score = round(min(100.0, raw), 1)
        if final_score >= 70: status = "Kesin Troll"
        elif final_score >= 50: status = "İlk Dalga"
        elif final_score >= 30: status = "Şüpheli"
        else: status = "Organik"
        
    if final_score > 0:
        print(f"@{nick:<28} | Skor: %{final_score:<5} [{status:<12}] | Incept:{inception_count} | Swarm:{early_swarm_count} | Coord:{coord_count}")
