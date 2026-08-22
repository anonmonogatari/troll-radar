import uvicorn
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from database import init_db
from seed_data import seed_database

def main():
    print("=========================================================")
    print("  TrollRadar // Ekşi Sözlük Manipülasyon Analiz Sistemi  ")
    print("=========================================================")
    
    # Initialize DB & Seed data if necessary
    init_db()
    seed_database()
    
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    
    print(f"\n[+] Web Platformu Hazır: http://localhost:{port}")
    print(f"[+] 27 Hedef Yazar İzleniyor.")
    print(f"[+] Sunucu Başlatılıyor...\n")
    
    uvicorn.run("server:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    main()
