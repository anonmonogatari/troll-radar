import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from database import get_db
from manufactured_topic_detector import is_manufactured_troll_topic
from discovery_engine import TrollDiscoveryEngine
from collections import defaultdict
import json

with get_db() as conn:
    cursor = conn.cursor()
    all_entries = [dict(r) for r in cursor.execute("SELECT * FROM entries").fetchall()]
    author_entries = [dict(r) for r in cursor.execute("SELECT * FROM entries WHERE author = 'timurun fillerinin bakicisi'").fetchall()]

print(f"Total entries for @timurun fillerinin bakicisi: {len(author_entries)}")

topic_map = defaultdict(list)
for e in all_entries:
    topic_map[e['topic']].append(e)

print("\n--- ENTRIES OF @timurun fillerinin bakicisi ---")
for i, e in enumerate(author_entries):
    topic = e['topic']
    is_manuf, cell = is_manufactured_troll_topic(topic, e.get('content', ''))
    
    # rank in topic
    t_entries = topic_map.get(topic, [])
    try:
        rank = next(idx for idx, te in enumerate(t_entries) if te['id'] == e['id'])
    except StopIteration:
        rank = -1
        
    print(f"[{i+1}] Topic: '{topic}' | is_manuf={is_manuf} ({cell}) | rank={rank} | coord={e['is_coordinated']} | fav={e['favorite_count']}")

engine = TrollDiscoveryEngine()
eval_res = engine.evaluate_author_on_manufactured_topics('timurun fillerinin bakicisi', author_entries, all_entries, topic_map)
print("\n--- EVALUATION RESULT ---")
print(json.dumps(eval_res, indent=2, ensure_ascii=False))
