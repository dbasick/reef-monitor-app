#!/usr/bin/env python3
"""
iNaturalist "Not Coral" Image Downloader — Round 2
Backfills failed and new categories for Reef Monitor V2 three-class model.

Round 1 left gaps:
  - Parrotfish (Scaridae family ID 49692): 0 downloaded — FAILED
      Reason: iNaturalist reclassified Scaridae into Labridae around 2020.
              Family-level ID is now inactive. Fix: use species-level IDs.
  - Algae (Dictyota genus): only 23 of 85 — TOO NARROW
      Fix: broaden to class Phaeophyceae (brown algae) + genus Halimeda (green).

New categories (divers commonly photograph these on USVI reefs):
  - Sea turtles, Surgeonfish/Tangs, Sea cucumbers, Lionfish

All images go to the SAME flat folder as round 1:
  ~/Data/coral/raw/not_coral_inat/images/

Round 1 images are NOT re-downloaded (resume logic checks existing filenames).

Usage:
    python3.12 download_not_coral_round2.py              # Download all round 2 categories
    python3.12 download_not_coral_round2.py --test       # Download 5 per category (quick test)
    python3.12 download_not_coral_round2.py --target 30  # Custom per-category target
    python3.12 download_not_coral_round2.py --categories parrotfish-stoplight algae-brown
    python3.12 download_not_coral_round2.py --list       # Show categories and exit

Requirements:
    python3.12 -m pip install requests pillow --break-system-packages
"""

import os
import json
import requests
import time
import argparse
from pathlib import Path
from urllib.parse import urlencode
from PIL import Image
from io import BytesIO

# =============================================================
# ROUND 2 TAXA — FIXED + NEW CATEGORIES ONLY
# (Categories that succeeded in round 1 are skipped)
# =============================================================

TAXA_LIST = [

    # ---- FIXED: PARROTFISH --------------------------------
    # Root cause: Family Scaridae (49692) was merged into Labridae by iNaturalist ~2020.
    # The old family ID returns 0 results. Species-level IDs are stable and unaffected.
    {
        "id": "parrotfish-stoplight",
        "name": "Sparisoma viride (Stoplight Parrotfish)",
        "search_name": "Sparisoma viride",   # API lookup by name (no hardcoded ID)
        "target_count": 60,
        "notes": "Most recognizable Caribbean parrotfish — bright green/red/blue coloring"
    },
    {
        "id": "parrotfish-redband",
        "name": "Sparisoma aurofrenatum (Redband Parrotfish)",
        "search_name": "Sparisoma aurofrenatum",
        "target_count": 50,
        "notes": "Very common in USVI — distinctive red band behind mouth"
    },
    {
        "id": "parrotfish-queen",
        "name": "Scarus vetula (Queen Parrotfish)",
        "search_name": "Scarus vetula",
        "target_count": 40,
        "notes": "Common Caribbean parrotfish — large terminal phase males are vivid blue-green"
    },

    # ---- FIXED: ALGAE -------------------------------------
    # Dictyota genus (51021) only yielded 23 images — too taxonomically narrow.
    # Fix: use class Phaeophyceae (all brown algae) and genus Halimeda (common green alga).
    {
        "id": "algae-brown",
        "name": "Phaeophyceae (Brown Algae)",
        "search_name": "Phaeophyceae",
        "target_count": 80,
        "notes": "Broad brown algae class — includes Dictyota, Sargassum, Lobophora — dominant on overgrown reefs"
    },
    {
        "id": "algae-halimeda",
        "name": "Halimeda (Calcified Green Algae)",
        "search_name": "Halimeda",
        "target_count": 60,
        "notes": "Paddle-shaped calcified green alga — extremely abundant on Caribbean reefs and sandy areas"
    },

    # ---- NEW: SEA TURTLES ---------------------------------
    {
        "id": "turtle-green",
        "name": "Chelonia mydas (Green Sea Turtle)",
        "search_name": "Chelonia mydas",
        "target_count": 50,
        "notes": "Commonly encountered by divers grazing on seagrass in USVI — easily confused with coral background"
    },
    {
        "id": "turtle-hawksbill",
        "name": "Eretmochelys imbricata (Hawksbill Sea Turtle)",
        "search_name": "Eretmochelys imbricata",
        "target_count": 40,
        "notes": "Frequents coral reefs in USVI — often photographed resting near coral heads"
    },

    # ---- NEW: REEF FISH -----------------------------------
    {
        "id": "surgeonfish",
        "name": "Acanthuridae (Surgeonfish / Tangs)",
        "search_name": "Acanthuridae",
        "target_count": 80,
        "notes": "Blue tang (Acanthurus coeruleus) is everywhere in USVI — bright blue reef fish"
    },
    {
        "id": "lionfish",
        "name": "Pterois (Lionfish)",
        "search_name": "Pterois",
        "target_count": 60,
        "notes": "Invasive but ubiquitous in Caribbean — highly distinctive, commonly photographed by divers"
    },

    # ---- NEW: REEF INVERTEBRATES --------------------------
    {
        "id": "sea-cucumbers",
        "name": "Holothuroidea (Sea Cucumbers)",
        "search_name": "Holothuroidea",
        "target_count": 60,
        "notes": "Common on reef substrate and sandy patches — Holothuria mexicana especially common in USVI"
    },
    {
        "id": "nudibranchs",
        "name": "Nudibranchia (Nudibranchs / Sea Slugs)",
        "search_name": "Nudibranchia",
        "target_count": 50,
        "notes": "Colorful and commonly photographed on reefs — very different texture from coral"
    },
]

# =============================================================
# CONFIGURATION (matches round 1 layout exactly)
# =============================================================

DATA_ROOT   = Path.home() / "Data" / "coral" / "raw" / "not_coral_inat"
IMAGES_DIR  = DATA_ROOT / "images"    # Same flat folder as round 1
METADATA_DIR = DATA_ROOT / "metadata"

# Caribbean bounding box (same as round 1)
CARIBBEAN_BOUNDS = {
    "nelat": 27,
    "nelng": -59,
    "swlat": 10,
    "swlng": -86,
}

TARGET_SIZE   = 224
IMAGE_QUALITY = 95

API_BASE = "https://api.inaturalist.org/v1"
HEADERS  = {
    "User-Agent": "ReefMonitor/1.0 (Coral Conservation Research; contact: dabasick@gmail.com)"
}

DELAY_BETWEEN_IMAGES = 0.5
DELAY_BETWEEN_PAGES  = 1.0


# =============================================================
# TAXON ID LOOKUP — prevents stale hardcoded IDs
# =============================================================

def lookup_taxon_id(search_name):
    """
    Look up the current iNaturalist taxon_id for a scientific name.
    Returns (taxon_id, canonical_name) or (None, None) on failure.

    This is the core fix for the parrotfish problem: instead of
    hardcoding a family ID that may be inactive, we look up the
    current active ID at runtime.
    """
    params = {"q": search_name, "per_page": 5, "is_active": "true"}
    try:
        r = requests.get(f"{API_BASE}/taxa", params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        results = r.json().get("results", [])
        if not results:
            return None, None

        # Prefer exact name match; fall back to first result
        for t in results:
            if t["name"].lower() == search_name.lower():
                return t["id"], t["name"]

        # No exact match — use first result but warn
        t = results[0]
        print(f"  [warn] Exact match not found for '{search_name}'; using '{t['name']}' (id={t['id']})")
        return t["id"], t["name"]

    except Exception as e:
        print(f"  [error] Taxa lookup failed for '{search_name}': {e}")
        return None, None


# =============================================================
# iNATURALIST API CALLS
# =============================================================

def check_caribbean_availability(taxon_id, taxon_name):
    """Check how many research-grade, photo'd observations exist in the Caribbean."""
    params = {
        "taxon_id": taxon_id,
        "quality_grade": "research",
        "photos": "true",
        "per_page": 1,
        **CARIBBEAN_BOUNDS,
    }
    try:
        r = requests.get(f"{API_BASE}/observations", params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.json().get("total_results", 0)
    except Exception as e:
        print(f"  [error] Availability check failed: {e}")
        return 0


def fetch_observations(taxon_id, page=1, per_page=200):
    """Fetch a page of research-grade Caribbean observations for a taxon."""
    params = {
        "taxon_id": taxon_id,
        "quality_grade": "research",
        "photos": "true",
        "per_page": per_page,
        "page": page,
        "order": "desc",
        "order_by": "created_at",
        **CARIBBEAN_BOUNDS,
    }
    try:
        r = requests.get(f"{API_BASE}/observations", params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"  [error] Fetch failed: {e}")
        return None


# =============================================================
# IMAGE DOWNLOAD
# =============================================================

def download_and_resize_image(url, filepath, target_size=TARGET_SIZE, max_retries=3):
    """Download, center-crop to square, resize to target_size, save as JPEG."""
    for attempt in range(max_retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()

            img = Image.open(BytesIO(r.content)).convert("RGB")
            w, h = img.size
            min_dim = min(w, h)
            left = (w - min_dim) // 2
            top  = (h - min_dim) // 2
            img  = img.crop((left, top, left + min_dim, top + min_dim))
            img  = img.resize((target_size, target_size), Image.LANCZOS)
            img.save(filepath, "JPEG", quality=IMAGE_QUALITY)
            return True

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                print(f"  [error] Download failed: {e}")
                return False


# =============================================================
# PER-TAXON PROCESSOR
# =============================================================

def process_taxon(taxon_info):
    """Resolve taxon ID, check availability, download images."""
    print(f"\n{'=' * 62}")
    print(f"  {taxon_info['name']}")
    print(f"  Target: {taxon_info['target_count']} images | Caribbean only")
    print(f"  {taxon_info['notes']}")
    print(f"{'=' * 62}")

    # --- Step 1: Resolve current taxon ID ---
    print(f"  Looking up taxon ID for '{taxon_info['search_name']}'...")
    taxon_id, canonical_name = lookup_taxon_id(taxon_info["search_name"])
    if not taxon_id:
        print(f"  [SKIP] Could not resolve taxon ID. Skipping.")
        return 0
    print(f"  Resolved: {canonical_name} → taxon_id={taxon_id}")
    time.sleep(0.5)

    # --- Step 2: Check Caribbean availability ---
    available = check_caribbean_availability(taxon_id, canonical_name)
    print(f"  Caribbean research-grade observations: {available}")
    if available == 0:
        print(f"  [SKIP] Zero Caribbean observations — skipping.")
        return 0
    if available < taxon_info["target_count"]:
        print(f"  [warn] Fewer images available ({available}) than target ({taxon_info['target_count']})")
    time.sleep(0.5)

    # --- Step 3: Load existing metadata / resume ---
    metadata_file = METADATA_DIR / f"{taxon_info['id']}_metadata.json"
    prefix = f"not_coral_{taxon_info['id']}_"
    existing_files = list(IMAGES_DIR.glob(f"{prefix}*.jpg"))
    downloaded = len(existing_files)

    existing_ids = set()
    metadata_list = []
    if metadata_file.exists():
        with open(metadata_file) as f:
            metadata_list = json.load(f)
            existing_ids = {m["observation_id"] for m in metadata_list}

    if downloaded > 0:
        print(f"  Resuming: {downloaded} images already present")

    # --- Step 4: Download ---
    page = 1
    consecutive_skips = 0

    while downloaded < taxon_info["target_count"]:
        data = fetch_observations(taxon_id, page=page)

        if not data or not data.get("results"):
            print("  No more results.")
            break

        for obs in data["results"]:
            if downloaded >= taxon_info["target_count"]:
                break

            if obs["id"] in existing_ids:
                consecutive_skips += 1
                continue

            consecutive_skips = 0

            if not obs.get("photos"):
                continue

            photo = obs["photos"][0]
            image_url = photo.get("url")
            if not image_url:
                continue
            image_url = image_url.replace("square", "medium")

            filename = f"not_coral_{taxon_info['id']}_{obs['id']}.jpg"
            filepath = IMAGES_DIR / filename

            if filepath.exists():
                downloaded += 1
                continue

            print(f"  [{downloaded + 1}/{taxon_info['target_count']}] {filename}")
            if download_and_resize_image(image_url, filepath):
                downloaded += 1
                existing_ids.add(obs["id"])
                metadata_list.append({
                    "filename":       filename,
                    "observation_id": obs["id"],
                    "class":          "not_coral",
                    "subcategory":    taxon_info["id"],
                    "taxon_name":     canonical_name,
                    "quality_grade":  obs.get("quality_grade"),
                    "observed_on":    obs.get("observed_on"),
                    "place_guess":    obs.get("place_guess"),
                    "latitude":       obs.get("geojson", {}).get("coordinates", [None, None])[1]
                                      if obs.get("geojson") else None,
                    "longitude":      obs.get("geojson", {}).get("coordinates", [None, None])[0]
                                      if obs.get("geojson") else None,
                    "url":            f"https://www.inaturalist.org/observations/{obs['id']}",
                    "license":        photo.get("license_code"),
                    "attribution":    photo.get("attribution"),
                    "round":          2,
                })

            time.sleep(DELAY_BETWEEN_IMAGES)

        page += 1
        time.sleep(DELAY_BETWEEN_PAGES)

        if consecutive_skips > 200:
            print("  Too many consecutive skips — moving on.")
            break

    # Save metadata after each taxon (crash-safe)
    with open(metadata_file, "w") as f:
        json.dump(metadata_list, f, indent=2)

    print(f"  Done: {downloaded} images")
    return downloaded


# =============================================================
# MAIN
# =============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Round 2 not-coral image downloader for Reef Monitor V2")
    parser.add_argument("--test",       action="store_true",
                        help="Quick test: 5 images per category")
    parser.add_argument("--target",     type=int, default=None,
                        help="Override per-category target count")
    parser.add_argument("--categories", nargs="+", default=None,
                        help="Only run specific categories (e.g. parrotfish-stoplight algae-brown)")
    parser.add_argument("--list",       action="store_true",
                        help="List categories and exit without downloading")
    args = parser.parse_args()

    print()
    print("iNaturalist 'Not Coral' Downloader — Round 2")
    print("Reef Monitor V2 Three-Class Model")
    print("=" * 62)

    # Count existing round 1 images for context
    if IMAGES_DIR.exists():
        existing_count = len(list(IMAGES_DIR.glob("*.jpg")))
        print(f"\nExisting images in folder: {existing_count} (round 1 + any prior round 2)")

    if args.list:
        print("\nAvailable categories:")
        for t in TAXA_LIST:
            print(f"  {t['id']:35s} {t['name']}")
            print(f"  {'':35s} Search: '{t['search_name']}' | Target: {t['target_count']}")
        return

    taxa_to_process = TAXA_LIST
    if args.categories:
        taxa_to_process = [t for t in TAXA_LIST if t["id"] in args.categories]
        if not taxa_to_process:
            avail = [t["id"] for t in TAXA_LIST]
            print(f"\nNo matching categories found.\nAvailable: {avail}")
            return

    if args.test:
        print("\n[TEST MODE] 5 images per category\n")
        for t in taxa_to_process:
            t["target_count"] = 5
    elif args.target:
        print(f"\n[Custom target] {args.target} per category\n")
        for t in taxa_to_process:
            t["target_count"] = args.target

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)

    total_target = sum(t["target_count"] for t in taxa_to_process)
    print(f"\nCategories this run : {len(taxa_to_process)}")
    print(f"Images targeted     : {total_target}")
    print(f"Output folder       : {IMAGES_DIR}")
    print()

    results = {}
    for taxon in taxa_to_process:
        count = process_taxon(taxon)
        results[taxon["id"]] = (taxon["name"], count, taxon["target_count"])

    # Final summary
    print(f"\n{'=' * 62}")
    print("ROUND 2 SUMMARY")
    print(f"{'=' * 62}")
    total_new = 0
    any_shortfall = False
    for cat_id, (name, got, target) in results.items():
        status = "✓" if got >= target else f"PARTIAL ({got}/{target})"
        print(f"  {cat_id:35s} {got:3d}  {status}")
        total_new += got
        if got < target:
            any_shortfall = True

    if IMAGES_DIR.exists():
        grand_total = len(list(IMAGES_DIR.glob("*.jpg")))
    else:
        grand_total = total_new

    print(f"\n  New images this run : {total_new}")
    print(f"  Grand total (all)   : {grand_total} images in {IMAGES_DIR}")

    print("\nNext steps:")
    print("  1. Visual review: spot-check a sample from each new category")
    if any_shortfall:
        print("  2. Re-run with --categories <shortfall_id> to retry partial downloads")
    print("  2. Re-assemble dataset: python3.12 train_v2_health_model.py --assemble")
    print("  3. Retrain:             caffeinate -is python3.12 train_v2_health_model.py --lr 0.0001")
    print()


if __name__ == "__main__":
    main()
