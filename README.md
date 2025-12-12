# 🪸 Reef Monitor - AI Coral Health Mobile App

<div align="center">

![Reef Monitor](https://img.shields.io/badge/Status-Production%20Ready-success)
![React](https://img.shields.io/badge/React-18.x-blue)
![ONNX](https://img.shields.io/badge/ONNX-Runtime-orange)
![License](https://img.shields.io/badge/License-MIT-green)

**AI-powered mobile app for analyzing coral reef health in the field**

[Live Demo](#) | [Documentation](./MOBILE_APP_SETUP.md) | [Report Bug](#)

</div>

---

## 📱 About

Reef Monitor is a progressive web app (PWA) that brings AI-powered coral health analysis to marine biologists, conservationists, and reef enthusiasts in the field. Built with React and ONNX Runtime, it runs entirely offline after the initial load, making it perfect for remote reef locations.

### ✨ Key Features

- 📸 **Native Camera Integration** - Capture coral images directly from your phone
- 🤖 **Offline AI Analysis** - Model runs in browser, no internet required after first load
- 📊 **Instant Results** - Get health predictions with confidence scores in seconds
- 💾 **History Tracking** - Save and review up to 50 previous scans
- 🎨 **Beautiful UI** - Ocean-themed design optimized for mobile
- 🌍 **Cross-Platform** - Works on iOS, Android, and desktop browsers
- 📲 **Installable PWA** - Add to home screen for app-like experience

---

## 🎯 Quick Start

### Prerequisites

- Node.js 14+ and npm
- Python 3.8+ (for model conversion)
- Your trained Keras model (`best_coral_model.keras`)

### Installation

```bash
# 1. Install dependencies
cd reef-monitor
npm install

# 2. Convert your model to ONNX
cd ..
pip install tensorflow tf2onnx onnx
python convert_to_onnx.py

# 3. Copy model to app
cp coral_model.onnx reef-monitor/public/

# 4. Start development server
cd reef-monitor
npm start
```

Visit `http://localhost:3000` to see the app!

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│          React Frontend                 │
│  (Camera, UI, Image Processing)         │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│       ONNX Runtime Web                  │
│  (AI Model Inference in Browser)        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      Trained CNN Model (.onnx)          │
│   (Coral Health Classification)         │
└─────────────────────────────────────────┘
```

**Tech Stack:**
- **Frontend:** React 18, Lucide Icons
- **AI Runtime:** ONNX Runtime Web
- **Model Format:** ONNX (converted from Keras)
- **Storage:** Browser LocalStorage
- **Styling:** Custom CSS with CSS Variables

---

## 🎨 Screenshots

<div align="center">

| Home Screen | Camera View | Results |
|-------------|-------------|---------|
| ![Home](./docs/home.png) | ![Camera](./docs/camera.png) | ![Results](./docs/results.png) |

| History | Analysis | Loading |
|---------|----------|---------|
| ![History](./docs/history.png) | ![Analysis](./docs/analysis.png) | ![Loading](./docs/loading.png) |

</div>

---

## 🚀 Deployment

### Option 1: GitHub Pages (Free)

```bash
# Add to package.json
"homepage": "https://yourusername.github.io/reef-monitor"

# Deploy
npm run build
npm run deploy
```

### Option 2: Netlify (Free)

1. Drag `build/` folder to [netlify.com](https://netlify.com)
2. Or connect GitHub repo for auto-deployment

### Option 3: Vercel (Free)

```bash
npm install -g vercel
vercel
```

### Option 4: Native App Stores

Use Capacitor to package as native iOS/Android app:

```bash
npm install @capacitor/cli @capacitor/core
npx cap init
npx cap add ios
npx cap add android
npm run build
npx cap sync
npx cap open ios  # or android
```

---

## 📖 How It Works

### 1. Model Conversion

```python
# Keras → ONNX conversion
model = tf.keras.models.load_model('best_coral_model.keras')
spec = (tf.TensorSpec((None, 224, 224, 3), tf.float32, name="input"),)
model_proto, _ = tf2onnx.convert.from_keras(model, input_signature=spec)
onnx.save(model_proto, 'coral_model.onnx')
```

### 2. Image Preprocessing

```javascript
// Resize to 224x224 and normalize to [0, 1]
const canvas = document.createElement('canvas');
canvas.width = 224;
canvas.height = 224;
ctx.drawImage(imageElement, 0, 0, 224, 224);
const pixels = ctx.getImageData(0, 0, 224, 224).data;
const tensorData = new Float32Array(1 * 224 * 224 * 3);
for (let i = 0; i < pixels.length; i += 4) {
  tensorData[idx * 3] = pixels[i] / 255.0;     // R
  tensorData[idx * 3 + 1] = pixels[i + 1] / 255.0; // G
  tensorData[idx * 3 + 2] = pixels[i + 2] / 255.0; // B
}
```

### 3. AI Inference

```javascript
// Run model inference
const tensor = new ort.Tensor('float32', tensorData, [1, 224, 224, 3]);
const results = await model.run({ input: tensor });
const predictions = Array.from(results[Object.keys(results)[0]].data);
```

### 4. Results Display

```javascript
// Get top prediction
const maxIndex = predictions.indexOf(Math.max(...predictions));
const confidence = predictions[maxIndex] * 100;
const prediction = CLASS_LABELS[maxIndex];
```

---

## 🧪 Model Details

**Input:**
- Format: RGB image
- Size: 224 × 224 × 3
- Range: [0, 1] (normalized)

**Output:**
- Classes: 4 (Healthy, Bleached, Dead, Diseased)
- Format: Softmax probabilities
- Range: [0, 1]

**Performance:**
- Accuracy: ~80% (on test set)
- Inference Time: ~500ms (on mobile)
- Model Size: ~70MB (ONNX format)

---

## 📱 Usage

### For Field Work

1. **First Time Setup:**
   - Visit the app URL on your phone
   - Wait for model to download (~70MB, one-time)
   - Tap "Add to Home Screen"

2. **Taking Scans:**
   - Open app (works offline after first load)
   - Tap "Take Photo" to use camera
   - Or "Upload Image" to select from gallery
   - Wait ~1 second for AI analysis

3. **Reviewing Results:**
   - See primary prediction with confidence
   - View detailed breakdown of all 4 classes
   - Tap "History" to review past scans
   - Results saved automatically

### Best Practices

- **Lighting:** Natural daylight works best
- **Distance:** 1-2 feet from coral
- **Angle:** Perpendicular to coral surface
- **Stability:** Keep phone steady during capture
- **Coverage:** Multiple angles increase confidence

---

## 🔧 Configuration

### Update Class Labels

Edit `src/App.js`:

```javascript
const CLASS_LABELS = [
  'Healthy Coral',
  'Bleached Coral',
  'Dead Coral',
  'Diseased Coral'
];
```

### Customize Colors

Edit `src/App.css`:

```css
:root {
  --ocean-deep: #0a1929;
  --ocean-mid: #1e3a5f;
  --ocean-light: #2d5a8a;
  --coral-healthy: #00d4aa;
  --coral-warn: #ffa726;
  --coral-danger: #ef5350;
  --coral-disease: #ab47bc;
}
```

### Adjust Preprocessing

If your model expects different normalization:

```javascript
// For [-1, 1] range instead of [0, 1]:
tensorData[idx * 3] = (pixels[i] / 127.5) - 1.0;
```

---

## 🐛 Troubleshooting

### Model Won't Load
- Verify `coral_model.onnx` is in `/public/` folder
- Check file isn't corrupted (~70MB expected)
- Check browser console for specific errors

### Camera Not Working
- Camera requires HTTPS or localhost
- Check browser permissions
- Try Safari on iOS (Chrome doesn't support camera on iOS)

### Slow Performance
- First load downloads 70MB model (cached after)
- Consider model quantization to reduce size
- Use WiFi for initial download

See [MOBILE_APP_SETUP.md](./MOBILE_APP_SETUP.md) for detailed troubleshooting.

---

## 📊 Performance Optimization

### Model Quantization

Reduce model size by ~75%:

```python
import onnxruntime as ort
from onnxruntime.quantization import quantize_dynamic

quantize_dynamic(
    'coral_model.onnx',
    'coral_model_quantized.onnx',
    weight_type=ort.QuantType.QUInt8
)
```

### Code Splitting

Already enabled by Create React App. Model loads separately.

### Caching Strategy

- Model: Browser cache (automatic after first load)
- History: LocalStorage (persists offline)
- Images: Base64 in LocalStorage

---

## 🤝 Contributing

We welcome contributions! Here's how:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

### Development Setup

```bash
git clone https://github.com/yourusername/reef-monitor.git
cd reef-monitor
npm install
npm start
```

---

## 📝 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.

**Dependencies:**
- React: MIT License
- ONNX Runtime Web: MIT License
- Lucide React: ISC License

---

## 🙏 Acknowledgments

- Coral health dataset from [Kaggle](https://www.kaggle.com/)
- ONNX Runtime team for browser AI capabilities
- React team for the framework
- Marine conservation community for inspiration

---

## 📞 Contact

**Project Maintainer:** Daniel Basick
- Email: DaBasick@yahoo.com
- GitHub: [@dbasick](https://github.com/dbasick)
- Project: [https://github.com/dbasick/reef-monitor-app](https://github.com/dbasick/reef-monitor-app)

---

## 🗺️ Roadmap

- [ ] GPS location tagging
- [ ] Export scan history as CSV
- [ ] Social sharing functionality
- [ ] Multi-language support
- [ ] Offline map integration
- [ ] Confidence threshold alerts
- [ ] Batch scanning mode
- [ ] Cloud backup option
- [ ] Educational coral guide
- [ ] Integration with reef databases

---

## 📈 Project Status

**Current Version:** 1.0.0  
**Status:** Production Ready  
**Last Updated:** December 2024

---

<div align="center">

**Built with 💙 for ocean conservation**

[⬆ Back to Top](#-reef-monitor---ai-coral-health-mobile-app)

</div>
