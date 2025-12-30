#!/usr/bin/env python3
"""
iNaturalist Coral Image Downloader
Downloads research-grade coral observations for training dataset

Usage:
    python download_coral_images.py

Requirements:
    pip install requests pillow --break-system-packages
"""

import os
import json
import requests
import time
from pathlib import Path
from urllib.parse import urlencode

# Species to download (matching our coral guide)
SPECIES_LIST = [
    {
        "id": "elkhorn",
        "name": "Acropora palmata",
        "taxon_id": 52831,  # iNaturalist taxon ID
        "target_count": 150
    },
    {
        "id": "staghorn",
        "name": "Acropora cervicornis",
        "taxon_id": 52834,
        "target_count": 150
    },
    {
        "id": "boulder-brain",
        "name": "Colpophyllia natans",
        "taxon_id": 126326,
        "target_count": 150
    },
    {
        "id": "mountainous-star",
        "name": "Orbicella faveolata",
        "taxon_id": 415155,
        "target_count": 150
    },
    {
        "id": "mustard-hill",
        "name": "Porites astreoides",
        "taxon_id": 52963,
        "target_count": 150
    }
]

# Output directory structure
OUTPUT_DIR = Path("training_data")
METADATA_DIR = OUTPUT_DIR / "metadata"

# iNaturalist API configuration
API_BASE = "https://api.inaturalist.org/v1"
HEADERS = {
    "User-Agent": "ReefMonitor/1.0 (Coral Conservation Research)"
}

def create_directories():
    """Create directory structure for downloaded images"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    METADATA_DIR.mkdir(exist_ok=True)
    
    for species in SPECIES_LIST:
        species_dir = OUTPUT_DIR / species["id"]
        species_dir.mkdir(exist_ok=True)
        print(f"Created directory: {species_dir}")

def fetch_observations(species_info, page=1, per_page=200):
    """Fetch observations from iNaturalist API"""
    params = {
        "taxon_id": species_info["taxon_id"],
        "quality_grade": "research",  # Only research-grade observations
        "photos": "true",  # Must have photos
        "per_page": per_page,
        "page": page,
        "order": "desc",
        "order_by": "created_at",
        # Optional: filter by location (Caribbean region)
        # "nelat": 25, "nelng": -60, "swlat": 10, "swlng": -85,
    }
    
    url = f"{API_BASE}/observations?{urlencode(params)}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching observations: {e}")
        return None

def download_image(url, filepath, max_retries=3):
    """Download image from URL with retry logic"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            return True
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait before retry
                continue
            else:
                print(f"Failed to download {url}: {e}")
                return False

def process_species(species_info):
    """Download images for a specific species"""
    print(f"\n{'='*60}")
    print(f"Processing: {species_info['name']} ({species_info['id']})")
    print(f"Target: {species_info['target_count']} images")
    print(f"{'='*60}\n")
    
    species_dir = OUTPUT_DIR / species_info["id"]
    metadata_file = METADATA_DIR / f"{species_info['id']}_metadata.json"
    
    downloaded = 0
    page = 1
    metadata_list = []
    
    while downloaded < species_info["target_count"]:
        print(f"Fetching page {page}...")
        data = fetch_observations(species_info, page=page)
        
        if not data or "results" not in data:
            print("No more results available.")
            break
        
        observations = data["results"]
        if not observations:
            print("No more observations found.")
            break
        
        for obs in observations:
            if downloaded >= species_info["target_count"]:
                break
            
            # Get the first photo (usually best quality)
            if not obs.get("photos") or len(obs["photos"]) == 0:
                continue
            
            photo = obs["photos"][0]
            
            # Use medium size for training (good balance of quality/size)
            image_url = photo.get("url")
            if not image_url:
                continue
            
            # Replace "square" with "medium" in URL for better quality
            image_url = image_url.replace("square", "medium")
            
            # Create filename from observation ID
            filename = f"{species_info['id']}_{obs['id']}.jpg"
            filepath = species_dir / filename
            
            # Skip if already downloaded
            if filepath.exists():
                print(f"Skipping (already exists): {filename}")
                downloaded += 1
                continue
            
            # Download image
            print(f"Downloading ({downloaded + 1}/{species_info['target_count']}): {filename}")
            if download_image(image_url, filepath):
                downloaded += 1
                
                # Save metadata
                metadata_list.append({
                    "filename": filename,
                    "observation_id": obs["id"],
                    "species": species_info["name"],
                    "quality_grade": obs.get("quality_grade"),
                    "observed_on": obs.get("observed_on"),
                    "place_guess": obs.get("place_guess"),
                    "latitude": obs.get("geojson", {}).get("coordinates", [None, None])[1],
                    "longitude": obs.get("geojson", {}).get("coordinates", [None, None])[0],
                    "url": f"https://www.inaturalist.org/observations/{obs['id']}",
                    "license": photo.get("license_code"),
                    "attribution": photo.get("attribution")
                })
            
            # Be nice to iNaturalist servers
            time.sleep(0.5)
        
        page += 1
        time.sleep(1)  # Pause between pages
    
    # Save metadata
    with open(metadata_file, 'w') as f:
        json.dump(metadata_list, f, indent=2)
    
    print(f"\n✓ Downloaded {downloaded} images for {species_info['name']}")
    print(f"✓ Metadata saved to: {metadata_file}")
    
    return downloaded

def main():
    """Main execution function"""
    print("iNaturalist Coral Image Downloader")
    print("="*60)
    
    create_directories()
    
    total_downloaded = 0
    results = {}
    
    for species in SPECIES_LIST:
        count = process_species(species)
        results[species["name"]] = count
        total_downloaded += count
    
    # Print summary
    print("\n" + "="*60)
    print("DOWNLOAD SUMMARY")
    print("="*60)
    for species_name, count in results.items():
        print(f"{species_name}: {count} images")
    print(f"\nTotal downloaded: {total_downloaded} images")
    print(f"Output directory: {OUTPUT_DIR.absolute()}")
    print("\nNext steps:")
    print("1. Review images in each species folder")
    print("2. Remove any misidentified or poor quality images")
    print("3. Split into train/validation/test sets")
    print("4. Begin model training")

if __name__ == "__main__":
    main()
