# 🪸 Reef Monitor - AI Coral Health Analysis

<div align="center">

![Reef Monitor](https://img.shields.io/badge/Status-Production%20Ready-success)
![React](https://img.shields.io/badge/React-18.x-blue)
![AI Powered](https://img.shields.io/badge/AI-ONNX%20Runtime-orange)
![License](https://img.shields.io/badge/License-Proprietary-red)

**AI-powered mobile app for real-time coral reef health monitoring**

[🌊 Try Live Demo](https://dbasick.github.io/reef-monitor-app/) | [📧 Contact Developer](mailto:DaBasick@yahoo.com)

</div>

---

## 📱 About

Reef Monitor brings professional-grade AI coral health analysis to your phone. Designed for marine biologists, dive operators, conservationists, and reef enthusiasts in the USVI and beyond. Take a photo, get instant analysis, and contribute to community reef health monitoring—all while working completely offline.

### ✨ Key Features

- 🤖 **AI-Powered Analysis** - Advanced machine learning identifies coral health status in seconds
- 📸 **Instant Assessment** - Point, shoot, analyze—get results before you surface
- 🌐 **Works Offline** - Full functionality without internet after initial setup
- 📊 **Community Database** - Your observations contribute to reef conservation efforts
- 🔒 **Privacy First** - Control what location data you share (GPS, dive sites, or general areas)
- 💾 **Track Your Dives** - Automatic history of all your observations
- 📱 **Install as App** - Add to your home screen for native app experience
- 🎯 **USVI Dive Sites** - Pre-loaded with local dive site locations

---

## 🎯 How It Works

<div align="center">

**📸 Take Photo → 🤖 AI Analysis → 📍 Add Location → ☁️ Save to Database**

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

## 🏗️ Technical Overview

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
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│       Cloud Database (Firebase)         │
│   Community Data + Personal History     │
└─────────────────────────────────────────┘
```

### Model Specifications

- **Input:** 224×224 RGB images, normalized
- **Architecture:** Convolutional Neural Network (CNN)
- **Accuracy:** ~80% on validation dataset
- **Inference:** ~1 second on mobile devices
- **Size:** 77MB (one-time download, cached locally)

### Technology Stack

- **Frontend:** React 18 with modern hooks
- **AI Runtime:** ONNX Runtime Web (browser-based inference)
- **Database:** Firebase (Firestore + Storage)
- **Hosting:** GitHub Pages / Netlify
- **Platform:** Cross-platform PWA (iOS, Android, Desktop)

---

## 📱 Getting Started

### Access the App

**🌐 Live App:**  
👉 [https://dbasick.github.io/reef-monitor-app/](https://dbasick.github.io/reef-monitor-app/)

**📲 Install on Your Phone:**
1. Visit the link above on your mobile browser
2. Wait for the AI model to download (~77MB, one-time only)
3. Tap your browser's "Add to Home Screen" option
4. Launch from your home screen like a native app

**✅ Requirements:**
- Modern mobile browser (Safari, Chrome, Edge)
- ~100MB free storage for app and model
- Internet connection for first-time setup only
- Camera access for photo capture

---

## 🌊 Field Usage Guide

### For Marine Researchers

**Best Practices:**
- Natural daylight provides best results
- Position 1-2 feet from coral subject
- Keep phone steady during capture
- Capture multiple angles for confidence
- Add detailed notes for research value

**Location Options:**
- **Exact GPS** - Precise coordinates (optional)
- **Dive Sites** - Pre-populated USVI locations
- **Custom Sites** - Save your own locations
- **General Area** - Broad region only
- **Mark as Sensitive** - Hide from public database

### For Dive Operators

Track coral health across your regular dive sites. Monitor changes over time. Contribute to local conservation efforts. Share findings with marine authorities.

### For Citizen Scientists

Every scan contributes to understanding USVI reef health. Your observations help researchers identify trends, track bleaching events, and prioritize conservation efforts.

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
- Image (for verification and research)

**What We DON'T Collect:**
- Personal identifying information
- User accounts or login data
- Device information
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
- Collect geo-tagged observations for scientific studies
- Monitor specific dive sites longitudinally

---

## 🗺️ Project Roadmap

### Current Version (1.0)
- ✅ Binary classification (Healthy vs Bleached)
- ✅ Offline AI inference
- ✅ Firebase cloud database
- ✅ Location privacy controls
- ✅ USVI dive site integration

### Planned Features
- 🔄 Multi-class coral health (Healthy, Bleached, Dead, Diseased)
- 🔄 Export scan history as CSV
- 🔄 Coral species identification
- 🔄 Batch scanning mode
- 🔄 Integration with reef monitoring databases
- 🔄 Multi-language support
- 🔄 Offline maps for dive sites

---

## 📞 Contact & Support

**Developer:** Daniel Basick  
**Email:** [DaBasick@yahoo.com](mailto:DaBasick@yahoo.com)  
**Project Repository:** Private (contact for inquiries)

### Questions?
- **Technical issues?** Email with screenshots and description

### Acknowledgments

Built for the USVI marine conservation community. Special thanks to local dive operators, marine biologists, and citizen scientists who inspired this project.

Powered by advanced AI technology to support ocean conservation efforts.

---

## 📝 License & Terms

**Copyright © 2024 Daniel Basick. All Rights Reserved.**

This software is proprietary. The application is provided for use by marine researchers, conservationists, and ocean enthusiasts. 

**Usage Terms:**
- ✅ Free for personal, educational, and research use
- ✅ Data contributed to community database helps conservation efforts
- ❌ Redistribution or modification of the application is prohibited
- ❌ Commercial use requires prior written permission

For licensing inquiries, contact: DaBasick@yahoo.com

---

## 📈 Project Status

**Version:** 1.0.0  
**Status:** 🟢 Production Ready  
**Last Updated:** December 2024  
**Maintained By:** Daniel Basick

**Platforms:**
- Web App (All Browsers)
- iOS (via PWA)
- Android (via PWA)
- Desktop (via PWA)

---

<div align="center">

**🪸 Built with 💙 for ocean conservation 🌊**

*Every scan contributes to protecting our coral reefs*

[⬆ Back to Top](#-reef-monitor---ai-coral-health-analysis)

</div>
