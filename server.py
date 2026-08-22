import uuid
import json
import asyncio
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, BackgroundTasks, Query, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path

from config import TARGET_AUTHORS, BASE_DIR
from database import (
    init_db, get_db, get_entries, get_all_authors_summary, get_overview_stats
)
from analyzer import (
    detect_coordinated_operations, get_coordination_network_data,
    get_posting_heatmap_data, get_top_manipulation_narratives,
    extract_top_keywords
)
from scraper import EksiScraper
from seed_data import seed_database

app = FastAPI(
    title="Ekşi Sözlük Manipülasyon & Troll Radar",
    description="27 Hedef Yazarın Koordineli Algı Operasyonları Analiz Platformu",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active scraping jobs tracker
ACTIVE_JOBS = {}

@app.on_event("startup")
def on_startup():
    init_db()
    # Check if empty, seed initial data
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        if count == 0:
            seed_database(force=True)

# Static files mount
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def read_root():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse({"message": "TrollRadar API running. Please load frontend."})

# ----------------- API ENDPOINTS ----------------- #

@app.get("/api/stats")
def get_stats(days: int = 7):
    """Returns overview KPI metrics, category breakdowns, and daily trendline."""
    return get_overview_stats(days=days)

@app.get("/api/narratives")
def get_narratives(days: int = 7):
    """Returns the Executive Manipulation Briefing with clustered topics and evidence entries."""
    briefing = get_top_manipulation_narratives(days=days)
    return {"period_days": days, "narratives": briefing}

@app.get("/api/entries")
def get_entry_list(
    days: int = 7,
    author: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    coordinated_only: bool = False,
    limit: int = 50,
    offset: int = 0
):
    """Returns filtered entries."""
    return get_entries(
        days=days,
        author=author,
        category=category,
        search=search,
        coordinated_only=coordinated_only,
        limit=limit,
        offset=offset
    )

@app.get("/api/authors")
def get_authors(days: int = 7):
    """Returns statistics and risk scores for all 27 target accounts."""
    authors = get_all_authors_summary(days=days)
    return {"total": len(authors), "authors": authors}

@app.get("/api/coordination")
def get_coordination(days: int = 7):
    """Returns network graph nodes/edges and list of coordinated operations."""
    network = get_coordination_network_data(days=days)
    with get_db() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT * FROM coordinations
            ORDER BY timestamp DESC
            LIMIT 50
        """).fetchall()
        coordinations = []
        for r in rows:
            d = dict(r)
            try:
                d['authors_involved'] = json.loads(d['authors_involved'])
                d['entry_ids'] = json.loads(d['entry_ids'])
            except Exception:
                pass
            coordinations.append(d)

    return {"network": network, "coordinations": coordinations}

@app.get("/api/heatmap")
def get_heatmap(days: int = 7):
    """Returns day x hour posting schedule heatmap data."""
    return {"heatmap": get_posting_heatmap_data(days=days)}

@app.get("/api/keywords")
def get_keywords(days: int = 7, limit: int = 30):
    """Returns top keywords across entries."""
    return {"keywords": extract_top_keywords(days=days, top_n=limit)}

# ----------------- BACKGROUND SCRAPING ----------------- #

def background_scraper_task(job_id: str, authors: List[str], days: int, domain: Optional[str]):
    scraper = EksiScraper(domain=domain)
    
    def on_progress(data):
        ACTIVE_JOBS[job_id] = {**ACTIVE_JOBS.get(job_id, {}), **data}

    ACTIVE_JOBS[job_id] = {
        "job_id": job_id,
        "status": "running",
        "processed": 0,
        "total": len(authors),
        "current": "Başlatılıyor...",
        "entries": 0
    }
    
    try:
        result = scraper.run_full_scan(job_id=job_id, authors=authors, lookback_days=days, callback=on_progress)
        ACTIVE_JOBS[job_id]["status"] = "completed"
    except Exception as e:
        ACTIVE_JOBS[job_id]["status"] = "failed"
        ACTIVE_JOBS[job_id]["error"] = str(e)

@app.post("/api/scrape/start")
def start_scrape(
    background_tasks: BackgroundTasks,
    days: int = 7,
    author: Optional[str] = None,
    domain: Optional[str] = None
):
    """Starts asynchronous scraping job."""
    job_id = str(uuid.uuid4())
    authors_to_scrape = [author] if author else TARGET_AUTHORS

    background_tasks.add_task(background_scraper_task, job_id, authors_to_scrape, days, domain)

    return {
        "job_id": job_id,
        "status": "started",
        "target_authors_count": len(authors_to_scrape),
        "lookback_days": days
    }

@app.get("/api/scrape/status/{job_id}")
def get_scrape_status(job_id: str):
    """Returns live scraping progress and logs."""
    if job_id in ACTIVE_JOBS:
        return ACTIVE_JOBS[job_id]
    
    # Fallback to DB
    with get_db() as conn:
        cursor = conn.cursor()
        job = cursor.execute("SELECT * FROM scrape_jobs WHERE id = ?", (job_id,)).fetchone()
        if job:
            d = dict(job)
            try:
                d['logs'] = json.loads(d.get('logs', '[]'))
            except Exception:
                d['logs'] = []
            return d

    return {"status": "not_found", "job_id": job_id}

@app.get("/api/export")
def export_data(format: str = "json", days: int = 7):
    """Exports entries as JSON or CSV."""
    data = get_entries(days=days, limit=5000)
    entries = data.get("entries", [])
    
    if format.lower() == "csv":
        import io
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Yazar", "Başlık", "Kategori", "Tarih", "Koordineli", "Metin"])
        for e in entries:
            writer.writerow([
                e['id'], e['author'], e['topic'], e['category'],
                e['created_at'], 'Evet' if e['is_coordinated'] else 'Hayır',
                e['content'].replace('\n', ' ')
            ])
        response = Response(content=output.getvalue(), media_type="text/csv")
        response.headers["Content-Disposition"] = f"attachment; filename=troll_radar_export_{datetime.now().strftime('%Y%m%d')}.csv"
        return response
    
    return JSONResponse(entries)
