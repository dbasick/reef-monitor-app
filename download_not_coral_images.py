#!/usr/bin/env python3
"""
iNaturalist "Not Coral" Image Downloader
Downloads diverse non-coral marine observations from the Caribbean
for training a three-class model: Healthy Coral / Bleached Coral / Not Coral

Targets ~600 images across 7 categories commonly seen on Caribbean reefs:
  - Sponges, Sea Fans, Seagrass, Algae, Sea Urchins, Parrotfish, Anemones

Usage:
    python download_not_coral_images.py
    python download_not_coral_images.py --test          # Download 5 per category (quick test)
    python download_not_coral_images.py --target 50     # Custom per-category target

Requirements:
    pip install requests pillow --break-system-packages
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
# NON-CORAL TAXA TO DOWNLOAD
# =============================================================
# These are organisms commonly seen on Caribbean reefs that
# users might accidentally photograph thinking it's coral.
# Each targets ~85 images to reach ~600 total across 7 categories.

TAXA_LIST = [
    {
        "id": "sponges",
        "name": "Porifera (Sponges)",
        "taxon_id": 48824,        # Phylum Porifera
        "target_count": 100,
        "notes": "Barrel sponges, tube sponges, encrusting sponges - very common on Caribbean reefs"
    },
    {
        "id": "sea-fans",
        "name": "Gorgonia (Sea Fans)",
        "taxon_id": 120132,        # Genus Gorgonia
        "target_count": 85,
        "notes": "Often confused with coral - technically soft coral/octocoral"
    },
    {
        "id": "seagrass",
        "name": "Thalassia testudinum (Turtle Grass)",
        "taxon_id": 118509,        # Species
        "target_count": 85,
        "notes": "Dominant seagrass in USVI waters, different habitat from reef"
    },
    {
        "id": "algae",
        "name": "Dictyota (Y-branched Algae)",
        "taxon_id": 51021,         # Genus Dictyota
        "target_count": 85,
        "notes": "Common brown macroalgae on Caribbean reefs, often overgrows coral"
    },
    {
        "id": "sea-urchins",
        "name": "Diadema antillarum (Long-spined Sea Urchin)",
        "taxon_id": 52290,         # Species
        "target_count": 85,
        "notes": "Keystone herbivore on Caribbean reefs"
    },
    {
        "id": "parrotfish",
        "name": "Scaridae (Parrotfish)",
        "taxon_id": 49692,         # Family Scaridae
        "target_count": 85,
        "notes": "Most common reef fish, often in user photos"
    },
    {
        "id": "anemones",
        "name": "Actiniaria (Sea Anemones)",
        "taxon_id": 47533,         # Order Actiniaria
        "target_count": 85,
        "notes": "Can be confused with coral polyps"
    },
]

# =============================================================
# CONFIGURATION
# =============================================================

# Data lives in ~/Data/coral/raw/not_coral_inat/ (separate from project repo)
DATA_ROOT = Path.home() / "Data" / "coral" / "raw" / "not_coral_inat"
IMAGES_DIR = DATA_ROOT / "images"         # All images in one flat folder
METADATA_DIR = DATA_ROOT / "metadata"     # Subcategory tracked here only

# Caribbean bounding box for geographic filtering
# Covers USVI, Puerto Rico, and broader Caribbean
CARIBBEAN_BOUNDS = {
    "nelat": 27,    # North
    "nelng": -59,   # East
    "swlat": 10,    # South
    "swlng": -86,   # West
}

# Image settings
TARGET_SIZE = 224   # Match existing model input size
IMAGE_QUALITY = 95  # JPEG quality for resized images

# iNaturalist API
API_BASE = "https://api.inaturalist.org/v1"
HEADERS = {
    "User-Agent": "ReefMonitor/1.0 (Coral Conservation Research; contact: DaBasick@yahoo.com)"
}

# Rate limiting
DELAY_BETWEEN_IMAGES = 0.5   # seconds
DELAY_BETWEEN_PAGES = 1.0    # seconds


def create_directories():
    """Create directory structure — single flat images folder"""
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(exist_ok=True)
    METADATA_DIR.mkdir(exist_ok=True)

    print(f"Images folder: {IMAGES_DIR.absolute()}")
    print(f"  (all not-coral images go here regardless of subcategory)")
    print()


def fetch_observations(taxon_info, page=1, per_page=200):
    """Fetch observations from iNaturalist API with Caribbean filtering"""
    params = {
        "taxon_id": taxon_info["taxon_id"],
        "quality_grade": "research",
        "photos": "true",
        "per_page": per_page,
        "page": page,
        "order": "desc",
        "order_by": "created_at",
        # Caribbean geographic filter
        **CARIBBEAN_BOUNDS,
    }

    url = f"{API_BASE}/observations?{urlencode(params)}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"  Error fetching observations: {e}")
        return None


def download_and_resize_image(url, filepath, target_size=TARGET_SIZE, max_retries=3):
    """Download image, resize to target_size x target_size, save as JPEG"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()

            # Open image and resize to match model input
            img = Image.open(BytesIO(response.content))
            img = img.convert("RGB")  # Ensure RGB

            # Center crop to square first, then resize
            w, h = img.size
            min_dim = min(w, h)
            left = (w - min_dim) // 2
            top = (h - min_dim) // 2
            img = img.crop((left, top, left + min_dim, top + min_dim))
            img = img.resize((target_size, target_size), Image.LANCZOS)

            img.save(filepath, "JPEG", quality=IMAGE_QUALITY)
            return True

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            else:
                print(f"  Failed to download: {e}")
                return False


def process_taxon(taxon_info):
    """Download images for a specific non-coral taxon"""
    print(f"{'=' * 60}")
    print(f"  {taxon_info['name']}")
    print(f"  Target: {taxon_info['target_count']} images | Caribbean only")
    print(f"  {taxon_info['notes']}")
    print(f"{'=' * 60}")

    metadata_file = METADATA_DIR / f"{taxon_info['id']}_metadata.json"

    # Check for existing downloads (resume support)
    prefix = f"not_coral_{taxon_info['id']}_"
    existing = list(IMAGES_DIR.glob(f"{prefix}*.jpg"))
    downloaded = len(existing)
    if downloaded > 0:
        print(f"  Found {downloaded} existing images, resuming...")

    # Load existing metadata if resuming
    existing_ids = set()
    metadata_list = []
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            metadata_list = json.load(f)
            existing_ids = {m["observation_id"] for m in metadata_list}

    page = 1
    consecutive_skips = 0

    while downloaded < taxon_info["target_count"]:
        data = fetch_observations(taxon_info, page=page)

        if not data or "results" not in data:
            print("  No more results from API.")
            break

        observations = data["results"]
        if not observations:
            print("  No more observations found.")
            break

        total_available = data.get("total_results", "?")
        if page == 1:
            print(f"  Total available in Caribbean: {total_available}")

        for obs in observations:
            if downloaded >= taxon_info["target_count"]:
                break

            # Skip already downloaded
            if obs["id"] in existing_ids:
                consecutive_skips += 1
                continue

            consecutive_skips = 0

            # Must have photos
            if not obs.get("photos") or len(obs["photos"]) == 0:
                continue

            photo = obs["photos"][0]
            image_url = photo.get("url")
            if not image_url:
                continue

            # Use "medium" size (good balance of quality and download speed)
            image_url = image_url.replace("square", "medium")

            filename = f"not_coral_{taxon_info['id']}_{obs['id']}.jpg"
            filepath = IMAGES_DIR / filename

            if filepath.exists():
                downloaded += 1
                continue

            # Download and resize
            print(f"  [{downloaded + 1}/{taxon_info['target_count']}] {filename}")
            if download_and_resize_image(image_url, filepath):
                downloaded += 1
                existing_ids.add(obs["id"])

                metadata_list.append({
                    "filename": filename,
                    "observation_id": obs["id"],
                    "class": "not_coral",
                    "subcategory": taxon_info["id"],
                    "taxon_name": taxon_info["name"],
                    "quality_grade": obs.get("quality_grade"),
                    "observed_on": obs.get("observed_on"),
                    "place_guess": obs.get("place_guess"),
                    "latitude": obs.get("geojson", {}).get("coordinates", [None, None])[1] if obs.get("geojson") else None,
                    "longitude": obs.get("geojson", {}).get("coordinates", [None, None])[0] if obs.get("geojson") else None,
                    "url": f"https://www.inaturalist.org/observations/{obs['id']}",
                    "license": photo.get("license_code"),
                    "attribution": photo.get("attribution"),
                })

            time.sleep(DELAY_BETWEEN_IMAGES)

        page += 1
        time.sleep(DELAY_BETWEEN_PAGES)

        # Safety: if we've skipped too many in a row, we may be looping
        if consecutive_skips > 200:
            print("  Too many consecutive skips, moving on.")
            break

    # Save metadata (after each taxon, so progress isn't lost)
    with open(metadata_file, 'w') as f:
        json.dump(metadata_list, f, indent=2)

    print(f"  Done: {downloaded} images for {taxon_info['name']}")
    print()
    return downloaded


def print_summary(results):
    """Print final download summary"""
    print()
    print("=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)

    total = 0
    for name, count in results.items():
        status = "ok" if count > 0 else "FAILED"
        print(f"  {name}: {count} images [{status}]")
        total += count

    print(f"\n  Total 'not coral' images: {total}")
    print(f"  Output directory: {DATA_ROOT.absolute()}")
    print(f"  Image size: {TARGET_SIZE}x{TARGET_SIZE} (ready for training)")

    print("\n  Next steps:")
    print("  1. Quick visual review — remove any mislabeled images")
    print("  2. Combine with existing healthy/bleached training data")
    print("  3. Retrain model with 3-class output (healthy / bleached / not_coral)")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Download non-coral marine images from iNaturalist for training")
    parser.add_argument("--test", action="store_true",
                       help="Quick test: download only 5 per category")
    parser.add_argument("--target", type=int, default=None,
                       help="Override per-category target count")
    parser.add_argument("--categories", nargs="+", default=None,
                       help="Only download specific categories (e.g., sponges sea-fans)")
    args = parser.parse_args()

    print()
    print("iNaturalist 'Not Coral' Image Downloader")
    print("For Reef Monitor v2 Three-Class Model")
    print("=" * 60)
    print()

    # Apply overrides
    if args.test:
        print("TEST MODE: downloading 5 per category\n")
        for t in TAXA_LIST:
            t["target_count"] = 5
    elif args.target:
        print(f"Custom target: {args.target} per category\n")
        for t in TAXA_LIST:
            t["target_count"] = args.target

    # Filter categories if specified
    taxa_to_process = TAXA_LIST
    if args.categories:
        taxa_to_process = [t for t in TAXA_LIST if t["id"] in args.categories]
        if not taxa_to_process:
            print(f"No matching categories found. Available: {[t['id'] for t in TAXA_LIST]}")
            return

    total_target = sum(t["target_count"] for t in taxa_to_process)
    print(f"Categories: {len(taxa_to_process)}")
    print(f"Total target: {total_target} images")
    print()

    create_directories()

    results = {}
    for taxon in taxa_to_process:
        count = process_taxon(taxon)
        results[taxon["name"]] = count

    print_summary(results)


if __name__ == "__main__":
    main()
