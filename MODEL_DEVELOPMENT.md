# Model Development Log

Tracking model versions, training history, and development decisions for Reef Monitor.

---

## V1 — Binary Health Classifier (CURRENT PRODUCTION)

**Status:** Deployed, production-ready
**File:** `public/coral_model.onnx` (77MB)
**Backup:** `~/Data/coral/models/v1/coral_health_v1.onnx`

### Architecture
- Custom CNN, 19,396,801 parameters
- Built in Keras/TensorFlow, converted to ONNX via tf2onnx
- Input: 224x224x3 RGB, normalized to [0, 1]
- Output: single sigmoid (probability of healthy)
- Inference: ~1 sec on mobile (WASM backend)

### Training Data
- 9,292 total images (train + test)
- Test set: 923 images (485 bleached, 438 healthy)
- Training set: ~8,369 images

### Performance (on test set)
- Overall accuracy: 80.82%
- Bleached detection: precision 85.16%, recall 76.91%
- Healthy detection: precision 76.91%, recall 85.16%
- Full report: `RESEARCH_METRICS_REPORT.txt`

### Training Notebook
- Original notebook not found (repo, Data folder, GitHub, Kaggle checked)
- `.ipynb` is in `.gitignore`, so it existed locally at one point
- **RESOLVED:** Full architecture extracted directly from ONNX file (March 16, 2026)

### Reconstructed Architecture (from ONNX inspection)
```
Input(224, 224, 3)
  Conv2D(32, 3x3) + BatchNorm + ReLU + MaxPool(2x2)    → 112x112x32
  Conv2D(64, 3x3) + BatchNorm + ReLU + MaxPool(2x2)    → 56x56x64
  Conv2D(128, 3x3) + BatchNorm + ReLU + MaxPool(2x2)   → 28x28x128
  Conv2D(256, 3x3) + BatchNorm + ReLU + MaxPool(2x2)   → 14x14x256
  Flatten                                                → 36,864
  Dense(512) + ReLU                                      → 512   (18.8M params — bulk of model)
  Dense(256) + ReLU                                      → 256
  Dense(1) + Sigmoid                                     → 1     (v2: change to Dense(3) + Softmax)
```

---

## V2 — Three-Class Health Classifier (IN DEVELOPMENT)

**Status:** First training run complete — 74.6% val accuracy (target: ≥80%)
**Branch:** `feature/v2-health-model`
**Goal:** Healthy Coral / Bleached Coral / Not Coral

### Design Decision (March 16, 2026)
Chose single three-class model over two-stage gatekeeper approach:
- Single download, single inference call, simpler deployment
- Output layer changes from sigmoid to 3-way softmax
- Existing healthy/bleached data carries forward unchanged
- "Not coral" acts as a rejection class for non-coral inputs

### Data Plan
| Class | Source | Target | Status |
|-------|--------|--------|--------|
| Healthy coral | Kaggle dataset (`~/Data/coral_classification/`) | 3,504 train + 500 val + 438 test | Found |
| Bleached coral | Kaggle dataset (`~/Data/coral_classification/`) | 3,880 train + 485 val + 485 test | Found |
| Not coral | iNaturalist Caribbean downloads | 600-800 initial, 2000+ eventual | 463 downloaded (round 1) |

### Not-Coral Dataset (iNaturalist) — Round 1 Results (March 16, 2026)
- Download script: `download_not_coral_images.py`
- Data location: `~/Data/coral/raw/not_coral_inat/images/`
- All images: 224x224, center-cropped, JPEG
- Caribbean-filtered (geographic bounding box)
- Metadata preserved per subcategory in `~/Data/coral/raw/not_coral_inat/metadata/`

| Subcategory | Taxon ID | Target | Actual | Notes |
|-------------|----------|--------|--------|-------|
| Sponges (Porifera) | 48824 | 100 | 100 | Complete |
| Sea Fans (Gorgonia) | 120132 | 85 | 85 | Complete |
| Seagrass (Thalassia) | 118509 | 85 | 85 | Complete |
| Algae (Dictyota) | 51021 | 85 | 23 | Narrow genus, broaden to higher taxon |
| Sea Urchins (Diadema) | 52290 | 85 | 85 | Complete |
| Parrotfish (Scaridae) | 49692 | 85 | 0 | FAILED — retry with species-level IDs |
| Anemones (Actiniaria) | 47533 | 85 | 85 | Complete |
| **Total** | | **610** | **463** | **Usable for initial v2 training** |

**TODO — Round 2 backfill:**
- Parrotfish: try Sparisoma viride (Stoplight) or Scarus vetula (Queen)
- Algae: broaden from Dictyota genus to wider macroalgae taxa
- Consider adding: reef fish close-ups, sandy substrate, blurry/murky water shots

### Training Pipeline Changes (Implemented in `train_v2_health_model.py`)
1. Final layer: sigmoid -> 3-class softmax ✅
2. Loss function: binary crossentropy -> categorical crossentropy ✅
3. Output interpretation: single probability -> argmax of 3 probabilities ✅
4. Class weight balancing for imbalanced not_coral class (capped at 3.0x) ✅
5. Data augmentation matching v1: rotation (20°), width/height shift (0.2), horizontal+vertical flip, zoom (0.2) ✅
6. ONNX conversion via SavedModel export (from_keras has KeyError bug with newer TF) ✅
7. **TODO:** App inference code — update `CLASS_LABELS`, prediction logic in `App.js` and `BatchScanner.jsx`

### First Training Run (March 21, 2026)

**Config:**
- LR: 0.0001 (initial attempt at 0.001 diverged — accuracy dropped below random chance)
- Class weights: bleached 0.666, healthy 0.738, not_coral 3.0 (capped from raw 6.99)
- Epochs: 13 (early stopped, best at epoch 8)
- Hardware: CPU only (tensorflow-metal unavailable for Python 3.12)
- Time: ~25 minutes total (~2 min/epoch)
- Python: 3.12 via Homebrew (no conda/venv)

**Results (validation set, 1,031 images):**

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| bleached_coral | 77.9% | 67.0% | 72.1% | 485 |
| healthy_coral | 71.7% | 82.0% | 76.5% | 500 |
| not_coral | 81.0% | 73.9% | 77.3% | 46 |
| **Overall** | | | | **74.6% accuracy** |

**Confusion Matrix:**
```
                     Pred Bleached  Pred Healthy  Pred Not Coral
bleached_coral              325          153            7
healthy_coral                89          410            1
not_coral                     3            9           34
```

**Analysis:**
- Not_coral class is the strongest performer despite having fewest samples (370 train) — the model is learning this distinction well
- Bleached recall (67%) is the main weakness — 153 bleached images called healthy
- v1 had 80.82% accuracy with 2 classes; v2 at 74.6% with 3 classes is a reasonable starting point
- The 5.2 pp gap is likely closeable with more not_coral data and possibly a LR warmup schedule

**Saved models:**
- Keras: `~/Data/coral/models/v2/coral_health_v2_20260321_075556.keras`
- Best checkpoint: `~/Data/coral/models/v2/checkpoints/best_model.keras`
- ONNX: `~/Data/coral/models/v2/coral_health_v2.onnx` (100 MB)

**Lessons learned:**
- LR 0.001 is too aggressive for this architecture + data — caused divergence to <15% accuracy
- Uncapped class weights (~7x for not_coral) destabilize training — cap at 3.0
- tf2onnx `from_keras()` has a KeyError bug with newer TF — use SavedModel export + CLI conversion instead

### Data Folder Structure
```
~/Data/coral/
  raw/
    health-training-data/      # Original v1 labels (53 bleached, 78 healthy, 764 unknown)
    training-data/             # Species images (~3,900 across 10 coral species)
    reefnet_data/              # ReefNet annotations CSV (reference)
    not_coral_inat/            # iNaturalist not-coral downloads
      images/                  # Flat folder, all subcategories mixed
      metadata/                # JSON per subcategory
  models/
    v1/                        # Backup of production model + metrics
```

---

## Previous Dead Ends (Cleaned Up March 16, 2026)

These approaches were attempted but never produced usable training images:

- **CoralNet downloads** — `scripts/download_not_coral.py` tried to crop patches from CoralNet source images. Downloads consistently failed (581/581 failed).
- **ReefNet Caribbean curation** — `scripts/curate_reefnet_caribbean.py` and `scripts/build_not_coral_manifest.py` produced well-structured manifests but depended on CoralNet image access which was blocked.
- **Folders removed:** `processed/caribbean_3class/`, `processed/caribbean_3class_with_global_unhealthy/`, `processed/health_model_v2/` (empty training folders + failed downloads)

The iNaturalist API approach (`download_not_coral_images.py`) is working reliably and is the current path forward.

---

## Checklist Before V2 Training

- [x] ~~Locate v1 training notebook~~ — Not found; architecture extracted from ONNX instead
- [x] Back up v1 model to `~/Data/coral/models/v1/` (March 16, 2026)
- [x] Download not-coral images — 463 of 610 target (parrotfish failed, algae limited)
- [x] Locate original healthy/bleached training data — **FOUND** (March 16, 2026)
  - Location: `~/Data/coral_classification/` (copied from Windows machine)
  - Training: 7,384 (3,880 bleached + 3,504 healthy)
  - Validation: 985 (485 bleached + 500 healthy)
  - Testing: 923 (485 bleached + 438 healthy)
  - Total: 9,293 images
  - Original notebook: `01_data_exploration.ipynb` (also recovered from Windows)
- [ ] Visual review of not-coral images (remove mislabeled)
- [x] Create v2 training script — `train_v2_health_model.py`
- [x] Assemble training data into `~/Data/coral/processed/health_model_v2/` (March 17, 2026)
  - Training: 7,754 (3,880 bleached + 3,504 healthy + 370 not_coral)
  - Validation: 1,031 (485 bleached + 500 healthy + 46 not_coral)
  - Testing: 970 (485 bleached + 438 healthy + 47 not_coral)
- [x] First training run — 74.6% val accuracy (March 21, 2026) — see results above
- [x] Convert to ONNX — `~/Data/coral/models/v2/coral_health_v2.onnx` (100 MB)
- [ ] Round 2 data backfill (parrotfish + broader algae) → reassemble → retrain
- [ ] Retrain with expanded dataset (target: ≥80%)
- [ ] Test ONNX model in browser
- [ ] Update app inference code (App.js, BatchScanner.jsx)
- [ ] Merge `feature/v2-health-model` → `main` when ready
