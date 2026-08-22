import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from manufactured_topic_detector import is_manufactured_troll_topic
from database import get_db

with get_db() as conn:
    cursor = conn.cursor()
    entries = [dict(r) for r in cursor.execute("SELECT * FROM entries WHERE author = 'timurun fillerinin bakicisi'").fetchall()]

print(f"Testing enhanced topic framing on {len(entries)} entries...")
for e in entries:
    topic = e['topic']
    is_m, cell = is_manufactured_troll_topic(topic, e.get('content', ''))
    print(f"- '{topic}' -> is_m={is_m} ({cell})")
