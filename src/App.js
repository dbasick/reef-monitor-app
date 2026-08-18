import React, { useState, useRef, useEffect } from 'react';
import { Camera, Upload, History, Info, ChevronRight, Loader, Trash2, Map } from 'lucide-react';
import * as ort from 'onnxruntime-web';
import './App.css';
import LocationPicker from './components/LocationPicker';
import MapView from './components/MapView';
import CoralGuide from './components/CoralGuide';
import BatchScanner from './BatchScanner';
import { 
  saveObservation,
  saveBatchObservations,
  LOCATION_TYPES, 
  USVI_DIVE_SITES, 
  GENERAL_AREAS 
} from './firebase/database';
import { auth, db } from './firebase/config';
import { collection, query, where, orderBy, getDocs } from 'firebase/firestore';

// Class labels for coral health - 3-CLASS MODEL (v3c)
const CLASS_LABELS = ['Bleached Coral', 'Healthy Coral', 'Not Coral'];

function App() {
  const [model, setModel] = useState(null);          // v2 binary health classifier (healthy/bleached)
  const [gateModel, setGateModel] = useState(null);  // coral / not_coral gate
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [expandedBatch, setExpandedBatch] = useState(null);
  const [showMap, setShowMap] = useState(false);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);
  const videoRef = useRef(null);
  const [isCameraActive, setIsCameraActive] = useState(false);
  
  // Firebase/Location states
  const [showLocationModal, setShowLocationModal] = useState(false);
  const [locationType, setLocationType] = useState(LOCATION_TYPES.DIVE_SITE);
  const [selectedSite, setSelectedSite] = useState(null);
  const [selectedArea, setSelectedArea] = useState(null);
  const [customSiteName, setCustomSiteName] = useState('');
  const [customSiteIsland, setCustomSiteIsland] = useState('St. Thomas');
  const [customSiteDescription, setCustomSiteDescription] = useState('');
  const [useGPS, setUseGPS] = useState(true);
  const [isSensitive, setIsSensitive] = useState(false);
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [currentImageFile, setCurrentImageFile] = useState(null);
  const [showWelcome, setShowWelcome] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // View mode state - single or batch
  const [viewMode, setViewMode] = useState('single'); // 'single' or 'batch'

  // Load model on component mount
  useEffect(() => {
    loadModel();
    loadHistory();
    checkFirstTime();
    checkIfMobile();
  }, []);

  const checkFirstTime = () => {
    const hasSeenWelcome = localStorage.getItem('reefMonitorWelcomeSeen');
    if (!hasSeenWelcome) {
      setShowWelcome(true);
    }
  };

  const checkIfMobile = () => {
    const mobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    setIsMobile(mobile);
  };

  const dismissWelcome = () => {
    localStorage.setItem('reefMonitorWelcomeSeen', 'true');
    setShowWelcome(false);
  };

  const loadModel = async () => {
    try {
      setLoading(true);
      setError(null);
      // Load gate (coral/not_coral) and v2 health (binary bleached/healthy) in parallel
      const [gateSession, healthSession] = await Promise.all([
        ort.InferenceSession.create(process.env.PUBLIC_URL + '/coral_gate.onnx',  { executionProviders: ['wasm'] }),
        ort.InferenceSession.create(process.env.PUBLIC_URL + '/coral_model.onnx', { executionProviders: ['wasm'] }),
      ]);
      setGateModel(gateSession);
      setModel(healthSession);
      setLoading(false);
    } catch (err) {
      console.error('Error loading models:', err);
      setError('Failed to load AI models. Please refresh the page.');
      setLoading(false);
    }
  };

  const loadHistory = async () => {
    console.log('🔍 loadHistory called');
    try {
      // Check if user is authenticated
      if (!auth.currentUser) {
        console.log('❌ No user logged in, skipping history load');
        return;
      }

      const userId = auth.currentUser.uid;
      console.log('✅ User authenticated:', userId);
      
      // Query observations for current user
      const observationsRef = collection(db, 'observations');
      const q = query(
        observationsRef,
        where('userId', '==', userId),
        orderBy('timestamp', 'desc')
      );
      
      console.log('📡 Querying Firebase...');
      const querySnapshot = await getDocs(q);
      console.log(`📦 Got ${querySnapshot.size} documents from Firebase`);
      
      // Group by batchId for batch scans
      const batches = {};
      const singles = [];
      
      querySnapshot.forEach((doc) => {
        const data = doc.data();
        console.log('📄 Document:', doc.id, data);
        const historyItem = {
          id: doc.id,
          prediction: data.prediction,
          confidence: data.confidence,
          imageUrl: data.imageUrl,
          timestamp: data.timestamp?.toDate?.() || new Date(data.timestamp),
          location: data.location,
          source: data.source || 'single',
          batchId: data.batchId,
          batchIndex: data.batchIndex,
          synced: true
        };
        
        if (data.batchId) {
          // Batch scan - group by batchId
          if (!batches[data.batchId]) {
            batches[data.batchId] = [];
          }
          batches[data.batchId].push(historyItem);
        } else {
          // Single scan
          singles.push(historyItem);
        }
      });
      
      // Convert batches object to array and combine with singles
      const batchArray = Object.entries(batches).map(([batchId, items]) => ({
        id: batchId,
        type: 'batch',
        batchId: batchId,
        items: items.sort((a, b) => a.batchIndex - b.batchIndex),
        timestamp: items[0].timestamp,
        location: items[0].location,
        synced: true
      }));
      
      // Combine and sort by timestamp
      const allHistory = [...singles, ...batchArray].sort((a, b) => 
        new Date(b.timestamp) - new Date(a.timestamp)
      );
      
      console.log(`✅ Loaded ${allHistory.length} history items (${singles.length} singles, ${batchArray.length} batches)`);
      setHistory(allHistory.slice(0, 50)); // Keep only 50 most recent
      
    } catch (error) {
      console.error('❌ Error loading history from Firebase:', error);
      // Fallback to localStorage if Firebase fails
      const saved = localStorage.getItem('reefMonitorHistory');
      if (saved) {
        setHistory(JSON.parse(saved));
      }
    }
  };

  const saveToHistory = (result, cloudId = null) => {
    const newEntry = {
      ...result,
      timestamp: new Date().toISOString(),
      id: Date.now(),
      cloudId: cloudId,
      synced: cloudId ? true : false
    };
    const newHistory = [newEntry, ...history].slice(0, 50);
    setHistory(newHistory);
    localStorage.setItem('reefMonitorHistory', JSON.stringify(newHistory));
  };

  const deleteFromHistory = (id) => {
    const newHistory = history.filter(item => item.id !== id);
    setHistory(newHistory);
    localStorage.setItem('reefMonitorHistory', JSON.stringify(newHistory));
  };

  const preprocessImage = (imageElement) => {
    return new Promise((resolve) => {
      const canvas = document.createElement('canvas');
      canvas.width = 224;
      canvas.height = 224;
      const ctx = canvas.getContext('2d');
      
      ctx.drawImage(imageElement, 0, 0, 224, 224);
      const imageData = ctx.getImageData(0, 0, 224, 224);
      const pixels = imageData.data;
      
      const tensorData = new Float32Array(1 * 224 * 224 * 3);
      for (let i = 0; i < pixels.length; i += 4) {
        const idx = i / 4;
        tensorData[idx * 3] = pixels[i] / 255.0;
        tensorData[idx * 3 + 1] = pixels[i + 1] / 255.0;
        tensorData[idx * 3 + 2] = pixels[i + 2] / 255.0;
      }
      
      resolve(tensorData);
    });
  };

  const analyzeImage = async (imageUrl, imageFile) => {
    // FIX #1: Check if both models are loaded but don't show error yet - just wait
    if (!model || !gateModel) {
      if (loading) {
        // Model is still loading, wait a bit and retry
        setTimeout(() => analyzeImage(imageUrl, imageFile), 500);
        return;
      } else {
        // Model failed to load
        setError('Model failed to load. Please refresh the page.');
        return;
      }
    }

    setAnalyzing(true);
    setError(null); // Clear any previous errors
    setCurrentImageFile(imageFile); // Store for later upload

    try {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      
      await new Promise((resolve, reject) => {
        img.onload = resolve;
        img.onerror = reject;
        img.src = imageUrl;
      });

      const tensorData = await preprocessImage(img);
      const tensor = new ort.Tensor('float32', tensorData, [1, 224, 224, 3]);

      // Step 1: gate decides "is this a coral image at all?"
      const gateOut = (await gateModel.run({ [gateModel.inputNames[0]]: tensor }))[gateModel.outputNames[0]];
      // gate softmax: [coral_prob, not_coral_prob]
      const notCoralProb = gateOut.data[1];

      let resultData;
      if (notCoralProb > 0.5) {
        // Gate rejected — skip the health classifier entirely
        resultData = {
          prediction: 'Not Coral',
          confidence: (notCoralProb * 100).toFixed(1),
          allPredictions: [
            { label: 'Bleached Coral', confidence: '0.0' },
            { label: 'Healthy Coral',  confidence: '0.0' },
            { label: 'Not Coral',      confidence: (notCoralProb * 100).toFixed(1) },
          ],
          imageUrl
        };
      } else {
        // Step 2: gate passed — run v2 binary for healthy/bleached
        const healthOut = (await model.run({ [model.inputNames[0]]: tensor }))[model.outputNames[0]];
        // v2 outputs single sigmoid: data[0] = healthy probability
        const healthyProb  = healthOut.data[0];
        const bleachedProb = 1 - healthyProb;
        const isHealthy = healthyProb > 0.5;
        const prediction = isHealthy ? 'Healthy Coral' : 'Bleached Coral';
        const confidence = (isHealthy ? healthyProb : bleachedProb) * 100;

        resultData = {
          prediction: prediction,
          confidence: confidence.toFixed(1),
          allPredictions: [
            { label: 'Bleached Coral', confidence: (bleachedProb * 100).toFixed(1) },
            { label: 'Healthy Coral',  confidence: (healthyProb  * 100).toFixed(1) },
            { label: 'Not Coral',      confidence: (notCoralProb * 100).toFixed(1) },
          ],
          imageUrl
        };
      }
      
      setResult(resultData);
      setAnalyzing(false);
      // FIX #2: Show location modal immediately after setting result
      setShowLocationModal(true);
      
    } catch (err) {
      console.error('Analysis error:', err);
      setError('Failed to analyze image. Please try again.');
      setAnalyzing(false);
    }
  };

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      // Clear any previous errors
      setError(null);
      
      // Ensure file has proper metadata for Firebase upload
      // If it's from camera capture, it might not have a proper name
      let properFile = file;
      if (!file.name || file.name === 'image.jpg' || file.name === 'blob') {
        properFile = new File(
          [file],
          `coral-${Date.now()}.jpg`,
          { type: file.type || 'image/jpeg' }
        );
      }
      
      const reader = new FileReader();
      reader.onload = (e) => {
        analyzeImage(e.target.result, properFile);
      };
      reader.onerror = () => {
        setError('Failed to read image file.');
      };
      reader.readAsDataURL(properFile);
    }
    
    // Reset the input so same file can be selected again
    event.target.value = '';
  };

  // Helper to get GPS coordinates
  const getCurrentGPSLocation = () => {
    return new Promise((resolve) => {
      if (!navigator.geolocation) {
        resolve(null);
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (position) => resolve({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
          accuracy: position.coords.accuracy
        }),
        () => resolve(null),
        { timeout: 5000 }
      );
    });
  };

  // Handle save with location
  const handleSaveWithLocation = async () => {
    try {
      setSaving(true);
      
      let locationData = {};
      
      switch (locationType) {
        case LOCATION_TYPES.GPS:
          if (useGPS) {
            const coords = await getCurrentGPSLocation();
            if (coords) {
              locationData = {
                coordinates: { lat: coords.lat, lng: coords.lng },
                accuracy: coords.accuracy
              };
            } else {
              alert('Could not get GPS location. Please try another option.');
              setSaving(false);
              return;
            }
          }
          break;
          
        case LOCATION_TYPES.DIVE_SITE:
          console.log('🔍 DIVE_SITE case triggered');
          console.log('🔍 selectedSite value:', selectedSite);
          
          if (!selectedSite) {
            alert('Please select a dive site');
            setSaving(false);
            return;
          }
          
          // FIX: Search by ID, not name (selectedSite contains the ID)
          const site = USVI_DIVE_SITES.find(s => s.id === selectedSite);
          console.log('🔍 Found site object:', site);
          
          if (site) {
            locationData = {
              siteId: site.id,
              siteName: site.name,
              island: site.island
            };
            console.log('✅ locationData built:', locationData);
          } else {
            console.error('❌ Site not found in USVI_DIVE_SITES!');
          }
          break;
          
        case LOCATION_TYPES.CUSTOM_SITE:
          if (!customSiteName.trim()) {
            alert('Please enter a site name');
            setSaving(false);
            return;
          }
          locationData = {
            siteName: customSiteName,
            island: customSiteIsland,
            description: customSiteDescription
          };
          if (useGPS) {
            const coords = await getCurrentGPSLocation();
            if (coords) {
              locationData.coordinates = { lat: coords.lat, lng: coords.lng };
              locationData.accuracy = coords.accuracy;
            }
          }
          break;
          
        case LOCATION_TYPES.GENERAL_AREA:
          if (!selectedArea) {
            alert('Please select an area');
            setSaving(false);
            return;
          }
          const area = GENERAL_AREAS.find(a => a.name === selectedArea);
          if (area) {
            locationData = {
              generalArea: area.name,
              approximateCoordinates: area.approximateCenter
            };
          }
          break;
      }
      
      // Prepare observation data
      const observationData = {
        imageFile: currentImageFile,  // ADD THIS LINE
        prediction: result.prediction,
        confidence: parseFloat(result.confidence),
        allPredictions: result.allPredictions,
        timestamp: new Date().toISOString(),
        locationType: locationType,
        locationData: locationData,  // CHANGED from location to locationData
        isSensitive: isSensitive,
        notes: notes.trim()
      };
      
      // Save to Firebase and get cloud ID
      const saveResult = await saveObservation(observationData);
      const cloudId = saveResult?.id || null;
      
      // Save to local history with cloud ID
      saveToHistory(result, cloudId);
      
      // Reset states
      setShowLocationModal(false);
      setCurrentImageFile(null);
      setNotes('');
      setCustomSiteName('');
      setCustomSiteDescription('');
      setSelectedSite(null);
      setSelectedArea(null);
      
      alert('Observation saved successfully! 🪸');
      
    } catch (err) {
      console.error('Error saving observation:', err);
      alert('Failed to save to cloud, but saved locally. Check your connection.');
      // Still save locally even if cloud fails
      saveToHistory(result, null);
      setShowLocationModal(false);
    } finally {
      setSaving(false);
    }
  };

  const handleCancelLocation = () => {
    // Just close modal without saving
    setShowLocationModal(false);
    setCurrentImageFile(null);
    // Keep the result visible but without location data
  };

  // Handle batch save
  const handleBatchSave = async (selectedImages, reviewImages, location, isSensitive) => {
    try {
      await saveBatchObservations(selectedImages, reviewImages, location, isSensitive);
    } catch (error) {
      console.error('Error saving batch:', error);
      throw error;
    }
  };

  const getHealthColor = (prediction) => {
    if (prediction === 'Not Coral') return 'var(--coral-disease)';
    if (prediction.includes('Healthy')) return 'var(--coral-healthy)';
    if (prediction.includes('Bleached')) return 'var(--coral-warn)';
    if (prediction.includes('Dead')) return 'var(--coral-danger)';
    return 'var(--coral-disease)';
  };

  const getHealthIcon = (prediction) => {
    if (prediction === 'Not Coral') return '🚫';
    if (prediction.includes('Healthy')) return '🪸';
    if (prediction.includes('Bleached')) return '⚠️';
    if (prediction.includes('Dead')) return '💀';
    return '🦠';
  };

  return (
    <div className="App">
      {/* Header */}
      <header className="header">
        <h1>🪸 Reef Monitor</h1>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button 
            className="history-btn"
            onClick={() => {
              setShowHistory(!showHistory);
              if (!showHistory) loadHistory(); // Reload when opening
            }}
            title="View History"
          >
            <History size={24} />
          </button>
          <button 
            className="history-btn"
            onClick={() => setShowMap(true)}
            title="View Map"
          >
            <Map size={24} />
          </button>
        </div>
      </header>

      {/* Mode Toggle - REMOVED */}

      {/* Loading State - FIX #3: Only show if loading and no error */}
      {loading && !error && (
        <div className="loading-screen">
          <Loader className="spinner" size={64} />
          <h2>Loading AI Model...</h2>
          <p>Downloading coral health classifier (~77MB)</p>
          <p className="loading-tip">This only happens once!</p>
        </div>
      )}

      {/* Location Picker Modal */}
      {showLocationModal && (
        <LocationPicker
          locationType={locationType}
          setLocationType={setLocationType}
          selectedSite={selectedSite}
          setSelectedSite={setSelectedSite}
          selectedArea={selectedArea}
          setSelectedArea={setSelectedArea}
          customSiteName={customSiteName}
          setCustomSiteName={setCustomSiteName}
          customSiteIsland={customSiteIsland}
          setCustomSiteIsland={setCustomSiteIsland}
          customSiteDescription={customSiteDescription}
          setCustomSiteDescription={setCustomSiteDescription}
          useGPS={useGPS}
          setUseGPS={setUseGPS}
          isSensitive={isSensitive}
          setIsSensitive={setIsSensitive}
          notes={notes}
          setNotes={setNotes}
          onSave={handleSaveWithLocation}
          onCancel={handleCancelLocation}
          saving={saving}
        />
      )}

      {/* Welcome Screen - First Time Only */}
      {showWelcome && (
        <div className="welcome-overlay">
          <div className="welcome-modal">
            <div className="welcome-header">
              <h1>🪸 Reef Monitor</h1>
              <p className="welcome-subtitle">AI-Powered Coral Health Analysis</p>
            </div>
            
            <div className="welcome-content">
              <p className="welcome-developer">Developed by <strong>Daniel Basick</strong></p>
              
              <p className="welcome-description">
                An AI-powered tool for documenting coral health in the USVI. 
                Built to support marine researchers, dive operators, and citizen 
                scientists in tracking reef conditions over time.
              </p>
              
              <div className="welcome-features">
                <div className="welcome-feature">
                  <span className="feature-icon">🪸</span>
                  <span>Every scan helps build a community database</span>
                </div>
                <div className="welcome-feature">
                  <span className="feature-icon">🌊</span>
                  <span>Your observations contribute to conservation efforts</span>
                </div>
              </div>
              
              <p className="welcome-contact">
                Questions? <a href="mailto:DaBasick@yahoo.com">DaBasick@yahoo.com</a>
              </p>
            </div>
            
            <button className="welcome-btn" onClick={dismissWelcome}>
              Get Started
            </button>
          </div>
        </div>
      )}

      {/* Main Content */}
      {!showHistory && !showMap && viewMode === 'single' && (
        <main className="main">
          {/* Action Buttons */}
          {!result && !loading && (
            <div className="action-section">
              {/* Upload Image - Single Scan */}
              <button 
                className="action-btn primary"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload size={32} />
                <span>Upload Image</span>
              </button>
              
              {/* Upload Batch Button */}
              <button 
                className="action-btn secondary"
                onClick={() => setViewMode('batch')}
              >
                <Upload size={32} />
                <span>Upload Batch</span>
              </button>
              
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileUpload}
                style={{ display: 'none' }}
              />
              
              <input
                ref={cameraInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                onChange={handleFileUpload}
                style={{ display: 'none' }}
              />
            </div>
          )}

          {/* Analyzing State */}
          {analyzing && (
            <div className="analyzing">
              <Loader className="spinner" size={48} />
              <h2>Analyzing Coral Health...</h2>
              <p>AI processing in progress</p>
            </div>
          )}

          {/* Error State - FIX #4: Only show error if no result and not analyzing */}
          {error && !result && !analyzing && (
            <div className="error-banner">
              <Info size={20} />
              <span>{error}</span>
            </div>
          )}

          {/* Results */}
          {result && !analyzing && !showLocationModal && (
            <div className="results">
              <div className="result-image">
                <img src={result.imageUrl} alt="Analyzed coral" />
              </div>
              
              <div className="result-card">
                <div className="result-header">
                  <span className="result-icon">{getHealthIcon(result.prediction)}</span>
                  <div>
                    <h2>{result.prediction}</h2>
                    <p className="confidence">{result.confidence}% confidence</p>
                  </div>
                </div>
                
                <div className="confidence-bar">
                  <div 
                    className="confidence-fill"
                    style={{ 
                      width: `${result.confidence}%`,
                      backgroundColor: getHealthColor(result.prediction)
                    }}
                  />
                </div>

                <div className="all-predictions">
                  <h3>Detailed Analysis</h3>
                  {result.allPredictions.map((pred, i) => (
                    <div key={i} className="prediction-row">
                      <span className="pred-label">{pred.label}</span>
                      <div className="pred-bar-container">
                        <div 
                          className="pred-bar"
                          style={{ width: `${pred.confidence}%` }}
                        />
                      </div>
                      <span className="pred-value">{pred.confidence}%</span>
                    </div>
                  ))}
                </div>

                <button 
                  className="btn-new-scan"
                  onClick={() => {
                    setResult(null);
                    setError(null);
                    setCurrentImageFile(null);
                  }}
                >
                  New Scan
                  <ChevronRight size={20} />
                </button>
              </div>
            </div>
          )}

          {/* Info Card */}
          {!result && !analyzing && !loading && (
            <div className="info-card">
              <h3>How It Works</h3>
              <ol>
                <li>Take or upload a photo of coral</li>
                <li>AI analyzes the health condition</li>
                <li>Add location details for the database</li>
                <li>Contribute to global reef health monitoring</li>
              </ol>
            </div>
          )}

          {/* Coral Species Guide - NEW */}
          {!result && !analyzing && !loading && (
            <CoralGuide />
          )}
        </main>
      )}

      {/* Batch Scanner Mode */}
      {!showHistory && !showMap && viewMode === 'batch' && (
        <BatchScanner
          model={model}
          gateModel={gateModel}
          locationType={locationType}
          setLocationType={setLocationType}
          selectedSite={selectedSite}
          setSelectedSite={setSelectedSite}
          selectedArea={selectedArea}
          setSelectedArea={setSelectedArea}
          customSiteName={customSiteName}
          setCustomSiteName={setCustomSiteName}
          customSiteIsland={customSiteIsland}
          setCustomSiteIsland={setCustomSiteIsland}
          customSiteDescription={customSiteDescription}
          setCustomSiteDescription={setCustomSiteDescription}
          useGPS={useGPS}
          setUseGPS={setUseGPS}
          isSensitive={isSensitive}
          setIsSensitive={setIsSensitive}
          LOCATION_TYPES={LOCATION_TYPES}
          USVI_DIVE_SITES={USVI_DIVE_SITES}
          GENERAL_AREAS={GENERAL_AREAS}
          getCurrentGPSLocation={getCurrentGPSLocation}
          onBatchSave={handleBatchSave}
          onCancel={() => setViewMode('single')}
        />
      )}

      {/* History View */}
      {showHistory && (
        <div className="history-view">
          <div className="history-header">
            <h2>Scan History</h2>
            <button onClick={() => setShowHistory(false)}>Close</button>
          </div>
          
          {history.length === 0 ? (
            <div className="empty-history">
              <History size={64} />
              <p>No scans yet</p>
            </div>
          ) : (
            <div className="history-list">
              {history.map((item) => {
                // Batch item
                if (item.type === 'batch') {
                  const healthyCount = item.items.filter(i => i.prediction === 'Healthy Coral').length;
                  const bleachedCount = item.items.filter(i => i.prediction === 'Bleached Coral').length;
                  const notCoralCount = item.items.filter(i => i.prediction === 'Not Coral').length;
                  const isExpanded = expandedBatch === item.id;
                  
                  return (
                    <div key={item.id}>
                      <div 
                        className="history-item batch-item"
                        onClick={() => setExpandedBatch(isExpanded ? null : item.id)}
                        style={{ cursor: 'pointer' }}
                      >
                        <div className="batch-preview">
                          {item.items.slice(0, 4).map((img, idx) => (
                            <img 
                              key={idx} 
                              src={img.imageUrl} 
                              alt={`Batch scan ${idx + 1}`}
                            />
                          ))}
                          {item.items.length > 4 && (
                            <div className="batch-more">+{item.items.length - 4}</div>
                          )}
                        </div>
                        <div className="history-info">
                          <h4>📦 Batch Scan - {item.items.length} images</h4>
                          <p>{healthyCount} healthy, {bleachedCount} bleached{notCoralCount > 0 ? `, ${notCoralCount} not coral` : ''}</p>
                          <span className="history-date">
                            {new Date(item.timestamp).toLocaleDateString()}
                          </span>
                          {item.location?.siteName && (
                            <p className="location-name">📍 {item.location.siteName}</p>
                          )}
                          {item.synced && <span className="cloud-badge">☁️</span>}
                        </div>
                        <div
                          className="history-indicator"
                          style={{ backgroundColor:
                            healthyCount >= bleachedCount && healthyCount >= notCoralCount ? '#22c55e' :
                            bleachedCount >= notCoralCount ? '#ef4444' : '#9ca3af'
                          }}
                        />
                      </div>
                      
                      {/* Expanded batch view */}
                      {isExpanded && (
                        <div className="batch-expanded">
                          <div className="batch-expanded-grid">
                            {item.items.map((img, idx) => (
                              <div key={idx} className="batch-expanded-item">
                                <img src={img.imageUrl} alt={`Image ${idx + 1}`} />
                                <div className="batch-expanded-info">
                                  <span className={
                                    img.prediction === 'Healthy Coral' ? 'healthy' :
                                    img.prediction === 'Bleached Coral' ? 'bleached' : 'not-coral'
                                  }>
                                    {
                                      img.prediction === 'Healthy Coral' ? '🪸' :
                                      img.prediction === 'Bleached Coral' ? '⚠️' : '🚫'
                                    }
                                  </span>
                                  <span>{img.confidence?.toFixed?.(1)}%</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                }
                
                // Single item
                return (
                  <div key={item.id} className="history-item">
                    <img src={item.imageUrl} alt="Historical scan" />
                    <div className="history-info">
                      <h4>{item.prediction}</h4>
                      <p>{item.confidence?.toFixed?.(1) || item.confidence}% confident</p>
                      <span className="history-date">
                        {new Date(item.timestamp).toLocaleDateString()}
                      </span>
                      {item.location?.siteName && (
                        <p className="location-name">📍 {item.location.siteName}</p>
                      )}
                      {item.synced && <span className="cloud-badge">☁️</span>}
                    </div>
                    <div 
                      className="history-indicator"
                      style={{ backgroundColor: getHealthColor(item.prediction) }}
                    />
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Map View */}
      {showMap && (
        <MapView onBack={() => setShowMap(false)} />
      )}

      {/* Footer */}
      <footer className="footer">
        <p>Developed by Daniel Basick • <a href="mailto:DaBasick@yahoo.com">DaBasick@yahoo.com</a></p>
        <p>Powered by AI • Built for Conservation</p>
      </footer>
    </div>
  );
}

export default App;
