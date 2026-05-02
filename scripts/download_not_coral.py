#!/usr/bin/env python3
"""
Download Not-Coral Images from CoralNet
=========================================
Reads the curated not_coral_manifest.csv and downloads the
referenced images from CoralNet, then crops 224x224 patches
at the annotated coordinates.

This is a two-phase script:
    Phase 1: Download full images from CoralNet
    Phase 2: Crop 224x224 patches at annotation coordinates

Usage:
    python download_not_coral.py \
        --manifest ~/Data/coral/processed/health_model_v2/manifests/not_coral_manifest.csv \
        --image-dir ~/Data/coral/processed/health_model_v2/downloads/images \
        --output-dir ~/Data/coral/processed/health_model_v2/training_data/not_coral

Requirements:
    pip install requests Pillow tqdm

Notes:
    - CoralNet image URL pattern may need adjustment based on how
      their image serving works. The script tries multiple patterns.
    - 0.5s delay between requests to be polite to CoralNet servers.
    - Resumes where it left off (skips existing downloads/crops).
    - Run with --dry-run first to see what would be downloaded.
"""

import csv
import os
import argparse
import time
from collections import Counter

try:
    import requests
except ImportError:
    print("Missing 'requests' library. Install with: pip install requests")
    exit(1)

try:
    from PIL import Image
except ImportError:
    print("Missing 'Pillow' library. Install with: pip install Pillow")
    exit(1)

try:
    from tqdm import tqdm
except ImportError:
    # Fallback: simple progress without tqdm
    class tqdm:
        def __init__(self, iterable, desc="", **kwargs):
            self.iterable = iterable
            self.desc = desc
            self.total = len(iterable) if hasattr(iterable, '__len__') else None
        def __iter__(self):
            for i, item in enumerate(self.iterable):
                if self.total and i % 50 == 0:
                    print(f"  {self.desc}: {i}/{self.total}")
                yield item


PATCH_SIZE = 224
REQUEST_DELAY = 0.5

# CoralNet URL patterns to try for image download
# The source URL from the manifest looks like:
#   https://coralnet.ucsd.edu/source/1388/
# Images may be accessible at several URL patterns
CORALNET_URL_PATTERNS = [
    # Direct media URL
    "https://coralnet.ucsd.edu/media/images/{image_name}",
    # Browse URL (may redirect)
    "{images_url}{image_name}",
]


def download_image(image_name, images_url, output_path, session):
    """Try to download an image. Returns True if successful."""
    if os.path.exists(output_path):
        return True

    for pattern in CORALNET_URL_PATTERNS:
        url = pattern.format(image_name=image_name, images_url=images_url)
        if not url.startswith('http'):
            continue
        try:
            resp = session.get(url, timeout=30, allow_redirects=True)
            if resp.status_code == 200 and len(resp.content) > 1000:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(resp.content)
                return True
        except Exception:
            continue

    return False


def crop_patch(image_path, center_row, center_col, patch_size=PATCH_SIZE):
    """Crop a square patch centered at (row, col). Returns PIL Image or None."""
    try:
        img = Image.open(image_path)
    except Exception:
        return None

    width, height = img.size
    half = patch_size // 2

    left = center_col - half
    upper = center_row - half
    right = center_col + half
    lower = center_row + half

    # Shift if out of bounds
    if left < 0:
        right -= left
        left = 0
    if upper < 0:
        lower -= upper
        upper = 0
    if right > width:
        left -= (right - width)
        right = width
    if lower > height:
        upper -= (lower - height)
        lower = height

    # Validate
    if left < 0 or upper < 0 or right > width or lower > height:
        return None
    if (right - left) != patch_size or (lower - upper) != patch_size:
        return None

    return img.crop((left, upper, right, lower))


def main():
    parser = argparse.ArgumentParser(
        description='Download and crop Not Coral training images')
    parser.add_argument('--manifest', required=True,
                       help='Path to not_coral_manifest.csv')
    parser.add_argument('--image-dir', required=True,
                       help='Directory to save downloaded full images')
    parser.add_argument('--output-dir', required=True,
                       help='Directory to save cropped 224x224 patches')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be downloaded without downloading')
    parser.add_argument('--skip-download', action='store_true',
                       help='Skip download phase (images already downloaded)')
    args = parser.parse_args()

    # Read manifest
    annotations = []
    with open(args.manifest, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            annotations.append(row)

    print(f"Manifest: {len(annotations)} annotations")

    # Unique images
    unique_images = {}
    for ann in annotations:
        key = f"{ann['source']}||{ann['image_name']}"
        if key not in unique_images:
            unique_images[key] = ann

    print(f"Unique images: {len(unique_images)}")

    # Group stats
    groups = Counter(ann['group'] for ann in annotations)
    print(f"\nSamples per group:")
    for group, count in groups.most_common():
        print(f"  {group}: {count}")

    if args.dry_run:
        print("\n[DRY RUN] Would download images from these sources:")
        sources = Counter(ann['source'] for ann in annotations)
        for source, count in sources.most_common():
            url = annotations[0].get('source_url', 'unknown')
            for a in annotations:
                if a['source'] == source:
                    url = a.get('source_url', 'unknown')
                    break
            print(f"  {source}: {count} images — {url}")
        return

    os.makedirs(args.image_dir, exist_ok=True)
    os.makedirs(args.output_dir, exist_ok=True)

    # ---- Phase 1: Download ----
    if not args.skip_download:
        print(f"\n{'='*50}")
        print("PHASE 1: Downloading images from CoralNet")
        print(f"{'='*50}\n")

        session = requests.Session()
        session.headers.update({
            'User-Agent': 'ReefMonitor-Research/1.0 (coral health study)'
        })

        downloaded = 0
        skipped = 0
        failed = []

        for key, ann in tqdm(list(unique_images.items()), desc="Downloading"):
            source = ann['source']
            image_name = ann['image_name']
            images_url = ann.get('images_url', '')

            output_path = os.path.join(args.image_dir, source, image_name)

            if os.path.exists(output_path):
                skipped += 1
                continue

            success = download_image(image_name, images_url, output_path, session)
            if success:
                downloaded += 1
            else:
                failed.append((source, image_name))

            time.sleep(REQUEST_DELAY)

        print(f"\nDownload complete:")
        print(f"  New downloads: {downloaded}")
        print(f"  Already existed: {skipped}")
        print(f"  Failed: {len(failed)}")

        if failed:
            fail_path = os.path.join(args.image_dir, 'failed_downloads.txt')
            with open(fail_path, 'w') as f:
                for source, name in failed:
                    f.write(f"{source}\t{name}\n")
            print(f"  Failed list: {fail_path}")
    else:
        print("\nSkipping download phase (--skip-download)")

    # ---- Phase 2: Crop patches ----
    print(f"\n{'='*50}")
    print("PHASE 2: Cropping 224x224 patches")
    print(f"{'='*50}\n")

    cropped = 0
    skipped_crop = 0
    missing = 0
    crop_failed = 0

    for ann in tqdm(annotations, desc="Cropping"):
        source = ann['source']
        image_name = ann['image_name']
        row_px = int(float(ann['row_px']))
        col_px = int(float(ann['col_px']))
        group = ann['group']

        # Source image path
        image_path = os.path.join(args.image_dir, source, image_name)
        if not os.path.exists(image_path):
            missing += 1
            continue

        # Output patch path (organized by group subdirectory)
        safe_source = source.replace('/', '_').replace(' ', '_')[:30]
        safe_image = os.path.splitext(image_name)[0].replace('/', '_')[:30]
        patch_name = f"{safe_source}_{safe_image}_{row_px}_{col_px}.jpg"

        # Save in group subdirectory for easy review
        group_dir = os.path.join(args.output_dir, group)
        os.makedirs(group_dir, exist_ok=True)
        patch_path = os.path.join(group_dir, patch_name)

        if os.path.exists(patch_path):
            skipped_crop += 1
            cropped += 1
            continue

        patch = crop_patch(image_path, row_px, col_px)
        if patch is None:
            crop_failed += 1
            continue

        patch.save(patch_path, 'JPEG', quality=95)
        cropped += 1

    print(f"\nCrop complete:")
    print(f"  Patches created: {cropped}")
    print(f"  Missing images: {missing}")
    print(f"  Crop failed (too small): {crop_failed}")

    # Final summary
    print(f"\n{'='*50}")
    print("SUMMARY")
    print(f"{'='*50}")
    print(f"Training patches saved to: {args.output_dir}")
    print(f"Organized in subdirectories by group:")
    for group in sorted(groups.keys()):
        group_dir = os.path.join(args.output_dir, group)
        if os.path.exists(group_dir):
            count = len([f for f in os.listdir(group_dir) if f.endswith('.jpg')])
            print(f"  {group}/: {count} patches")
    print(f"\nTotal: {cropped} patches ready for training")
    print(f"\nNext step: visually review a sample of patches from each group")


if __name__ == '__main__':
    main()
