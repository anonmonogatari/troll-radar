import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from discovery_engine import TrollDiscoveryEngine

engine = TrollDiscoveryEngine()
results = engine.run_auto_discovery_scan(days=30)
print(f"Total evaluated: {len(results)}\n")
for r in results[:15]:
    m = r['metrics']
    print(f"@{r['nick']:<28} | Troll İndeksi: %{r['troll_score']:<5} [{r['risk_level']:<12}] | Kurgu Başlık: {m['inception_count']} | İlk Dalga: {m['early_swarm_count']}")
