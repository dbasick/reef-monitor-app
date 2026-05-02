#!/usr/bin/env python3
"""
Reef Monitor — V2 Three-Class Health Model Training Script
============================================================
Trains a CNN to classify coral images into:
  1. Healthy Coral
  2. Bleached Coral
  3. Not Coral

Architecture matches V1 (extracted from ONNX):
  4x Conv2D blocks (32→64→128→256) with BatchNorm + MaxPool
  3x Dense layers (512→256→3)
  Changed: final Dense(1)+Sigmoid → Dense(3)+Softmax

Usage:
    # Full training
    python train_v2_health_model.py

    # Quick test (2 epochs, small subset)
    python train_v2_health_model.py --test

    # Custom settings
    python train_v2_health_model.py --epochs 30 --batch-size 16

    # Resume from checkpoint
    python train_v2_health_model.py --resume checkpoints/best_model.keras

Requirements:
    pip install tensorflow tensorflow-metal tf2onnx pillow scikit-learn matplotlib --break-system-packages
    (tensorflow-metal is optional — enables GPU acceleration on Apple Silicon Macs)
"""

import os
import argparse
import json
from pathlib import Path
from datetime import datetime


# =============================================================
# CONFIGURATION
# =============================================================

# Class labels (order matters — index maps to model output)
CLASS_NAMES = ['bleached_coral', 'healthy_coral', 'not_coral']
NUM_CLASSES = len(CLASS_NAMES)

# Image settings (must match V1)
IMG_SIZE = 224
IMG_SHAPE = (IMG_SIZE, IMG_SIZE, 3)

# Training defaults
DEFAULT_EPOCHS = 25
DEFAULT_BATCH_SIZE = 32
DEFAULT_LEARNING_RATE = 0.001
VALIDATION_SPLIT = 0.2

# Paths
# Original Kaggle dataset (already split into Training/Validation/Testing)
KAGGLE_DIR = Path.home() / "Data" / "coral_classification"
# iNaturalist not-coral images (flat folder, will be split programmatically)
NOT_CORAL_DIR = Path.home() / "Data" / "coral" / "raw" / "not_coral_inat" / "images"
# Assembled v2 training data (built by --assemble step)
DATA_DIR = Path.home() / "Data" / "coral" / "processed" / "health_model_v2"
OUTPUT_DIR = Path.home() / "Data" / "coral" / "models" / "v2"
CHECKPOINT_DIR = OUTPUT_DIR / "checkpoints"


def build_model():
    """
    Reconstruct the V1 architecture with 3-class output.

    Architecture (from ONNX inspection of V1):
        Conv2D(32) + BN + ReLU + MaxPool → 112x112x32
        Conv2D(64) + BN + ReLU + MaxPool → 56x56x64
        Conv2D(128) + BN + ReLU + MaxPool → 28x28x128
        Conv2D(256) + BN + ReLU + MaxPool → 14x14x256
        Flatten → 36,864
        Dense(512) + ReLU
        Dense(256) + ReLU
        Dense(3) + Softmax  ← V2 change (was Dense(1) + Sigmoid)
    """
    model = keras.Sequential([
        # Input
        layers.Input(shape=IMG_SHAPE),

        # Block 1: Conv(32) + BN + ReLU + MaxPool
        layers.Conv2D(32, (3, 3), padding='same'),
        layers.BatchNormalization(),
        layers.ReLU(),
        layers.MaxPooling2D((2, 2)),

        # Block 2: Conv(64) + BN + ReLU + MaxPool
        layers.Conv2D(64, (3, 3), padding='same'),
        layers.BatchNormalization(),
        layers.ReLU(),
        layers.MaxPooling2D((2, 2)),

        # Block 3: Conv(128) + BN + ReLU + MaxPool
        layers.Conv2D(128, (3, 3), padding='same'),
        layers.BatchNormalization(),
        layers.ReLU(),
        layers.MaxPooling2D((2, 2)),

        # Block 4: Conv(256) + BN + ReLU + MaxPool
        layers.Conv2D(256, (3, 3), padding='same'),
        layers.BatchNormalization(),
        layers.ReLU(),
        layers.MaxPooling2D((2, 2)),

        # Classifier head
        layers.Flatten(),
        layers.Dense(512, activation='relu'),
        layers.Dropout(0.5),    # From original v1 notebook
        layers.Dense(256, activation='relu'),
        layers.Dropout(0.3),    # From original v1 notebook
        layers.Dense(NUM_CLASSES, activation='softmax'),  # V2: 3-class softmax
    ])

    return model


def load_datasets(data_dir, batch_size=DEFAULT_BATCH_SIZE, test_mode=False):
    """
    Load training, validation, and test datasets from pre-split directory structure.

    Expected layout (matches original Kaggle structure + not_coral):
        data_dir/
            Training/
                bleached_coral/
                healthy_coral/
                not_coral/
            Validation/
                bleached_coral/
                healthy_coral/
                not_coral/
            Testing/
                bleached_coral/
                healthy_coral/
                not_coral/
    """
    data_dir = Path(data_dir)
    train_dir = data_dir / "Training"
    val_dir = data_dir / "Validation"
    test_dir = data_dir / "Testing"

    if not train_dir.exists():
        print(f"\nERROR: Training directory not found: {train_dir}")
        print(f"\nRun '--assemble' first to build the dataset:")
        print(f"  python train_v2_health_model.py --assemble")
        raise FileNotFoundError(f"Training directory not found: {train_dir}")

    # Report class counts per split
    for split_name, split_dir in [("Training", train_dir), ("Validation", val_dir), ("Testing", test_dir)]:
        print(f"\n  {split_name}:")
        for cls in CLASS_NAMES:
            cls_dir = split_dir / cls
            if cls_dir.exists():
                count = len(list(cls_dir.glob("*.jpg"))) + len(list(cls_dir.glob("*.png")))
                print(f"    {cls}: {count}")
            else:
                print(f"    {cls}: MISSING")

    # Load datasets from pre-split directories
    train_ds = keras.utils.image_dataset_from_directory(
        train_dir,
        labels='inferred',
        label_mode='categorical',
        class_names=CLASS_NAMES,
        color_mode='rgb',
        batch_size=batch_size,
        image_size=(IMG_SIZE, IMG_SIZE),
        shuffle=True,
        seed=42,
    )

    val_ds = keras.utils.image_dataset_from_directory(
        val_dir,
        labels='inferred',
        label_mode='categorical',
        class_names=CLASS_NAMES,
        color_mode='rgb',
        batch_size=batch_size,
        image_size=(IMG_SIZE, IMG_SIZE),
        shuffle=False,
        seed=42,
    )

    # Normalize pixel values to [0, 1] (matches V1 preprocessing)
    normalization = layers.Rescaling(1.0 / 255.0)

    # Data augmentation — matches V1 ImageDataGenerator settings:
    #   rotation_range=20, width_shift_range=0.2, height_shift_range=0.2,
    #   horizontal_flip=True, vertical_flip=True, zoom_range=0.2
    # Applied ONLY to training data (not validation/test)
    data_augmentation = keras.Sequential([
        layers.RandomRotation(20 / 360),           # 20 degrees, same as v1
        layers.RandomTranslation(0.2, 0.2),         # width/height shift 0.2
        layers.RandomFlip("horizontal_and_vertical"),# both flips, same as v1
        layers.RandomZoom(0.2),                      # zoom_range=0.2
    ], name="data_augmentation")

    print(f"\n  Data augmentation: ON (rotation, shifts, flips, zoom)")

    # Apply normalization + augmentation to training, normalization only to val
    train_ds = train_ds.map(
        lambda x, y: (data_augmentation(normalization(x), training=True), y),
        num_parallel_calls=tf.data.AUTOTUNE,
    )
    val_ds = val_ds.map(
        lambda x, y: (normalization(x), y),
        num_parallel_calls=tf.data.AUTOTUNE,
    )

    # Performance optimization
    train_ds = train_ds.prefetch(tf.data.AUTOTUNE)
    val_ds = val_ds.prefetch(tf.data.AUTOTUNE)

    return train_ds, val_ds


def compute_class_weights(data_dir):
    """
    Compute class weights to handle imbalanced datasets.
    Important since not_coral (~463) is much smaller than healthy/bleached (~4,500 each).
    Counts from Training split only (what the model actually trains on).
    """
    counts = {}
    train_dir = Path(data_dir) / "Training"
    for i, cls in enumerate(CLASS_NAMES):
        cls_dir = train_dir / cls
        if cls_dir.exists():
            count = len(list(cls_dir.glob("*.jpg"))) + len(list(cls_dir.glob("*.png")))
            counts[i] = count
        else:
            counts[i] = 0

    total = sum(counts.values())
    if total == 0:
        return None

    # Inverse frequency weighting, capped at MAX_WEIGHT to prevent
    # training instability from extreme imbalance (not_coral ~370 vs others ~3500+)
    MAX_WEIGHT = 3.0
    weights = {}
    for cls_idx, count in counts.items():
        if count > 0:
            raw_weight = total / (NUM_CLASSES * count)
            weights[cls_idx] = min(raw_weight, MAX_WEIGHT)
        else:
            weights[cls_idx] = 1.0

    print(f"\n  Class weights (to handle imbalance, capped at {MAX_WEIGHT}):")
    for idx, w in weights.items():
        raw = total / (NUM_CLASSES * counts[idx]) if counts[idx] > 0 else 0
        capped = " (capped)" if raw > MAX_WEIGHT else ""
        print(f"    {CLASS_NAMES[idx]}: {w:.3f} (n={counts[idx]}){capped}")

    return weights


def train(args):
    """Main training loop."""
    # Heavy imports — only loaded when actually training
    import numpy as np
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers, callbacks
    from sklearn.metrics import classification_report, confusion_matrix
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    # Make these available to helper functions via globals
    globals().update({
        'np': np, 'tf': tf, 'keras': keras, 'layers': layers,
        'callbacks': callbacks, 'classification_report': classification_report,
        'confusion_matrix': confusion_matrix, 'plt': plt,
    })

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("\n" + "=" * 60)
    print("Reef Monitor — V2 Three-Class Model Training")
    print("=" * 60)

    # Detect available devices (Apple Silicon GPU via tensorflow-metal)
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        print(f"\n  GPU DETECTED: {len(gpus)} device(s)")
        for gpu in gpus:
            print(f"    {gpu.name}")
        print(f"  Training will use GPU acceleration")
    else:
        print(f"\n  No GPU detected — training on CPU")
        print(f"  Tip: pip install tensorflow-metal --break-system-packages")

    print(f"\n  Classes: {CLASS_NAMES}")
    print(f"  Data dir: {args.data_dir}")
    print(f"  Output dir: {args.output_dir}")
    print(f"  Epochs: {args.epochs}")
    print(f"  Batch size: {args.batch_size}")
    print(f"  Learning rate: {args.lr}")
    if args.test:
        print(f"  MODE: TEST (quick run, 2 epochs)")

    # Create output directories
    output_dir = Path(args.output_dir)
    checkpoint_dir = output_dir / "checkpoints"
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir.mkdir(exist_ok=True)

    # Load data
    print(f"\nLoading datasets...")
    train_ds, val_ds = load_datasets(
        args.data_dir,
        batch_size=args.batch_size,
        test_mode=args.test
    )

    # Compute class weights for imbalanced data
    class_weights = compute_class_weights(args.data_dir)

    # Build model
    print(f"\nBuilding model...")
    if args.resume:
        print(f"  Resuming from: {args.resume}")
        model = keras.models.load_model(args.resume)
    else:
        model = build_model()

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=args.lr),
        loss='categorical_crossentropy',
        metrics=['accuracy'],
    )

    model.summary()

    # Callbacks
    cb = [
        callbacks.ModelCheckpoint(
            str(checkpoint_dir / "best_model.keras"),
            monitor='val_accuracy',
            save_best_only=True,
            verbose=1,
        ),
        callbacks.EarlyStopping(
            monitor='val_accuracy',
            patience=5,
            restore_best_weights=True,
            verbose=1,
        ),
        callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=3,
            min_lr=1e-6,
            verbose=1,
        ),
    ]

    # Train
    epochs = 2 if args.test else args.epochs
    print(f"\nTraining for {epochs} epochs...")

    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs,
        class_weight=class_weights,
        callbacks=cb,
    )

    # Save final model
    final_keras = output_dir / f"coral_health_v2_{timestamp}.keras"
    model.save(str(final_keras))
    print(f"\n  Keras model saved: {final_keras}")

    # Convert to ONNX
    print(f"\n  Converting to ONNX...")
    try:
        import tf2onnx
        onnx_path = output_dir / f"coral_health_v2_{timestamp}.onnx"
        # Save as SavedModel first, then convert (more reliable than from_keras
        # which has KeyError issues with newer TF/Keras versions)
        saved_model_dir = output_dir / "tmp_saved_model"
        model.export(str(saved_model_dir))
        import subprocess
        result = subprocess.run([
            "python3.12", "-m", "tf2onnx.convert",
            "--saved-model", str(saved_model_dir),
            "--output", str(onnx_path),
            "--opset", "13",
        ], capture_output=True, text=True)
        if result.returncode == 0 and onnx_path.exists():
            print(f"  ONNX model saved: {onnx_path}")
            print(f"  ONNX size: {onnx_path.stat().st_size / 1024 / 1024:.1f} MB")
        else:
            print(f"  ONNX conversion via SavedModel failed, trying from_keras fallback...")
            print(f"  stderr: {result.stderr[:500]}")
            # Fallback: try from_keras with explicit output names
            spec = (tf.TensorSpec((None, IMG_SIZE, IMG_SIZE, 3), tf.float32, name="input"),)
            model_proto, _ = tf2onnx.convert.from_keras(
                model, input_signature=spec, output_path=str(onnx_path),
                opset=13,
            )
            print(f"  ONNX model saved (fallback): {onnx_path}")
            print(f"  ONNX size: {onnx_path.stat().st_size / 1024 / 1024:.1f} MB")
        # Cleanup temp SavedModel
        import shutil
        if saved_model_dir.exists():
            shutil.rmtree(saved_model_dir)
    except (ImportError, Exception) as e:
        print(f"  WARNING: ONNX conversion failed: {e}")
        print(f"  The Keras model was saved successfully — convert manually later.")

    # Evaluate
    print(f"\nEvaluating on validation set...")
    evaluate_model(model, val_ds, output_dir, timestamp)

    # Save training history
    history_path = output_dir / f"training_history_{timestamp}.json"
    with open(history_path, 'w') as f:
        json.dump({k: [float(v) for v in vals] for k, vals in history.history.items()}, f, indent=2)
    print(f"  Training history saved: {history_path}")

    # Plot training curves
    plot_training_curves(history, output_dir, timestamp)

    print(f"\n{'=' * 60}")
    print(f"Training complete!")
    print(f"{'=' * 60}")
    print(f"\n  Best model: {checkpoint_dir / 'best_model.keras'}")
    print(f"  Output dir: {output_dir}")
    print(f"\n  Next steps:")
    print(f"  1. Review metrics and confusion matrix")
    print(f"  2. If accuracy >= 80%, test ONNX model in browser")
    print(f"  3. Copy ONNX to public/coral_model.onnx to deploy")
    print(f"  4. Update App.js CLASS_LABELS and prediction logic")


def evaluate_model(model, val_ds, output_dir, timestamp):
    """Generate classification report and confusion matrix."""
    # Collect all predictions and labels
    all_preds = []
    all_labels = []

    for images, labels in val_ds:
        preds = model.predict(images, verbose=0)
        all_preds.extend(np.argmax(preds, axis=1))
        all_labels.extend(np.argmax(labels.numpy(), axis=1))

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)

    # Classification report
    report = classification_report(
        all_labels, all_preds,
        target_names=CLASS_NAMES,
        digits=4,
    )
    print(f"\n{report}")

    # Save report
    report_path = output_dir / f"evaluation_report_{timestamp}.txt"
    with open(report_path, 'w') as f:
        f.write(f"V2 Three-Class Model Evaluation\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'=' * 60}\n\n")
        f.write(report)
        f.write(f"\nConfusion Matrix:\n")
        cm = confusion_matrix(all_labels, all_preds)
        f.write(f"{cm}\n")
        f.write(f"\nClass mapping: {dict(enumerate(CLASS_NAMES))}\n")

    print(f"  Evaluation report saved: {report_path}")

    # Confusion matrix
    cm = confusion_matrix(all_labels, all_preds)
    print(f"\n  Confusion Matrix:")
    print(f"  {'':20s} {'Pred Bleached':>15s} {'Pred Healthy':>15s} {'Pred Not Coral':>15s}")
    for i, cls in enumerate(CLASS_NAMES):
        row = ''.join(f"{cm[i][j]:>15d}" for j in range(NUM_CLASSES))
        print(f"  {cls:20s}{row}")


def plot_training_curves(history, output_dir, timestamp):
    """Save training accuracy and loss curves."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

    # Accuracy
    ax1.plot(history.history['accuracy'], label='Train')
    ax1.plot(history.history['val_accuracy'], label='Validation')
    ax1.set_title('Model Accuracy')
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Accuracy')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Loss
    ax2.plot(history.history['loss'], label='Train')
    ax2.plot(history.history['val_loss'], label='Validation')
    ax2.set_title('Model Loss')
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('Loss')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plot_path = output_dir / f"training_curves_{timestamp}.png"
    plt.savefig(str(plot_path), dpi=150)
    plt.close()
    print(f"  Training curves saved: {plot_path}")


def assemble_dataset():
    """
    Assemble v2 three-class dataset from existing sources.

    Copies/symlinks:
      - Kaggle bleached_corals → Training/bleached_coral, etc.
      - Kaggle healthy_corals → Training/healthy_coral, etc.
      - iNaturalist not_coral images → split 80/10/10 into Training/Validation/Testing

    Output structure:
      ~/Data/coral/processed/health_model_v2/
        Training/
          bleached_coral/
          healthy_coral/
          not_coral/
        Validation/
          bleached_coral/
          healthy_coral/
          not_coral/
        Testing/
          bleached_coral/
          healthy_coral/
          not_coral/
    """
    import shutil
    import random

    random.seed(42)

    print("\n" + "=" * 60)
    print("Assembling V2 Three-Class Dataset")
    print("=" * 60)

    # Verify sources exist
    if not KAGGLE_DIR.exists():
        print(f"\nERROR: Kaggle dataset not found: {KAGGLE_DIR}")
        return
    if not NOT_CORAL_DIR.exists():
        print(f"\nERROR: Not-coral images not found: {NOT_CORAL_DIR}")
        return

    # Class name mapping (Kaggle uses plural, we standardize to singular)
    KAGGLE_CLASS_MAP = {
        'bleached_corals': 'bleached_coral',
        'healthy_corals': 'healthy_coral',
    }
    SPLIT_MAP = {
        'Training': 'Training',
        'Validation': 'Validation',
        'Testing': 'Testing',
    }

    # Create output structure
    for split in SPLIT_MAP.values():
        for cls in CLASS_NAMES:
            out_dir = DATA_DIR / split / cls
            out_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Copy Kaggle healthy/bleached data (preserving original splits)
    print(f"\n  Copying Kaggle data from: {KAGGLE_DIR}")
    for kaggle_split, out_split in SPLIT_MAP.items():
        split_dir = KAGGLE_DIR / kaggle_split
        if not split_dir.exists():
            print(f"  WARNING: {split_dir} not found, skipping")
            continue

        for kaggle_cls, out_cls in KAGGLE_CLASS_MAP.items():
            src = split_dir / kaggle_cls
            dst = DATA_DIR / out_split / out_cls

            if not src.exists():
                print(f"  WARNING: {src} not found, skipping")
                continue

            images = list(src.glob("*.jpg")) + list(src.glob("*.jpeg")) + list(src.glob("*.png"))
            existing = len(list(dst.glob("*.*")))

            if existing >= len(images):
                print(f"  {out_split}/{out_cls}: {existing} already present, skipping")
                continue

            print(f"  Copying {len(images)} images → {out_split}/{out_cls}")
            for img in images:
                shutil.copy2(img, dst / img.name)

    # Step 2: Split not_coral images 80/10/10 into train/val/test
    print(f"\n  Splitting not-coral images from: {NOT_CORAL_DIR}")
    not_coral_images = list(NOT_CORAL_DIR.glob("*.jpg")) + list(NOT_CORAL_DIR.glob("*.png"))
    random.shuffle(not_coral_images)

    n = len(not_coral_images)
    n_train = int(n * 0.8)
    n_val = int(n * 0.1)
    # Rest goes to test

    splits = {
        'Training': not_coral_images[:n_train],
        'Validation': not_coral_images[n_train:n_train + n_val],
        'Testing': not_coral_images[n_train + n_val:],
    }

    for split_name, images in splits.items():
        dst = DATA_DIR / split_name / 'not_coral'
        existing = len(list(dst.glob("*.*")))
        if existing >= len(images):
            print(f"  {split_name}/not_coral: {existing} already present, skipping")
            continue
        print(f"  Copying {len(images)} images → {split_name}/not_coral")
        for img in images:
            shutil.copy2(img, dst / img.name)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"ASSEMBLY COMPLETE")
    print(f"{'=' * 60}")
    print(f"\n  Output: {DATA_DIR}\n")

    grand_total = 0
    for split in ['Training', 'Validation', 'Testing']:
        print(f"  {split}:")
        for cls in CLASS_NAMES:
            cls_dir = DATA_DIR / split / cls
            count = len(list(cls_dir.glob("*.*"))) if cls_dir.exists() else 0
            print(f"    {cls}: {count}")
            grand_total += count
    print(f"\n  Grand total: {grand_total} images")
    print(f"\n  Ready to train: python train_v2_health_model.py")


def main():
    parser = argparse.ArgumentParser(
        description="Train Reef Monitor V2 three-class health model")
    parser.add_argument("--data-dir", type=str, default=str(DATA_DIR),
                       help=f"Training data directory (default: {DATA_DIR})")
    parser.add_argument("--output-dir", type=str, default=str(OUTPUT_DIR),
                       help=f"Output directory for models (default: {OUTPUT_DIR})")
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS,
                       help=f"Training epochs (default: {DEFAULT_EPOCHS})")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                       help=f"Batch size (default: {DEFAULT_BATCH_SIZE})")
    parser.add_argument("--lr", type=float, default=DEFAULT_LEARNING_RATE,
                       help=f"Learning rate (default: {DEFAULT_LEARNING_RATE})")
    parser.add_argument("--resume", type=str, default=None,
                       help="Path to checkpoint to resume from")
    parser.add_argument("--test", action="store_true",
                       help="Quick test mode (2 epochs, small subset)")
    parser.add_argument("--assemble", action="store_true",
                       help="Assemble v2 dataset from Kaggle + iNaturalist sources (run before training)")
    args = parser.parse_args()

    if args.assemble:
        assemble_dataset()
    else:
        train(args)


if __name__ == "__main__":
    main()
