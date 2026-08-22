import os
import json
import shutil
from pathlib import Path
from datetime import datetime

from config import BASE_DIR, TARGET_AUTHORS
from database import (
    init_db, get_entries, get_all_authors_summary, get_overview_stats, get_db
)
from analyzer import (
    detect_coordinated_operations, get_coordination_network_data,
    get_posting_heatmap_data, get_top_manipulation_narratives, extract_top_keywords
)
from seed_data import seed_database

def export_static_site(output_dir: str = "dist"):
    """
    Exports the entire platform into a standalone static bundle
    suitable for GitHub Pages hosting.
    """
    out_path = BASE_DIR / output_dir
    out_path.mkdir(exist_ok=True)
    
    data_out_path = out_path / "data"
    data_out_path.mkdir(exist_ok=True)

    init_db()
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        if count == 0:
            seed_database(force=True)

    # Detect coordinations
    detect_coordinated_operations(days=30)

    print("[*] Exporting static JSON datasets for GitHub Pages...")

    # 1. Stats
    for days in [1, 3, 7, 30]:
        stats = get_overview_stats(days=days)
        with open(data_out_path / f"stats_{days}.json", "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        narratives = get_top_manipulation_narratives(days=days)
        with open(data_out_path / f"narratives_{days}.json", "w", encoding="utf-8") as f:
            json.dump({"period_days": days, "narratives": narratives}, f, ensure_ascii=False, indent=2)

        authors = get_all_authors_summary(days=days)
        with open(data_out_path / f"authors_{days}.json", "w", encoding="utf-8") as f:
            json.dump({"total": len(authors), "authors": authors}, f, ensure_ascii=False, indent=2)

        network = get_coordination_network_data(days=days)
        with open(data_out_path / f"coordination_{days}.json", "w", encoding="utf-8") as f:
            json.dump({"network": network, "coordinations": []}, f, ensure_ascii=False, indent=2)

        heatmap = get_posting_heatmap_data(days=days)
        with open(data_out_path / f"heatmap_{days}.json", "w", encoding="utf-8") as f:
            json.dump({"heatmap": heatmap}, f, ensure_ascii=False, indent=2)

        from discovery_engine import TrollDiscoveryEngine
        disc_engine = TrollDiscoveryEngine()
        evaluations = disc_engine.run_auto_discovery_scan(days=days)
        cells = disc_engine.cluster_troll_cells(evaluations)
        with open(data_out_path / f"discovery_{days}.json", "w", encoding="utf-8") as f:
            json.dump({
                "total_evaluated": len(evaluations),
                "high_confidence_trolls": len([e for e in evaluations if e['troll_score'] >= 70]),
                "cells": cells,
                "candidates": evaluations
            }, f, ensure_ascii=False, indent=2)

        keywords = extract_top_keywords(days=days, top_n=30)
        with open(data_out_path / f"keywords_{days}.json", "w", encoding="utf-8") as f:
            json.dump({"keywords": keywords}, f, ensure_ascii=False, indent=2)

        entries = get_entries(days=days, limit=1000)
        with open(data_out_path / f"entries_{days}.json", "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)

    # Copy static assets
    static_src = BASE_DIR / "static"
    shutil.copy(static_src / "index.html", out_path / "index.html")
    
    static_out = out_path / "static"
    static_out.mkdir(exist_ok=True)
    shutil.copy(static_src / "style.css", static_out / "style.css")
    shutil.copy(static_src / "app.js", static_out / "app.js")

    print(f"[+] Static bundle successfully built at: {out_path}")

if __name__ == "__main__":
    export_static_site()
