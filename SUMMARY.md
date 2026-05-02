# Reef Monitor — Project State Summary
**Last Updated:** March 21, 2026
**Developer:** Daniel Basick (dabasick@gmail.com)
**App Version:** 1.2.0 — Production Ready

---

## What This Project Is

An AI-powered Progressive Web App (PWA) for real-time coral health monitoring in the U.S. Virgin Islands. Users photograph coral underwater, and a machine learning model running entirely in their browser classifies the coral as **Healthy** or **Bleached** in ~1 second. Observations sync anonymously to a Firebase cloud database for community science data collection. The app works offline after first load.

**Production URL:** https://reef-monitor.netlify.app
**Dev/GitHub Pages URL:** https://dbasick.github.io/reef-monitor-app/
**Firebase Project:** reef-health-monitor-c7263
**GitHub Repo:** dbasick/reef-monitor-app

---

## Repository Structure

```
reef-monitor-app/
├── src/
│   ├── App.js                        # Main application logic + ONNX inference
│   ├── App.css                       # All styles (ocean theme)
│   ├── BatchScanner.jsx              # Batch scan UI (1–50 images per session)
│   ├── BatchScanner.css
│   ├── components/
│   │   ├── CoralGuide.jsx            # 13-species Caribbean coral reference guide
│   │   ├── CoralGuide.css
│   │   ├── LocationPicker.js         # Location selection modal (GPS/site/custom/general)
│   │   └── MapView.js                # Interactive community observation map (React Leaflet)
│   ├── data/
│   │   └── caribbean-corals.json     # Species data for the coral guide
│   └── firebase/
│       ├── config.js                 # Firebase credentials & initialization
│       ├── database.js               # All Firestore/Storage/Auth operations
│       └── saveBatchObservations.js  # (Older draft — logic now in database.js)
├── build/                            # Production build — THIS is what Netlify deploys
│   └── coral_model.onnx              # 77 MB binary health classifier (ONNX format)
├── public/
│   └── manifest.json                 # PWA config
├── download_coral_images.py          # Script used to assemble training data
├── README.md                         # Full user-facing documentation
├── PROJECT-SUMMARY.md                # Earlier project summary (Dec 2025 snapshot)
├── RESEARCH_METRICS_REPORT.txt       # Detailed model performance metrics
└── SUMMARY.md                        # ← This file
```

**Related repo (separate):** `~/projects/AI/reef-monitor-ml/` — the ML training pipeline (not the app)

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | React 18 (Create React App) | Hooks-based, no Redux |
| AI Inference | ONNX Runtime Web 1.14 | Runs in browser via WASM; `executionProviders: ['wasm']` |
| AI Model | `coral_model.onnx` | 77 MB, binary CNN, 19.4M params, 224×224 input |
| Mobile | Capacitor 6 | Included; not yet used for App Store deploy |
| Database | Firebase Firestore | NoSQL, us-east1, project: reef-health-monitor-c7263 |
| Storage | Firebase Storage | coral-images bucket |
| Auth | Firebase Anonymous Auth | Silent, no accounts required |
| Mapping | React Leaflet + OpenStreetMap | Satellite tiles, clustered markers |
| Hosting | Netlify (prod) | Manual deploy: drag `build/` folder |
| Dev Hosting | GitHub Pages | Auto via `npm run deploy` (gh-pages package) |
| Image Compression | browser-image-compression | Max 1 MB before upload |
| Icons | Lucide React |  |

---

## The Production AI Model

### What It Does
Binary classification: **Healthy Coral** vs **Bleached Coral**
Single output: probability of Healthy (0–1). Threshold = 0.5.

### Architecture
- Type: Custom Convolutional Neural Network (CNN)
- Parameters: 19,396,801
- Input: 224 × 224 × 3 RGB, normalized to [0, 1]
- Training data: 9,292 labeled images
- Training framework: Keras/TensorFlow → exported to ONNX via tf2onnx
- File: `build/coral_model.onnx` (77 MB)

### Performance (RESEARCH_METRICS_REPORT.txt)
- Test set: 923 images (485 bleached, 438 healthy)
- **Overall accuracy: 80.82%**
- Bleached Detection — Precision: 85.16%, Recall: 76.91%
- Healthy Detection — Precision: 76.91%, Recall: 85.16%
- F1-Score: 80.82% (both classes)
- Research-grade target: 85% — currently ~4.2 pp below
- **Key note:** Misses ~23% of bleached corals (false negatives). Model is suitable as a screening tool with manual follow-up on borderline cases.

### How Inference Works
1. User photo → resize to 224×224 on a canvas element
2. Normalize pixels to [0,1] → Float32Array tensor
3. Feed to ONNX Runtime Web session (WASM backend)
4. Read `output.data[0]` (healthy probability) → classify
5. Model is cached in browser after first 77 MB download → works offline

---

## Firebase Database Schema

### Collection: `observations`
All confirmed coral scans (single + batch).

| Field | Type | Description |
|---|---|---|
| userId | string | Anonymous Firebase UID |
| timestamp | Timestamp | Server-side Firestore timestamp |
| prediction | string | "Healthy Coral" or "Bleached Coral" |
| confidence | number | 0.0–1.0 AI confidence score |
| allPredictions | object | Full probability breakdown (batch only) |
| imageUrl | string | Firebase Storage download URL |
| imageId | string | Unique image filename ID |
| location.type | string | `gps` / `dive_site` / `custom_site` / `general` |
| location.coordinates | object | `{lat, lng}` — present for GPS & pre-populated dive sites |
| location.siteName | string | Dive site name (if applicable) |
| location.island | string | Island name (if applicable) |
| isSensitive | boolean | If true, hidden from public map |
| notes | string | Free-text observer notes |
| batchId | string | Groups batch images: `batch_{timestamp}` |
| batchIndex | number | Position within batch |
| source | string | `single` or `batch` |
| deviceInfo | object | `{userAgent, platform, isIOS}` |

### Collection: `needs_review`
Low-confidence images flagged by users during batch scan review.
Same schema as `observations`, plus:

| Field | Type | Description |
|---|---|---|
| reviewStatus | string | `pending` → will add `approved`/`rejected` |
| reviewReason | string | Currently always `low_confidence` |

### Firebase Storage Paths
```
coral-images/{imageId}.jpg                          ← single scans
observations/{userId}/{batchId}/{filename}           ← batch scan images
needs_review/{userId}/{batchId}/{filename}           ← flagged review images
```

### Security Rules
- **Read:** Public (anyone can read — powers the community map)
- **Create:** Any authenticated user (anonymous auth auto-triggers on app load)
- **Update/Delete:** Authenticated users only

### Pre-populated USVI Dive Sites (with GPS coords)
St. Thomas: Coki Beach, Cow and Calf Rocks, Wreck Alley, French Cap, Hull Bay, Lovango (North), Lovango (South)
St. Croix: Frederiksted Pier, Salt River Canyon, Cane Bay Wall
St. John: Trunk Bay, Haulover Bay, Annaberg

---

## Netlify Deployment Workflow

```bash
# 1. Build for Netlify
npm run build:netlify     # sets PUBLIC_URL=/ → outputs to build/

# 2. Deploy
# Drag the build/ folder to netlify.com dashboard
# OR use Netlify CLI: netlify deploy --prod --dir=build

# Dev deploy (GitHub Pages)
npm run deploy            # runs predeploy (build) then gh-pages -d build
```

- Production domain: reef-monitor.netlify.app (HTTPS auto via Let's Encrypt)
- No server-side code; pure static hosting
- The 77 MB ONNX file is served from Netlify's CDN → downloads fast, cached locally after first use
- PWA installable: "Add to Home Screen" on any mobile browser → native app experience

---

## App Features (v1.2.0 — January 2026)

### Live
- Binary health classification (Healthy vs Bleached) with confidence score
- Offline AI inference (browser WASM)
- **Batch Scanning Mode** — upload 1–50 images, lock one location, process entire batch
- **Review Queue System** — flag uncertain batch images for later expert review
- **Firebase scan history** — loads from cloud on startup, grouped by batch
- Enhanced Map View — clustered markers with count badges, scrollable image galleries
- Caribbean Coral Guide — 13 USVI species with photos, descriptions, IUCN status
- Anonymous Firebase cloud sync
- 4-level location privacy (GPS / dive site / custom site / general area)
- Sensitive location flag (hides from public map)
- PWA installable on iOS, Android, Desktop
- Local history fallback (localStorage, 50 scans)

### In Development
- **V2 three-class health model** — Healthy / Bleached / Not Coral (see V2 section below)
- Review queue admin interface (approve/reject flagged observations)
- Coral species identification AI (see reef-monitor-ml repo)

### Planned
- Multi-class health scoring (Healthy / Bleached / Dead / Diseased)
- CSV export for researchers
- Integration with NOAA CoRIS / AGRRA databases
- Offline dive site maps
- Multi-language support

---

## The Species Classifier (In-Development — Separate Repo)

Located at: `~/projects/AI/reef-monitor-ml/`

**Goal:** Identify 10 USVI coral species from a photo (not yet deployed).

**Architecture:** EfficientNet-B0, transfer learning from ImageNet, fully unfrozen, fine-tuned end-to-end.

**Current best result:**
- Val accuracy: 74.6% (epoch 71 of 83)
- TTA accuracy: **78.5%** (+3.9 pp from Test-Time Augmentation)
- Top-3 accuracy: 92.3%
- Target: 85% (currently 6.5 pp gap)
- Best model saved: `reef-monitor-ml/models/run_20260209_105148/`

**Per-species accuracy (baseline):**
| Species | Accuracy | Tier |
|---|---|---|
| Pillar coral | 88.5% | Strong |
| Smooth flower coral | 86.2% | Strong |
| Massive starlet coral | 85.1% | Strong |
| Brain coral | 84.9% | Strong |
| Staghorn coral | 84.5% | Strong |
| Elkhorn coral | 73.7% | Mid |
| Elliptical star coral | 65.3% | Weak |
| Lettuce coral | 64.6% | Weak |
| Mustard hill coral | 60.5% | Weak |
| Great star coral | 57.1% | Weak |

**Training config (baseline — best result):**
- Optimizer: Adam, LR 5e-5
- LR schedule: ReduceLROnPlateau (factor 0.5, patience 8)
- Loss: CategoricalCrossentropy + label smoothing 0.1
- Batch size: 16, image size: 224×224
- Augmentation: rotation 30°, shifts 20%, shear 15%, zoom 20%, h-flip
- Early stopping: patience 12
- Hardware: Apple M5 + tensorflow-metal

**7 Experiments Run — All Failed to Beat Baseline:**

| Experiment | Result vs Baseline | Key Lesson |
|---|---|---|
| Exp 1: Lower LR (2.5e-5) | −4.3 pp | LR 5e-5 is already optimal; going lower causes premature convergence |
| Exp 2: Cosine annealing | −17.3 pp | CosineDecay decays too fast for small datasets; ReduceLROnPlateau is correct |
| Exp 3: LR warmup | Crashed | Script error; abandoned |
| Exp 4: Higher resolution (299×299) | −5.0 pp | Coral morphology doesn't benefit from extra pixels; smaller batch hurt stability |
| Exp 5: Progressive unfreeze + Mixup + Focal loss + SWA | −66.3 pp | CATASTROPHIC: (1) training=False on backbone used ImageNet BN stats on coral = fatal; (2) Focal+Mixup+label smoothing = gradient starvation |
| Exp 6: Progressive unfreeze + Mixup (no focal) | −63.4 pp | Progressive unfreezing fails when source/target domain gap is too large (ImageNet → coral) |
| Exp 7: Baseline + Mixup only | −12.3 pp | Mixup is counterproductive for small, fine-grained, visually-similar datasets |

**Conclusion:** The accuracy gap is a **data problem, not a model problem.** All training-side optimizations failed. Next step is more labeled data — especially for the 4 weak species. The 2.9 GB ReefNet dataset (already on disk at `~/Data/coral/raw/reefnet_data/`) is the primary candidate for expansion.

---

## Datasets on Disk (`~/Data/`)

| Path | Count / Size | Notes |
|---|---|---|
| `coral_classification/` | 9,293 images | Kaggle healthy/bleached dataset (copied from Windows machine). Pre-split: Training/Validation/Testing with `bleached_corals/` and `healthy_corals/` subfolders |
| `coral/raw/health-training-data/` | ~898 images | Seed images (54 bleached, 78 healthy, 766 unknown) |
| `coral/raw/not_coral_inat/images/` | 463 images | iNaturalist not-coral downloads (Caribbean-filtered, 224x224) |
| `coral/raw/not_coral_inat/metadata/` | JSON files | Per-subcategory download metadata |
| `coral/raw/training-data/` (10 species) | 3,717 images | Species classifier dataset; 308–432 per species |
| `coral/raw/reefnet_data/` | 2.9 GB CSV + xlsx | Global reef survey annotations — NOT yet integrated |
| `coral/processed/health_model_v2/` | 9,755 images | Assembled v2 three-class dataset (Training/Validation/Testing) |
| `coral/models/v1/` | ONNX + metrics | Backup of production v1 model |
| `coral/models/v2/` | Keras + ONNX | V2 trained model, checkpoints, ONNX (100 MB) |

---

## Known Behaviors / Quirks

1. **First load:** 77 MB ONNX model downloads once, then cached in browser (IndexedDB)
2. **Welcome screen:** Shows only once per device (localStorage `reefMonitorWelcomeSeen` flag)
3. **History load:** Requires anonymous auth to complete before Firebase history is available; falls back to localStorage if Firebase fails
4. **Location modal:** Appears after every successful single scan
5. **Batch batchId:** Format is `batch_{Date.now()}` — not globally unique but collision-resistant
6. **Firebase Blaze plan:** Pay-as-you-go; current usage is well within free tier limits
7. **Public_URL issue:** Production Netlify build uses `npm run build:netlify` (sets `PUBLIC_URL=/`); GitHub Pages uses standard `npm run build` (uses homepage from package.json)
8. **`feature/species` branch:** Exists in git; reserved for species classifier integration when ready

---

## V2 Health Model — Three-Class Classifier (Active Development)

**Status:** First training run complete — 74.6% val accuracy. Needs more not_coral data to reach 80% target.
**Branch:** `feature/v2-health-model` (created March 21, 2026 — all v2 work lives here, `main` is untouched)
**Tracking details:** See `MODEL_DEVELOPMENT.md` for full architecture, data counts, and checklist

### Goal
Add a "Not Coral" rejection class to the binary health classifier so the model can identify when a photo isn't coral at all, rather than forcing a healthy/bleached prediction on non-coral images.

### Approach
Single three-class model (healthy_coral / bleached_coral / not_coral) with softmax output. Chose this over a two-stage gatekeeper for simpler deployment — one download, one inference call.

### First Training Run Results (March 21, 2026)
- **Overall val accuracy: 74.6%** (target: ≥80%, v1 baseline: 80.82%)
- Best epoch: 8 of 13 (early stopping triggered at epoch 13)
- Learning rate: 0.0001 (initial 0.001 caused divergence — model performed worse than random)
- Class weights capped at 3.0 (uncapped ~7x for not_coral destabilized training)
- Trained on CPU (~2 min/epoch, ~25 min total)
- ONNX converted: `~/Data/coral/models/v2/coral_health_v2.onnx` (100 MB)

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| bleached_coral | 77.9% | 67.0% | 72.1% | 485 |
| healthy_coral | 71.7% | 82.0% | 76.5% | 500 |
| not_coral | 81.0% | 73.9% | 77.3% | 46 |

**Key observations:**
- Not_coral class performs best (81% precision) despite having fewest training samples (370)
- Bleached recall is the weak spot (67%) — 153 bleached images misclassified as healthy
- 5.2 pp gap from v1 is expected given we added a third class with very limited data
- Main path to improvement: more not_coral data (round 2 backfill) + possibly higher LR with warmup

### Progress (as of March 21, 2026)
- [x] Downloaded 463 "not coral" images from iNaturalist API (Caribbean-filtered)
- [x] Backed up v1 production model to `~/Data/coral/models/v1/`
- [x] Created v2 training script (`train_v2_health_model.py`)
- [x] Assembled three-class dataset (7,754 train / 1,031 val / 970 test)
- [x] Added data augmentation matching v1 (rotation, flips, shifts, zoom)
- [x] First training run complete — 74.6% val accuracy (March 21, 2026)
- [x] ONNX conversion successful (100 MB)
- [ ] Visual review of not-coral images (remove mislabeled)
- [ ] Round 2 data backfill: parrotfish (species-level IDs) + broader algae taxa
- [ ] Retrain with expanded dataset (target: ≥80%)
- [ ] Test ONNX model in browser
- [ ] Update app inference code (App.js CLASS_LABELS, BatchScanner.jsx)
- [ ] Merge `feature/v2-health-model` → `main` when ready

### Key Files
| File | Purpose |
|---|---|
| `train_v2_health_model.py` | Training script (--assemble to build dataset, then run to train) |
| `download_not_coral_images.py` | iNaturalist image downloader for not-coral class |
| `MODEL_DEVELOPMENT.md` | Detailed architecture, data counts, training decisions |

### To Resume Work
```bash
cd ~/projects/ai/reef-monitor-app
git checkout feature/v2-health-model
python3.12 train_v2_health_model.py --lr 0.0001
```

---

## Developer Environment Notes

**IMPORTANT — read this before starting a new session.** Daniel has hit environment issues multiple times, so this section documents what actually works on this machine.

### Machine
- MacBook Pro with Apple M5 chip
- macOS (Homebrew-managed)
- Old Windows 10 Bootcamp machine also exists (used for original v1 training, data has been migrated)

### Python Setup
- **System Python (Homebrew):** Python 3.14 at `/opt/homebrew/opt/python@3.14/bin/python3` — TOO NEW for TensorFlow
- **Python 3.12 (Homebrew):** Works for TensorFlow. Always use `python3.12` explicitly, not `python` or `python3`
- **No conda/miniforge/anaconda installed** on this Mac (was only on the old Windows machine)
- **No virtual environments** needed for current setup — packages installed globally via `pip install --break-system-packages`
- The species classifier repo (`reef-monitor-ml/`) previously used tensorflow-metal with conda on the old machine. That environment does NOT exist on this Mac.

### GPU Status
- **tensorflow-metal is NOT available** for Python 3.12+ — Apple has not released compatible wheels
- Training runs on **CPU only** (~2 min/epoch for the health model)
- If GPU acceleration is needed, use **Kaggle notebooks** (free NVIDIA GPU) rather than trying to fix tensorflow-metal locally
- The species classifier SUMMARY.md mentions "Apple M5 + tensorflow-metal" — that was the OLD setup, not current

### Package Installation
```bash
# Always use python3.12 and --break-system-packages
python3.12 -m pip install <package> --break-system-packages

# Currently installed (for v2 training):
# tensorflow, tf2onnx, pillow, scikit-learn, matplotlib
```

### Git Branches
| Branch | Purpose | Status |
|---|---|---|
| `main` | Production app (v1 binary classifier) | PROTECTED — do not experiment here |
| `feature/v2-health-model` | V2 three-class health model development | Active — all v2 work goes here |
| `feature/species` | Species classifier integration (10-class) | On hold — data problem, not model problem |

### Common Gotchas
1. **Wrong Python version** — `python3` defaults to 3.14, which can't run TensorFlow. Always use `python3.12`.
2. **"conda not found"** — There is no conda on this Mac. Don't try to activate environments.
3. **Working on `main`** — Always `git checkout feature/v2-health-model` before making ML changes.
4. **`caffeinate`** — Use `caffeinate -is python3.12 <script>` for long training runs to prevent sleep.
5. **tensorflow-metal** — Don't bother trying to install it. It doesn't support Python 3.12+.
6. **LR 0.001 is too high** for v2 training — caused divergence (worse than random). Use `--lr 0.0001`.

---

## Immediate Next Steps (as of March 2026)

1. **V2 health model improvement** — Visual review of not-coral images, round 2 data backfill, retrain to hit ≥80% accuracy
2. **Species classifier data expansion** — Mine ReefNet CSV for great star, mustard hill, lettuce, and elliptical star coral images to close the 6.5 pp accuracy gap
3. **Admin review queue UI** — Build a web interface to approve/reject observations in `needs_review` Firestore collection

---

## Contact & Collaboration

**Developer:** Daniel Basick
**Email:** dabasick@gmail.com
**Purpose:** Marine conservation technology for USVI reef health monitoring
**License:** Proprietary — free for personal/educational/research use; commercial use requires permission

*For research data access, API keys, or collaboration inquiries, contact the developer directly.*
