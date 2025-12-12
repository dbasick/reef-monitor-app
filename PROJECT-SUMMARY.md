# Reef Health Monitor - Complete Project Summary
**Last Updated:** December 11, 2025
**Developer:** Daniel Basick (DaBasick@yahoo.com)

---

## Project Overview

AI-powered mobile web application for monitoring coral health in the US Virgin Islands. Uses a trained CNN model to classify coral as Healthy or Bleached, with cloud database integration for community science data collection.

---

## Current Tech Stack

**Frontend:**
- React 18
- Progressive Web App (PWA)
- Capacitor for mobile features
- ONNX Runtime Web for client-side AI inference
- Lucide React for icons

**Backend/Database:**
- Firebase Firestore (NoSQL database)
- Firebase Storage (image hosting)
- Firebase Authentication (anonymous)

**AI Model:**
- Binary classification (Healthy vs Bleached)
- ONNX format (converted from Keras)
- Input: 224x224x3 RGB images
- Runs entirely in browser (offline-capable)

**Deployment:**
- Hosted on Netlify
- Continuous deployment from build folder

---

## Key Features Implemented

### 1. AI-Powered Coral Analysis
- Binary classification: Healthy vs Bleached Coral
- ~80% accuracy from trained model
- Client-side inference (works offline)
- Confidence scores with detailed breakdown
- ~1 second inference time on mobile

### 2. Mobile-First Camera Integration
- Native camera access via file input with capture attribute
- Rear-facing camera default
- Works on iOS and Android
- Image preprocessing (resize to 224x224, normalize)

### 3. Cloud Database Integration (Firebase)
- **Location Options:**
  - GPS coordinates (exact location with user permission)
  - Dive Site selection (pre-populated USVI sites)
  - Custom Site creation (user-named locations)
  - General Area (privacy-focused regions)

- **Data Stored:**
  - Compressed images (~1MB max)
  - Prediction results + confidence
  - Location data (based on user selection)
  - Timestamp
  - User notes
  - Sensitive location flag
  - Device info

### 4. Local Storage + Cloud Sync
- Maintains 50 most recent scans locally
- Cloud sync with visual indicator (☁️ badge)
- Graceful fallback if cloud fails
- Offline queue capability

### 5. Privacy Controls
- 4 location granularity options
- Sensitive location flag for rare species areas
- Optional GPS sharing
- Anonymous authentication

### 6. User Interface
- Ocean-themed gradient design
- Loading animations
- First-time welcome screen (shows once)
- Scan history view
- Developer attribution footer
- Professional, clean mobile UI

---

## File Structure

```
C:\reef-monitor\
├── public\
│   ├── coral_model.onnx          # AI model
│   ├── index.html
│   └── manifest.json              # PWA config
├── src\
│   ├── App.js                     # Main application
│   ├── App.css                    # All styles
│   ├── firebase\
│   │   ├── config.js              # Firebase credentials
│   │   └── database.js            # Database operations
│   └── components\
│       └── LocationPicker.js      # Location selection modal
├── package.json
└── build\                         # Production build (deploy this)
```

---

## Firebase Configuration

**Project:** reef-health-monitor-c7263

**Services Enabled:**
- Firestore Database (us-east1)
- Storage (coral-images bucket)
- Authentication (anonymous)

**Collections:**
- `observations` - All coral scan data

**Security Rules:**
- Read: Public
- Create: Anyone (anonymous auth)
- Update/Delete: Authenticated users only

---

## Key Code Components

### Location Types
```javascript
LOCATION_TYPES = {
  GPS: 'gps',
  DIVE_SITE: 'dive_site',
  CUSTOM_SITE: 'custom_site',
  GENERAL: 'general'
}
```

### Pre-populated Dive Sites (USVI)
- Coki Beach (St. Thomas)
- Cow and Calf Rocks (St. Thomas)
- Wreck Alley (St. Thomas)
- French Cap (St. Thomas)
- Hull Bay (St. Thomas)
- Frederiksted Pier (St. Croix)
- Salt River Canyon (St. Croix)
- Cane Bay Wall (St. Croix)
- Trunk Bay (St. John)
- Haulover Bay (St. John)

### Model Output Interpretation
```javascript
// Binary model outputs single probability for "Healthy"
const healthyProb = output.data[0];
const bleachedProb = 1 - healthyProb;
const prediction = healthyProb > 0.5 ? "Healthy Coral" : "Bleached Coral";
```

---

## Recent Changes & Fixes

### Session 1: Initial Mobile Deployment
- Converted Keras model to ONNX
- Built React PWA with camera integration
- Deployed to Netlify
- Fixed binary classification interpretation

### Session 2: Firebase Integration
- Added cloud database
- Created 4-option location picker
- Implemented image compression
- Added custom dive site feature
- Built community database structure

### Session 3: Developer Attribution
- Added first-time welcome screen
- Updated footer with developer credit
- Made email link readable (white text)
- Fixed loading screen text spacing

---

## Development Commands

```bash
# Install dependencies
npm install

# Run development server
npm start

# Build for production
npm run build

# Deploy
# Drag build/ folder to netlify.com
```

---

## Environment Variables / Secrets

**Firebase Config (in src/firebase/config.js):**
```javascript
apiKey: "AIzaSyD0JXHO4DzfHocbMb7DzxFkMnllIEjt2n0"
authDomain: "reef-health-monitor-c7263.firebaseapp.com"
projectId: "reef-health-monitor-c7263"
storageBucket: "reef-health-monitor-c7263.firebasestorage.app"
messagingSenderId: "930786260606"
appId: "1:930786260606:web:e0f0a3323cb8d2bd724a2f"
```

---

## Known Behaviors

1. **First Load:** Downloads ~77MB ONNX model (one-time)
2. **Welcome Screen:** Shows only on first use (localStorage flag)
3. **Location Modal:** Appears after every successful scan
4. **Offline Mode:** Works after first load, queues uploads
5. **History:** Stores 50 most recent scans locally

---

## Future Enhancement Ideas

- Real-time bleaching alerts
- Interactive map view
- Species identification (multi-class)
- Water quality data integration
- Research team collaboration features
- Dashboard with statistics
- CSV export
- Mobile app store deployment (via Capacitor)

---

## Important Notes

- Model is BINARY classification (Healthy vs Bleached only)
- All inference happens client-side (privacy + offline)
- Firebase on Blaze plan (pay-as-you-go, but usage is well within free tier)
- Custom dive sites are shared community-wide
- GPS coordinates require user permission
- Images compressed to ~1MB before upload

---

## Testing Checklist

- [x] Camera access on iOS
- [x] Photo upload from gallery
- [x] AI inference accuracy
- [x] Location modal appears
- [x] Firebase upload success
- [x] Local storage backup
- [x] History view
- [x] Welcome screen (first time)
- [x] Footer attribution
- [x] Offline functionality
- [x] PWA installability

---

## Contact

**Developer:** Daniel Basick  
**Email:** DaBasick@yahoo.com  
**Purpose:** Marine conservation technology for USVI reef monitoring

---

*This app represents a complete AI-powered mobile solution for community-driven coral health monitoring, balancing scientific data collection needs with user privacy and accessibility.*
