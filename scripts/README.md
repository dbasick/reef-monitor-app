# Reef Monitor — Data Scripts

Scripts for curating training data for the 3-class coral health model (v2).

## Goal

Retrain the binary health model (Healthy vs Bleached) into a 3-class model:
- **Healthy Coral** — living coral tissue, normal coloration
- **Unhealthy Coral** — bleached, diseased, dead skeleton, rubble
- **Not Coral** — sand, algae, fish, seagrass, sponges, equipment, etc.

## Data Folder Structure

```
~/Data/coral/
├── raw/
│   ├── health-training-data/       # Original binary model training images
│   │   ├── healthy/ (77 images)
│   │   ├── bleached/ (53 images)
│   │   └── unknown/ (764 brain coral images, unsorted)
│   ├── training-data/              # Species classifier images (~3,500 total)
│   └── reefnet_data/               # ReefNet annotations + metadata
│       ├── All_ReefNet_annotations.csv (5.9M rows)
│       ├── Overview_Sources_for_Image_Download.csv
│       └── ReefNet_labelmapping.xlsx
│
└── processed/
    └── health_model_v2/
        ├── manifests/              # Curated annotation manifests
        │   ├── not_coral_manifest.csv
        │   └── not_coral_sampling_report.txt
        ├── downloads/images/       # Full images downloaded from CoralNet
        └── training_data/          # Final 224x224 patches for training
            ├── healthy_coral/
            ├── unhealthy_coral/
            └── not_coral/
                ├── algae_turf/
                ├── sediment/
                ├── sponge/
                └── ...
```

## Scripts

### 1. `curate_reefnet_caribbean.py`
Full pipeline that streams the ReefNet CSV and produces manifests for all three
classes. Caribbean-only by default; use `--include-global-unhealthy` to pull
in bleached/dead annotations from other regions.

```bash
python curate_reefnet_caribbean.py \
    --annotations ~/Data/coral/raw/reefnet_data/All_ReefNet_annotations.csv \
    --sources ~/Data/coral/raw/reefnet_data/Overview_Sources_for_Image_Download.csv \
    --output ~/Data/coral/processed/health_model_v2/manifests
```

### 2. `build_not_coral_manifest.py`
Builds a balanced, stratified "Not Coral" manifest from Caribbean ReefNet data.
Ensures diversity across 11 non-coral categories (algae, sand, sponges, etc.)
with one sample per image for maximum visual variety.

```bash
python build_not_coral_manifest.py \
    --annotations ~/Data/coral/raw/reefnet_data/All_ReefNet_annotations.csv \
    --sources ~/Data/coral/raw/reefnet_data/Overview_Sources_for_Image_Download.csv \
    --output ~/Data/coral/processed/health_model_v2/manifests \
    --target 600
```

### 3. `download_not_coral.py`
Downloads images from CoralNet and crops 224x224 patches at annotated
coordinates. Run this on your local machine (needs internet access).

```bash
# Dry run first to see what will be downloaded
python download_not_coral.py \
    --manifest ~/Data/coral/processed/health_model_v2/manifests/not_coral_manifest.csv \
    --image-dir ~/Data/coral/processed/health_model_v2/downloads/images \
    --output-dir ~/Data/coral/processed/health_model_v2/training_data/not_coral \
    --dry-run

# Then actually download + crop
python download_not_coral.py \
    --manifest ~/Data/coral/processed/health_model_v2/manifests/not_coral_manifest.csv \
    --image-dir ~/Data/coral/processed/health_model_v2/downloads/images \
    --output-dir ~/Data/coral/processed/health_model_v2/training_data/not_coral
```

## Class Data Sources

| Class | Source | Status |
|-------|--------|--------|
| Healthy Coral | Existing 77 images + species folders + ReefNet Caribbean | Available |
| Unhealthy Coral | Existing 53 bleached + USVI field data from UVI | Needs local sourcing |
| Not Coral | ReefNet Caribbean (595 curated samples) | Manifest ready |

## Requirements

```bash
pip install requests Pillow tqdm
```

## Notes

- ReefNet annotations are **point annotations**, not full-image labels.
  Each annotation marks a specific pixel location classified by experts.
  We crop 224x224 patches centered on those points.
- Caribbean subset has no bleached/dead condition tags — unhealthy coral
  data should come from USVI local sources (UVI research team, NOAA surveys).
- The `--target` flag controls how many samples per class. Start with 500-600
  to match the scale of your existing healthy/bleached data, then scale up.
