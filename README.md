# 🪸 Reef Monitor - AI Coral Health Analysis

<div align="center">

![Reef Monitor](https://img.shields.io/badge/Status-Production%20Ready-success)
![React](https://img.shields.io/badge/React-18.x-blue)
![AI Powered](https://img.shields.io/badge/AI-ONNX%20Runtime-orange)
![License](https://img.shields.io/badge/License-Proprietary-red)

**AI-powered mobile app for real-time coral reef health monitoring**

[🌊 Try Live Demo](https://reef-monitor.netlify.app) | [📧 Contact Developer](mailto:DaBasick@yahoo.com)

</div>

---

## 📱 About

Reef Monitor brings professional-grade AI coral health analysis to your phone. Designed for marine biologists, dive operators, conservationists, and reef enthusiasts in the USVI and beyond. Take a photo, get instant analysis, learn about Caribbean coral species, and contribute to community reef health monitoring—all while working completely offline.

### ✨ Key Features

- 🤖 **AI-Powered Health Analysis** - Advanced machine learning identifies coral health status in seconds
- 🪸 **Caribbean Coral Guide** - Interactive reference guide with 13 common USVI species
- 📸 **Instant Assessment** - Point, shoot, analyze—get results before you surface
- 🌐 **Offline Capable** - AI runs in your browser, no server needed after initial download
- ☁️ **Cloud Sync** - Observations automatically upload when online
- 📊 **Community Database** - Your observations contribute to reef conservation efforts
- 🗺️ **Interactive Map** - Visualize community observations across USVI dive sites
- 🔒 **Privacy First** - Control what location data you share
- 💾 **Track Your Dives** - Automatic history of all your observations
- 📱 **Install as App** - Add to home screen for native app experience

---

## 🎯 How It Works

<div align="center">

**📸 Take Photo → 🤖 AI Analysis → 📍 Add Location → ☁️ Sync to Cloud**

Simple, fast, and accurate coral health monitoring in the field.

</div>

### Analysis Results

The AI model classifies coral into two primary categories:
- 🪸 **Healthy Coral** - Vibrant, normal coloration and structure
- ⚠️ **Bleached Coral** - Stressed or damaged coral showing bleaching

Each result includes:
- Primary prediction with confidence score
- Detailed probability breakdown
- High-resolution image capture
- Optional location tagging
- Personal observation notes

---

## 🪸 Caribbean Coral Guide

**NEW FEATURE:** Learn to identify 13 common coral species found in USVI waters!

### Featured Species

**Critically Endangered (2)**
- Elkhorn Coral (*Acropora palmata*)
- Staghorn Coral (*Acropora cervicornis*)
- Pillar Coral (*Dendrogyra cylindrus*)

**Endangered (1)**
- Mountainous Star Coral (*Orbicella faveolata*)

**Vulnerable (2)**
- Smooth Flower Coral (*Eusmilia fastigiata*)
- Elliptical Star Coral (*Dichocoenia stokesii*)

**Common Species (8)**
- Brain Coral (Mussidae family - multiple species)
- Mustard Hill Coral (*Porites astreoides*) - Most abundant on USVI reefs
- Lettuce Coral (*Agaricia agaricites*)
- Massive Starlet Coral (*Siderastrea siderea*)
- Great Star Coral (*Montastraea cavernosa*)
- Finger Coral (*Porites porites*)
- Blushing Star Coral (*Stephanocoenia intersepta*)

### Guide Features

- **High-quality photos** from iNaturalist research observations
- **Detailed descriptions** for each of 13 species
- **Identification tips** to distinguish similar corals
- **USVI status notes** on local abundance and threats
- **Conservation status** (IUCN Red List)
- **Habitat information** and depth ranges
- **Search functionality** to quickly find species
- **Threat factors** affecting each species

All coral photos properly attributed to photographers with Creative Commons licensing.

---

## 🗺️ Technical Overview

### Architecture

```
┌─────────────────────────────────────────┐
│     Progressive Web App (PWA)           │
│   React Frontend + AI Model Runtime     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      AI Model (Browser-Based)           │
│    Binary Classification: 80%+ Accuracy │
│      ONNX Runtime - Offline Capable     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│   Anonymous Authentication (Firebase)   │
│      Auto sign-in for cloud uploads     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│       Cloud Database (Firebase)         │
│   Community Data + Personal History     │
└─────────────────────────────────────────┘
```

### Model Specifications

**Health Classification Model:**
- **Input:** 224×224 RGB images, normalized
- **Architecture:** Convolutional Neural Network (CNN)
- **Accuracy:** ~80% on validation dataset
- **Inference:** ~1 second on mobile devices
- **Size:** 77MB (one-time download, cached locally)

**Coming Soon:** Species identification model (in development)

### Technology Stack

- **Frontend:** React 18 with modern hooks
- **AI Runtime:** ONNX Runtime Web (browser-based inference)
- **Database:** Firebase (Firestore + Storage)
- **Authentication:** Firebase Anonymous Auth (automatic, no login required)
- **Mapping:** React Leaflet with OpenStreetMap satellite imagery
- **Educational Content:** 18-species coral reference guide
- **Hosting:** Netlify (production) / GitHub Pages (development)
- **Platform:** Cross-platform PWA (iOS, Android, Desktop)

---

## 📱 Getting Started

### Access the App

**🌐 Live Production App:**  
👉 [https://reef-monitor.netlify.app](https://reef-monitor.netlify.app)

**🔬 Development Version (Latest Features):**  
👉 [https://dbasick.github.io/reef-monitor-app/](https://dbasick.github.io/reef-monitor-app/)

**📲 Install on Your Phone:**
1. Visit the production link on your mobile browser
2. Wait for the AI model to download (~77MB, one-time only)
3. Tap your browser's "Add to Home Screen" option
4. Launch from your home screen like a native app

**✅ Requirements:**
- Modern mobile browser (Safari, Chrome, Edge)
- ~100MB free storage for app and model
- Internet connection for initial setup and cloud sync
- Camera access for photo capture (mobile devices)
- GPS access for location tagging (optional)

---

## 🌊 Field Usage Guide

### For Marine Researchers

**Best Practices:**
- Natural daylight provides best results
- Position 1-2 feet from coral subject
- Keep phone steady during capture
- Capture multiple angles for confidence
- Add detailed notes for research value
- Use coral guide to confirm species in the field

**Location Options:**
- **Exact GPS** - Precise coordinates (optional)
- **Dive Sites** - Pre-populated USVI locations
- **Custom Sites** - Save your own locations
- **General Area** - Broad region only
- **Mark as Sensitive** - Hide from public database

### For Dive Operators

Track coral health across your regular dive sites. Monitor changes over time. Use the coral guide to educate clients. Contribute to local conservation efforts. Share findings with marine authorities.

### For Citizen Scientists

Every scan contributes to understanding USVI reef health. Your observations help researchers identify trends, track bleaching events, and prioritize conservation efforts. Learn to identify coral species with the built-in guide.

### For Educators

Use the coral guide as a teaching tool. Show students how to identify common USVI species. Track coral health over field trips. Contribute student observations to the community database.

---

## 📊 Data & Privacy

### What Gets Saved

**Locally on Your Device:**
- All your scan history (up to 50 scans)
- Analysis results and images
- Personal notes and observations

**In the Community Database (Optional):**
- Coral health classification
- Location information (at your chosen privacy level)
- Timestamp of observation
- Image (compressed, for verification)
- Anonymous user ID (auto-generated, not linked to you)

**What We DON'T Collect:**
- Personal identifying information
- User accounts or passwords
- Device tracking or analytics
- Browsing history

### Privacy Controls

You choose what to share:
- Share exact GPS coordinates
- Share only dive site name
- Share general area only
- Mark observations as "sensitive" (private)

All observations are anonymous by default.

---

## 🎯 Use Cases

### Marine Research
- Document bleaching events in real-time
- Track coral health over multiple dive seasons
- Collect geo-tagged observations for studies
- Monitor specific dive sites longitudinally
- Use coral guide for species confirmation

### Conservation Monitoring
- Identify areas of concern
- Track restoration project success
- Document coral recovery or decline
- Support conservation priority decisions

### Education & Outreach
- Teach coral identification to students
- Engage public in citizen science
- Demonstrate reef health trends
- Build awareness of conservation needs

---

## 🗺️ Project Roadmap

### Current Version (v1.1 - January 2026)
- ✅ Binary classification (Healthy vs Bleached)
- ✅ **Caribbean Coral Guide (13 USVI species)**
- ✅ Offline AI inference (browser-based)
- ✅ Firebase cloud database with automatic sync
- ✅ Anonymous authentication
- ✅ Interactive community observation map
- ✅ Mobile camera integration
- ✅ Location privacy controls
- ✅ USVI dive site database

### In Development
- 🔄 Coral species identification AI (multi-class model)
- 🔄 Expanded coral guide (additional species)

### Planned Features
- 📋 Multi-class coral health (Healthy, Bleached, Dead, Diseased)
- 📋 Export scan history as CSV
- 📋 Batch scanning mode
- 📋 Integration with reef monitoring databases
- 📋 Multi-language support
- 📋 Offline maps for dive sites

---

## 📞 Contact & Support

**Developer:** Daniel Basick  
**Email:** [DaBasick@yahoo.com](mailto:DaBasick@yahoo.com)  
**Production Site:** [reef-monitor.netlify.app](https://reef-monitor.netlify.app)  
**Development Site:** [dbasick.github.io/reef-monitor-app](https://dbasick.github.io/reef-monitor-app/)

### Questions?
- **Technical issues?** Email with screenshots and description
- **Research collaboration?** Contact for data sharing opportunities
- **Feature requests?** We'd love to hear your ideas

### Acknowledgments

Built for the USVI marine conservation community. Special thanks to:
- Local dive operators and marine biologists who inspired this project
- iNaturalist community for coral identification photos
- Citizen scientists contributing observations

**Photo Credits:** Coral guide photos from [iNaturalist Caribbean Coral Guide](https://www.inaturalist.org/guides/19437) by various photographers. Individual attributions displayed in app.

---

## 📜 License & Terms

**Copyright © 2025 Daniel Basick. All Rights Reserved.**

This software is proprietary. The application is provided for use by marine researchers, conservationists, and ocean enthusiasts.

**Usage Terms:**
- ✅ Free for personal, educational, and research use
- ✅ Data contributed to community database helps conservation efforts
- ✅ Coral guide photos used under Creative Commons licenses
- ❌ Redistribution or modification of the application is prohibited
- ❌ Commercial use requires prior written permission

For licensing inquiries, contact: DaBasick@yahoo.com

---

## 📈 Project Status

**Version:** 1.1.0  
**Status:** 🟢 Production Ready  
**Last Updated:** January 7, 2026  
**Maintained By:** Daniel Basick

**Platforms:**
- Web App (All Browsers)
- iOS (via PWA)
- Android (via PWA)
- Desktop (via PWA)

**Recent Updates:**
- Fixed brain coral photo attribution (replaced incorrect image)
- Added 13-species Caribbean coral identification guide
- Proper photo attribution for all coral species with CC licensing
- USVI-specific status notes for each species
- Enhanced search and filter functionality
- Improved mobile responsiveness

---

<div align="center">

**🪸 Built with 💙 for ocean conservation 🌊**

*Every scan contributes to protecting our coral reefs*

[⬆ Back to Top](#-reef-monitor---ai-coral-health-analysis)

</div>
