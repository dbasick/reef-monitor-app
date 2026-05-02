#!/usr/bin/env python3
"""
ReefNet Caribbean Curation Pipeline
====================================
Streams through the ReefNet All_ReefNet_annotations.csv and produces:

1. A manifest CSV for each of three classes:
   - healthy_coral_manifest.csv
   - unhealthy_coral_manifest.csv
   - not_coral_manifest.csv

2. An image download script (download_images.py) that fetches images
   from CoralNet and crops 224x224 patches at annotated coordinates.

3. A summary report of what was found.

Usage:
    python curate_reefnet_caribbean.py --annotations /path/to/All_ReefNet_annotations.csv \
                                       --sources /path/to/Overview_Sources_for_Image_Download.csv \
                                       --output /path/to/output_dir

The script is memory-efficient — it streams the CSV row by row and never
loads the full 6M-row file into memory.

Classes:
    - Healthy Coral: USVI genera annotations with no condition tag (or "Healthy")
    - Unhealthy Coral: Annotations tagged as Dead, Bleached, or Trematodiasis
      (Note: Caribbean subset has very few of these — see summary report)
    - Not Coral: Algae, Abiotic background, Other biota categories

Scope:
    - Caribbean ecoregions only (Greater Antilles, Southern Caribbean,
      Eastern Caribbean, Southwestern Caribbean)
    - USVI-relevant genera only for coral classes
"""

import csv
import json
import os
import argparse
from collections import Counter, defaultdict
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

# The 13 genera matching the 18 USVI species in the app
USVI_GENERA = {
    'Acropora',        # Elkhorn (A. palmata) + Staghorn (A. cervicornis)
    'Dendrogyra',      # Pillar Coral (D. cylindrus)
    'Orbicella',       # Mountainous/Lobed/Boulder Star
    'Colpophyllia',    # Boulder Brain (C. natans)
    'Pseudodiploria',  # Symmetrical Brain (P. strigosa)
    'Diploria',        # Grooved Brain (D. labyrinthiformis)
    'Eusmilia',        # Smooth Flower (E. fastigiata)
    'Dichocoenia',     # Elliptical Star (D. stokesii)
    'Porites',         # Mustard Hill (P. astreoides) + Finger (P. porites)
    'Agaricia',        # Lettuce (A. agaricites)
    'Siderastrea',     # Massive Starlet (S. siderea) + Lesser Starlet (S. radians)
    'Montastraea',     # Great Star (M. cavernosa)
    'Stephanocoenia',  # Blushing Star (S. intersepta)
}

# Keywords to identify Caribbean ecoregions
CARIBBEAN_KEYWORDS = ['caribbean', 'antilles', 'bahamian']

# Condition tags that map to "Unhealthy"
UNHEALTHY_CONDITIONS = {'Dead', 'Bleached', 'Trematodiasis'}

# Broad categories that map to "Not Coral"
NOT_CORAL_CATEGORIES = {'Algae', 'Abiotic background', 'Other biota'}

# Specific non-coral labels to EXCLUDE (too ambiguous or not useful)
EXCLUDED_NONCORAL_LABELS = {'Unsorted', 'Unknown', 'Shadow'}

# Patch size for cropping
PATCH_SIZE = 224

# Target samples per class (for balanced dataset recommendations)
TARGET_PER_CLASS = 500


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def is_caribbean(ecoregion):
    """Check if an ecoregion string matches Caribbean regions."""
    if not ecoregion:
        return False
    eco_lower = ecoregion.lower()
    return any(kw in eco_lower for kw in CARIBBEAN_KEYWORDS)


def classify_annotation(row):
    """
    Classify a single annotation row into one of three classes.

    Returns:
        'healthy_coral', 'unhealthy_coral', 'not_coral', or None (skip)
    """
    label = row.get('Sorted_ReefNet_label', '')
    broad = row.get('Broad_category', '')
    condition = row.get('Condition_indication', '')

    # Check if it's a USVI coral genus
    if label in USVI_GENERA:
        if condition in UNHEALTHY_CONDITIONS:
            return 'unhealthy_coral'
        else:
            return 'healthy_coral'

    # Check if it's a non-coral category
    if broad in NOT_CORAL_CATEGORIES:
        if label in EXCLUDED_NONCORAL_LABELS:
            return None  # Skip ambiguous labels
        return 'not_coral'

    return None  # Not relevant to our three classes


def build_source_lookup(sources_csv):
    """
    Build a lookup from CoralNet source name to source URL info.

    Returns dict: source_name -> {url, images_url, image_count}
    """
    lookup = {}
    if not sources_csv or not os.path.exists(sources_csv):
        return lookup

    with open(sources_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            source = row.get('Source', '')
            if source and row.get('Valid', '') == 'yes':
                lookup[source] = {
                    'url': row.get('URL', ''),
                    'images_url': row.get('ImagesURL', ''),
                    'image_count': row.get('ImagesNumber', ''),
                }
    return lookup


# ============================================================
# MAIN PIPELINE
# ============================================================

def run_pipeline(annotations_csv, sources_csv, output_dir,
                 include_global_unhealthy=False):
    """
    Main pipeline: stream through annotations, classify, and produce manifests.

    If include_global_unhealthy=True, bleached/dead coral annotations from
    ALL ecoregions (not just Caribbean) are included in the unhealthy class.
    """
    print(f"=" * 60)
    print(f"ReefNet Caribbean Curation Pipeline")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=" * 60)
    print()

    # Build source URL lookup
    print("Loading CoralNet source URLs...")
    source_lookup = build_source_lookup(sources_csv)
    print(f"  Found {len(source_lookup)} valid sources")
    print()

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # --------------------------------------------------------
    # PASS 1: Stream through CSV, collect annotations by class
    # --------------------------------------------------------
    # We group annotations by (source, image_name) to later
    # pick the best images for each class.

    print(f"Streaming through annotations CSV...")
    print(f"  File: {annotations_csv}")
    print()

    # Structure: class -> image_key -> [annotations]
    # To keep memory manageable, we store only what we need per annotation
    class_images = {
        'healthy_coral': defaultdict(list),
        'unhealthy_coral': defaultdict(list),
        'not_coral': defaultdict(list),
    }

    # Counters for the summary report
    total_rows = 0
    caribbean_rows = 0
    classified_rows = 0
    class_counts = Counter()
    genus_counts = Counter()
    noncoral_label_counts = Counter()
    condition_counts = Counter()
    ecoregion_counts = Counter()

    with open(annotations_csv, 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            total_rows += 1

            # Progress indicator every 1M rows
            if total_rows % 1_000_000 == 0:
                print(f"  Processed {total_rows:,} rows...")

            # Filter by region
            ecoregion = row.get('Ecoregion', '')
            condition = row.get('Condition_indication', '')
            in_caribbean = is_caribbean(ecoregion)

            # Allow global unhealthy annotations through if flag is set
            if not in_caribbean:
                if include_global_unhealthy and condition in UNHEALTHY_CONDITIONS:
                    label = row.get('Sorted_ReefNet_label', '')
                    if label in USVI_GENERA:
                        pass  # Let it through for unhealthy class
                    else:
                        continue
                else:
                    continue

            caribbean_rows += 1
            ecoregion_counts[ecoregion] += 1

            # Classify this annotation
            cls = classify_annotation(row)
            if cls is None:
                continue

            classified_rows += 1
            class_counts[cls] += 1

            # Track genus/label stats
            label = row.get('Sorted_ReefNet_label', '')
            condition = row.get('Condition_indication', '')

            if cls in ('healthy_coral', 'unhealthy_coral'):
                genus_counts[label] += 1
                if condition and condition != 'NA':
                    condition_counts[condition] += 1
            else:
                noncoral_label_counts[label] += 1

            # Store annotation data grouped by image
            source = row.get('CoralNet_source', '')
            image_name = row.get('Image_name', '')
            image_key = f"{source}||{image_name}"

            annotation = {
                'source': source,
                'image_name': image_name,
                'row_px': row.get('Row', ''),
                'col_px': row.get('Column', ''),
                'label': label,
                'condition': condition if condition != 'NA' else '',
                'ecoregion': ecoregion,
                'lat': row.get('Latitude', ''),
                'lon': row.get('Longitude', ''),
                'source_url': source_lookup.get(source, {}).get('url', ''),
                'images_url': source_lookup.get(source, {}).get('images_url', ''),
            }

            class_images[cls][image_key].append(annotation)

    print(f"  Done! Processed {total_rows:,} total rows")
    print()

    # --------------------------------------------------------
    # PASS 2: Score images and select best candidates
    # --------------------------------------------------------
    # For each class, we want images where most annotation points
    # belong to that class (high "purity"). We also prefer images
    # with multiple annotations of the same class (more crop options).

    print("Scoring and ranking images per class...")
    print()

    manifests = {}

    for cls in ['healthy_coral', 'unhealthy_coral', 'not_coral']:
        images = class_images[cls]

        # Build list of (image_key, annotation_count, annotations)
        image_list = []
        for image_key, annotations in images.items():
            image_list.append({
                'image_key': image_key,
                'annotation_count': len(annotations),
                'annotations': annotations,
            })

        # Sort by number of annotations (more = better coverage)
        image_list.sort(key=lambda x: x['annotation_count'], reverse=True)

        manifests[cls] = image_list

        print(f"  {cls}: {len(image_list):,} unique images, "
              f"{class_counts[cls]:,} total annotations")

    print()

    # --------------------------------------------------------
    # PASS 3: Write manifest CSVs
    # --------------------------------------------------------
    print("Writing manifest CSVs...")

    manifest_fields = [
        'class', 'source', 'image_name', 'row_px', 'col_px',
        'label', 'condition', 'ecoregion', 'lat', 'lon',
        'source_url', 'images_url', 'patch_size'
    ]

    for cls, image_list in manifests.items():
        manifest_path = os.path.join(output_dir, f'{cls}_manifest.csv')

        row_count = 0
        with open(manifest_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=manifest_fields)
            writer.writeheader()

            for image_info in image_list:
                for ann in image_info['annotations']:
                    writer.writerow({
                        'class': cls,
                        'source': ann['source'],
                        'image_name': ann['image_name'],
                        'row_px': ann['row_px'],
                        'col_px': ann['col_px'],
                        'label': ann['label'],
                        'condition': ann['condition'],
                        'ecoregion': ann['ecoregion'],
                        'lat': ann['lat'],
                        'lon': ann['lon'],
                        'source_url': ann['source_url'],
                        'images_url': ann['images_url'],
                        'patch_size': PATCH_SIZE,
                    })
                    row_count += 1

        print(f"  {manifest_path}")
        print(f"    {row_count:,} annotation rows")

    print()

    # --------------------------------------------------------
    # PASS 4: Write summary report
    # --------------------------------------------------------
    report_path = os.path.join(output_dir, 'curation_report.txt')

    report_lines = [
        "=" * 60,
        "REEFNET CARIBBEAN CURATION REPORT",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 60,
        "",
        "SCOPE",
        "-----",
        f"Total CSV rows processed: {total_rows:,}",
        f"Caribbean rows: {caribbean_rows:,}",
        f"Classified (relevant to 3-class model): {classified_rows:,}",
        "",
        "ECOREGIONS INCLUDED",
        "-------------------",
    ]
    for eco, count in ecoregion_counts.most_common():
        report_lines.append(f"  {eco}: {count:,}")

    report_lines += [
        "",
        "CLASS TOTALS",
        "------------",
        f"  Healthy Coral:   {class_counts['healthy_coral']:,} annotations "
        f"across {len(manifests['healthy_coral']):,} images",
        f"  Unhealthy Coral: {class_counts['unhealthy_coral']:,} annotations "
        f"across {len(manifests['unhealthy_coral']):,} images",
        f"  Not Coral:       {class_counts['not_coral']:,} annotations "
        f"across {len(manifests['not_coral']):,} images",
        "",
        "HEALTHY CORAL - GENUS BREAKDOWN",
        "--------------------------------",
    ]
    for g, c in genus_counts.most_common():
        report_lines.append(f"  {g}: {c:,}")

    report_lines += [
        "",
        "UNHEALTHY CORAL - CONDITION BREAKDOWN",
        "--------------------------------------",
    ]
    if condition_counts:
        for cond, c in condition_counts.most_common():
            report_lines.append(f"  {cond}: {c:,}")
    else:
        report_lines.append("  (No condition-tagged annotations found in Caribbean subset)")

    report_lines += [
        "",
        "NOT CORAL - TOP LABELS",
        "----------------------",
    ]
    for label, c in noncoral_label_counts.most_common(20):
        report_lines.append(f"  {label}: {c:,}")

    report_lines += [
        "",
        "DATASET BALANCE ASSESSMENT",
        "--------------------------",
    ]

    healthy_count = class_counts['healthy_coral']
    unhealthy_count = class_counts['unhealthy_coral']
    noncoral_count = class_counts['not_coral']

    report_lines.append(f"  Target per class: ~{TARGET_PER_CLASS} images")
    report_lines.append(f"  Healthy Coral:   {len(manifests['healthy_coral']):,} images available "
                       f"({'SUFFICIENT' if len(manifests['healthy_coral']) >= TARGET_PER_CLASS else 'NEEDS MORE'})")
    report_lines.append(f"  Unhealthy Coral: {len(manifests['unhealthy_coral']):,} images available "
                       f"({'SUFFICIENT' if len(manifests['unhealthy_coral']) >= TARGET_PER_CLASS else 'NEEDS MORE'})")
    report_lines.append(f"  Not Coral:       {len(manifests['not_coral']):,} images available "
                       f"({'SUFFICIENT' if len(manifests['not_coral']) >= TARGET_PER_CLASS else 'NEEDS MORE'})")

    report_lines += [
        "",
        "RECOMMENDATIONS",
        "---------------",
    ]

    if unhealthy_count == 0:
        report_lines += [
            "  WARNING: No bleached/dead annotations found in Caribbean subset.",
            "  To build the 'Unhealthy Coral' class, consider:",
            "    1. Use your existing 53 bleached training images",
            "    2. Include global ReefNet dead/bleached annotations (especially",
            "       Acropora Dead: ~5,116 annotations outside Caribbean)",
            "    3. Source NOAA SCTLD survey images from USVI",
            "    4. Request field images from UVI research team",
            "    5. Re-run this script with --include-global-unhealthy flag",
        ]

    report_lines += [
        "",
        "NEXT STEPS",
        "----------",
        "  1. Run download_images.py to fetch images from CoralNet",
        "  2. Run crop_patches.py to extract 224x224 patches",
        "  3. Visually review a sample of ~50 patches per class",
        "  4. Address unhealthy coral data gap (see recommendations)",
        "  5. Balance dataset and begin retraining",
        "",
        "=" * 60,
    ]

    report_text = '\n'.join(report_lines)

    with open(report_path, 'w') as f:
        f.write(report_text)

    print(f"Summary report: {report_path}")
    print()
    print(report_text)


# ============================================================
# ALSO: Generate the download + crop helper scripts
# ============================================================

def generate_download_script(output_dir):
    """
    Generate a standalone download_images.py script that the user
    runs on their local machine to fetch images from CoralNet.
    """
    script_path = os.path.join(output_dir, 'download_images.py')

    script = '''#!/usr/bin/env python3
"""
Download ReefNet Images from CoralNet
======================================
Reads manifest CSVs produced by curate_reefnet_caribbean.py and
downloads the referenced images from CoralNet.

Usage:
    python download_images.py --manifest-dir /path/to/manifests \\
                              --image-dir /path/to/save/images \\
                              --max-per-class 600

Requirements:
    pip install requests tqdm

Notes:
    - CoralNet images are publicly accessible via direct URL
    - Images are downloaded once and shared across classes
    - Respects a 0.5s delay between requests to be polite to CoralNet
    - Resumes where it left off if interrupted (skips existing files)
"""

import csv
import os
import time
import argparse
from collections import defaultdict

try:
    import requests
    from tqdm import tqdm
except ImportError:
    print("Please install required packages:")
    print("  pip install requests tqdm")
    exit(1)


# CoralNet image URL pattern
# Images can typically be accessed at:
# https://coralnet.ucsd.edu/media/images/{image_name}
# But the exact URL pattern may vary by source. We'll try common patterns.

CORALNET_URL_PATTERNS = [
    "https://coralnet.ucsd.edu/media/images/{image_name}",
]

REQUEST_DELAY = 0.5  # seconds between downloads (be polite)


def download_image(image_name, output_path, session):
    """Try to download an image from CoralNet. Returns True if successful."""
    if os.path.exists(output_path):
        return True  # Already downloaded

    for pattern in CORALNET_URL_PATTERNS:
        url = pattern.format(image_name=image_name)
        try:
            resp = session.get(url, timeout=30)
            if resp.status_code == 200:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(resp.content)
                return True
        except Exception as e:
            continue

    return False


def main():
    parser = argparse.ArgumentParser(description='Download ReefNet images from CoralNet')
    parser.add_argument('--manifest-dir', required=True,
                       help='Directory containing manifest CSVs')
    parser.add_argument('--image-dir', required=True,
                       help='Directory to save downloaded images')
    parser.add_argument('--max-per-class', type=int, default=600,
                       help='Max unique images to download per class (default: 600)')
    args = parser.parse_args()

    # Collect unique images needed per class
    class_images = defaultdict(set)  # class -> set of (source, image_name)

    for manifest_file in ['healthy_coral_manifest.csv',
                          'unhealthy_coral_manifest.csv',
                          'not_coral_manifest.csv']:
        path = os.path.join(args.manifest_dir, manifest_file)
        if not os.path.exists(path):
            print(f"  Skipping {manifest_file} (not found)")
            continue

        cls = manifest_file.replace('_manifest.csv', '')
        with open(path, 'r') as f:
            reader = csv.DictReader(f)
            seen = set()
            for row in reader:
                img_key = (row['source'], row['image_name'])
                if img_key not in seen and len(seen) < args.max_per_class:
                    seen.add(img_key)
                    class_images[cls].add(img_key)

    # Flatten to unique images across all classes
    all_images = set()
    for imgs in class_images.values():
        all_images.update(imgs)

    print(f"Images to download: {len(all_images)}")
    for cls, imgs in class_images.items():
        print(f"  {cls}: {len(imgs)} unique images")

    # Download
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'ReefMonitor-Research/1.0 (coral health monitoring project)'
    })

    failed = []
    for source, image_name in tqdm(sorted(all_images), desc="Downloading"):
        # Organize by source
        output_path = os.path.join(args.image_dir, source, image_name)

        success = download_image(image_name, output_path, session)
        if not success:
            failed.append((source, image_name))

        time.sleep(REQUEST_DELAY)

    print(f"\\nDone! Downloaded {len(all_images) - len(failed)}/{len(all_images)} images")
    if failed:
        print(f"Failed: {len(failed)} images")
        fail_path = os.path.join(args.image_dir, 'failed_downloads.txt')
        with open(fail_path, 'w') as f:
            for source, name in failed:
                f.write(f"{source}\\t{name}\\n")
        print(f"Failed list saved to: {fail_path}")


if __name__ == '__main__':
    main()
'''

    with open(script_path, 'w') as f:
        f.write(script)

    print(f"  Download script: {script_path}")


def generate_crop_script(output_dir):
    """
    Generate a standalone crop_patches.py script that extracts
    224x224 patches from downloaded images at annotation coordinates.
    """
    script_path = os.path.join(output_dir, 'crop_patches.py')

    script = '''#!/usr/bin/env python3
"""
Crop 224x224 Patches from Downloaded Images
=============================================
Reads manifest CSVs and crops patches centered on each annotation point.

Usage:
    python crop_patches.py --manifest-dir /path/to/manifests \\
                           --image-dir /path/to/downloaded/images \\
                           --output-dir /path/to/training_patches \\
                           --max-per-class 500

Output structure:
    output_dir/
        healthy_coral/
            {source}_{image}_{row}_{col}.jpg
        unhealthy_coral/
            ...
        not_coral/
            ...

Requirements:
    pip install Pillow tqdm
"""

import csv
import os
import argparse
from collections import Counter

try:
    from PIL import Image
    from tqdm import tqdm
except ImportError:
    print("Please install required packages:")
    print("  pip install Pillow tqdm")
    exit(1)


PATCH_SIZE = 224


def crop_patch(image_path, center_row, center_col, patch_size=PATCH_SIZE):
    """
    Crop a square patch centered at (center_row, center_col).

    Row = Y coordinate (pixels from top)
    Col = X coordinate (pixels from left)

    Returns a PIL Image or None if the crop would be out of bounds.
    """
    try:
        img = Image.open(image_path)
    except Exception:
        return None

    width, height = img.size
    half = patch_size // 2

    # Calculate crop box (left, upper, right, lower)
    left = center_col - half
    upper = center_row - half
    right = center_col + half
    lower = center_row + half

    # Handle edge cases: shift the box if it goes out of bounds
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

    # Final bounds check
    if left < 0 or upper < 0 or right > width or lower > height:
        return None  # Image too small for this patch size

    if (right - left) != patch_size or (lower - upper) != patch_size:
        return None  # Couldn't get a full patch

    return img.crop((left, upper, right, lower))


def main():
    parser = argparse.ArgumentParser(description='Crop training patches from images')
    parser.add_argument('--manifest-dir', required=True,
                       help='Directory containing manifest CSVs')
    parser.add_argument('--image-dir', required=True,
                       help='Directory with downloaded images (organized by source)')
    parser.add_argument('--output-dir', required=True,
                       help='Directory to save cropped patches')
    parser.add_argument('--max-per-class', type=int, default=500,
                       help='Max patches per class (default: 500)')
    args = parser.parse_args()

    manifests = [
        ('healthy_coral', 'healthy_coral_manifest.csv'),
        ('unhealthy_coral', 'unhealthy_coral_manifest.csv'),
        ('not_coral', 'not_coral_manifest.csv'),
    ]

    stats = Counter()

    for cls, manifest_file in manifests:
        manifest_path = os.path.join(args.manifest_dir, manifest_file)
        if not os.path.exists(manifest_path):
            print(f"Skipping {cls} (manifest not found)")
            continue

        cls_output = os.path.join(args.output_dir, cls)
        os.makedirs(cls_output, exist_ok=True)

        # Read manifest
        annotations = []
        with open(manifest_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                annotations.append(row)

        print(f"\\n{cls}: {len(annotations)} annotations in manifest")

        cropped = 0
        skipped = 0
        missing = 0

        for ann in tqdm(annotations, desc=f"Cropping {cls}"):
            if cropped >= args.max_per_class:
                break

            source = ann['source']
            image_name = ann['image_name']
            row_px = int(float(ann['row_px']))
            col_px = int(float(ann['col_px']))

            # Find the image file
            image_path = os.path.join(args.image_dir, source, image_name)
            if not os.path.exists(image_path):
                missing += 1
                continue

            # Crop patch
            patch = crop_patch(image_path, row_px, col_px)
            if patch is None:
                skipped += 1
                continue

            # Save patch
            safe_source = source.replace('/', '_').replace(' ', '_')[:30]
            safe_image = os.path.splitext(image_name)[0].replace('/', '_')[:30]
            patch_name = f"{safe_source}_{safe_image}_{row_px}_{col_px}.jpg"
            patch_path = os.path.join(cls_output, patch_name)

            patch.save(patch_path, 'JPEG', quality=95)
            cropped += 1

        stats[cls] = cropped
        print(f"  Cropped: {cropped}, Skipped: {skipped}, Missing images: {missing}")

    print(f"\\n{'='*40}")
    print("CROP SUMMARY")
    print(f"{'='*40}")
    for cls, count in stats.items():
        print(f"  {cls}: {count} patches")
    print(f"\\nPatches saved to: {args.output_dir}")
    print("Next step: visually review a sample of ~50 patches per class")


if __name__ == '__main__':
    main()
'''

    with open(script_path, 'w') as f:
        f.write(script)

    print(f"  Crop script: {script_path}")


# ============================================================
# CLI ENTRY POINT
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='Curate ReefNet Caribbean data for 3-class coral health model',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
    python curate_reefnet_caribbean.py \\
        --annotations ~/Data/coral/raw/reefnet_data/All_ReefNet_annotations.csv \\
        --sources ~/Data/coral/raw/reefnet_data/Overview_Sources_for_Image_Download.csv \\
        --output ~/Data/coral/processed/caribbean_3class

Optional flags:
    --include-global-unhealthy   Also include bleached/dead annotations
                                 from non-Caribbean ecoregions to supplement
                                 the unhealthy class
        """
    )

    parser.add_argument('--annotations', required=True,
                       help='Path to All_ReefNet_annotations.csv')
    parser.add_argument('--sources', default=None,
                       help='Path to Overview_Sources_for_Image_Download.csv')
    parser.add_argument('--output', required=True,
                       help='Output directory for manifests and reports')
    parser.add_argument('--include-global-unhealthy', action='store_true',
                       help='Include global (non-Caribbean) bleached/dead annotations')

    args = parser.parse_args()

    # Validate inputs
    if not os.path.exists(args.annotations):
        print(f"ERROR: Annotations file not found: {args.annotations}")
        return

    if args.include_global_unhealthy:
        print("NOTE: Including global unhealthy coral annotations")
        print("      (not just Caribbean) to supplement the unhealthy class")
        print()

    # Run the main pipeline
    run_pipeline(args.annotations, args.sources, args.output,
                 include_global_unhealthy=args.include_global_unhealthy)

    # Generate helper scripts
    print("Generating helper scripts...")
    generate_download_script(args.output)
    generate_crop_script(args.output)
    print()
    print("Done! See curation_report.txt for full details.")


if __name__ == '__main__':
    main()
