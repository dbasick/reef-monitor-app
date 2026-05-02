#!/usr/bin/env python3
"""
Build a Balanced "Not Coral" Training Manifest
================================================
Reads the full ReefNet annotations CSV and produces a curated,
diverse manifest for the "Not Coral" class.

Strategy:
    - Caribbean ecoregions only (matches the healthy coral data)
    - Stratified sampling across non-coral label types so the model
      sees a good mix of algae, sand, sponges, seagrass, rock, etc.
    - One annotation per image to maximize visual diversity
      (avoids many crops from the same photo)
    - Targets a configurable number of total samples (default 600),
      distributed proportionally across label categories with a
      minimum floor per category

Usage:
    python build_not_coral_manifest.py \
        --annotations /path/to/All_ReefNet_annotations.csv \
        --sources /path/to/Overview_Sources_for_Image_Download.csv \
        --output /path/to/health_model_v2/manifests \
        --target 600

Output:
    not_coral_manifest.csv  — curated annotations ready for download + crop
    not_coral_sampling_report.txt — breakdown of what was selected
"""

import csv
import os
import argparse
import random
from collections import defaultdict, Counter
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

CARIBBEAN_KEYWORDS = ['caribbean', 'antilles', 'bahamian']

NOT_CORAL_CATEGORIES = {'Algae', 'Abiotic background', 'Other biota'}

# Labels to exclude (too ambiguous or not useful for training)
EXCLUDED_LABELS = {'Unsorted', 'Unknown', 'Shadow', 'Water'}

# Group similar labels into broader training categories
# This ensures the model sees a good spread of "not coral" types
LABEL_GROUPS = {
    'algae_turf': {'Turf algae'},
    'algae_macro': {'Macroalgae', 'Phaeophyceae', 'Chlorophyta', 'Rhodophyta'},
    'algae_coralline': {'Corallinales'},
    'algae_cyano': {'Cyanobacteria'},
    'sediment': {'Sediment'},
    'hard_substrate': {'Hard substrate', 'Rubble'},
    'seagrass': {'Seagrass'},
    'sponge': {'Porifera'},
    'soft_coral': {'Octocorallia', 'Millepora', 'Other hydrozoa'},
    'other_inverts': {'Zoantharia', 'Actiniaria', 'Echinoidea',
                      'Tunicata', 'Other invertrebrate'},
    'human_objects': {'Human objects'},
}

# Reverse lookup: label -> group
LABEL_TO_GROUP = {}
for group, labels in LABEL_GROUPS.items():
    for label in labels:
        LABEL_TO_GROUP[label] = group

# Minimum samples per group (ensures rare categories are represented)
MIN_PER_GROUP = 20

# Random seed for reproducibility
RANDOM_SEED = 42

PATCH_SIZE = 224


def is_caribbean(ecoregion):
    if not ecoregion:
        return False
    eco_lower = ecoregion.lower()
    return any(kw in eco_lower for kw in CARIBBEAN_KEYWORDS)


def build_source_lookup(sources_csv):
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
                }
    return lookup


def main():
    parser = argparse.ArgumentParser(
        description='Build balanced Not Coral training manifest')
    parser.add_argument('--annotations', required=True,
                       help='Path to All_ReefNet_annotations.csv')
    parser.add_argument('--sources', default=None,
                       help='Path to Overview_Sources_for_Image_Download.csv')
    parser.add_argument('--output', required=True,
                       help='Output directory for manifest')
    parser.add_argument('--target', type=int, default=600,
                       help='Target total samples (default: 600)')
    args = parser.parse_args()

    random.seed(RANDOM_SEED)
    os.makedirs(args.output, exist_ok=True)

    source_lookup = build_source_lookup(args.sources)

    print(f"{'=' * 60}")
    print(f"Building Balanced 'Not Coral' Manifest")
    print(f"Target: {args.target} samples")
    print(f"{'=' * 60}")
    print()

    # --------------------------------------------------------
    # PASS 1: Collect candidates grouped by label category
    # --------------------------------------------------------
    # Store one candidate per image (best annotation per image)
    # to maximize visual diversity

    print("Streaming annotations (Caribbean non-coral only)...")

    # group -> {image_key -> annotation}
    group_candidates = defaultdict(dict)
    ungrouped_labels = Counter()
    total_scanned = 0

    with open(args.annotations, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_scanned += 1
            if total_scanned % 1_000_000 == 0:
                print(f"  Scanned {total_scanned:,} rows...")

            # Caribbean only
            if not is_caribbean(row.get('Ecoregion', '')):
                continue

            # Non-coral categories only
            broad = row.get('Broad_category', '')
            if broad not in NOT_CORAL_CATEGORIES:
                continue

            label = row.get('Sorted_ReefNet_label', '')
            if label in EXCLUDED_LABELS:
                continue

            # Map to group
            group = LABEL_TO_GROUP.get(label)
            if group is None:
                ungrouped_labels[label] += 1
                continue

            # Use one annotation per image for diversity
            source = row.get('CoralNet_source', '')
            image_name = row.get('Image_name', '')
            image_key = f"{source}||{image_name}"

            # Keep first annotation per image per group
            if image_key not in group_candidates[group]:
                group_candidates[group][image_key] = {
                    'source': source,
                    'image_name': image_name,
                    'row_px': row.get('Row', ''),
                    'col_px': row.get('Column', ''),
                    'label': label,
                    'group': group,
                    'ecoregion': row.get('Ecoregion', ''),
                    'lat': row.get('Latitude', ''),
                    'lon': row.get('Longitude', ''),
                    'source_url': source_lookup.get(source, {}).get('url', ''),
                    'images_url': source_lookup.get(source, {}).get('images_url', ''),
                }

    print(f"  Done! Scanned {total_scanned:,} rows")
    print()

    # --------------------------------------------------------
    # PASS 2: Stratified sampling
    # --------------------------------------------------------
    # Distribute target across groups proportionally, with a
    # minimum floor per group

    print("Stratified sampling across label groups...")
    print()

    # Show available candidates per group
    available = {}
    total_available = 0
    for group in sorted(LABEL_GROUPS.keys()):
        count = len(group_candidates[group])
        available[group] = count
        total_available += count
        print(f"  {group}: {count:,} unique images available")

    print(f"\n  Total available: {total_available:,} unique images")
    print()

    # Calculate allocation per group
    target = args.target
    allocations = {}

    # First pass: give everyone the minimum
    remaining_target = target
    for group in LABEL_GROUPS:
        if available.get(group, 0) > 0:
            alloc = min(MIN_PER_GROUP, available[group])
            allocations[group] = alloc
            remaining_target -= alloc

    # Second pass: distribute remainder proportionally
    if remaining_target > 0:
        # Proportional to available count (minus already allocated)
        remaining_available = {
            g: available.get(g, 0) - allocations.get(g, 0)
            for g in LABEL_GROUPS
            if available.get(g, 0) > allocations.get(g, 0)
        }
        total_remaining_avail = sum(remaining_available.values())

        if total_remaining_avail > 0:
            for group, avail in remaining_available.items():
                extra = int(remaining_target * (avail / total_remaining_avail))
                extra = min(extra, avail)
                allocations[group] = allocations.get(group, 0) + extra

    # Verify and report
    print("Allocation plan:")
    total_allocated = 0
    for group in sorted(allocations, key=allocations.get, reverse=True):
        alloc = allocations[group]
        total_allocated += alloc
        print(f"  {group}: {alloc} samples "
              f"(from {available.get(group, 0)} available)")
    print(f"\n  Total allocated: {total_allocated}")
    print()

    # --------------------------------------------------------
    # PASS 3: Sample and write manifest
    # --------------------------------------------------------
    print("Sampling and writing manifest...")

    selected = []
    for group, alloc in allocations.items():
        candidates = list(group_candidates[group].values())
        random.shuffle(candidates)
        selected.extend(candidates[:alloc])

    # Shuffle the final selection
    random.shuffle(selected)

    # Write manifest
    manifest_path = os.path.join(args.output, 'not_coral_manifest.csv')
    manifest_fields = [
        'class', 'group', 'source', 'image_name', 'row_px', 'col_px',
        'label', 'ecoregion', 'lat', 'lon',
        'source_url', 'images_url', 'patch_size'
    ]

    with open(manifest_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=manifest_fields)
        writer.writeheader()
        for ann in selected:
            writer.writerow({
                'class': 'not_coral',
                'group': ann['group'],
                'source': ann['source'],
                'image_name': ann['image_name'],
                'row_px': ann['row_px'],
                'col_px': ann['col_px'],
                'label': ann['label'],
                'ecoregion': ann['ecoregion'],
                'lat': ann['lat'],
                'lon': ann['lon'],
                'source_url': ann['source_url'],
                'images_url': ann['images_url'],
                'patch_size': PATCH_SIZE,
            })

    print(f"  Manifest: {manifest_path}")
    print(f"  Total samples: {len(selected)}")
    print()

    # --------------------------------------------------------
    # Write sampling report
    # --------------------------------------------------------
    report_path = os.path.join(args.output, 'not_coral_sampling_report.txt')

    # Count what we actually selected per group
    selected_counts = Counter(ann['group'] for ann in selected)
    selected_labels = Counter(ann['label'] for ann in selected)

    lines = [
        "=" * 60,
        "NOT CORAL SAMPLING REPORT",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Target: {target} | Actual: {len(selected)}",
        "=" * 60,
        "",
        "SAMPLES PER GROUP",
        "-" * 30,
    ]
    for group, count in selected_counts.most_common():
        lines.append(f"  {group}: {count}")

    lines += ["", "SAMPLES PER LABEL", "-" * 30]
    for label, count in selected_labels.most_common():
        lines.append(f"  {label}: {count}")

    if ungrouped_labels:
        lines += ["", "UNGROUPED LABELS (excluded)", "-" * 30]
        for label, count in ungrouped_labels.most_common():
            lines.append(f"  {label}: {count}")

    lines += [
        "",
        "UNIQUE IMAGES SELECTED",
        "-" * 30,
        f"  {len(set(ann['image_name'] for ann in selected))} unique images",
        f"  from {len(set(ann['source'] for ann in selected))} CoralNet sources",
        "",
        "=" * 60,
    ]

    report_text = '\n'.join(lines)
    with open(report_path, 'w') as f:
        f.write(report_text)

    print(report_text)


if __name__ == '__main__':
    main()
