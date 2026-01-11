import React, { useState, useRef } from 'react';
import { Camera, Upload, X, Check, AlertCircle, Download, Save, Eye } from 'lucide-react';
import * as ort from 'onnxruntime-web';
import './BatchScanner.css';

const BatchScanner = ({ 
  model,
  locationType,
  setLocationType,
  selectedSite,
  setSelectedSite,
  selectedArea,
  setSelectedArea,
  customSiteName,
  setCustomSiteName,
  customSiteIsland,
  setCustomSiteIsland,
  customSiteDescription,
  setCustomSiteDescription,
  useGPS,
  setUseGPS,
  isSensitive,
  setIsSensitive,
  LOCATION_TYPES,
  USVI_DIVE_SITES,
  GENERAL_AREAS,
  getCurrentGPSLocation,
  onBatchSave,
  onCancel
}) => {
  // Batch workflow states
  const [step, setStep] = useState('location'); // 'location', 'upload', 'results'
  const [lockedLocation, setLockedLocation] = useState(null);
  const [images, setImages] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const fileInputRef = useRef(null);

  // Handle location lock
  const handleLockLocation = async () => {
    let locationData = null;

    try {
      switch (locationType) {
        case LOCATION_TYPES.GPS:
          if (useGPS) {
            const coords = await getCurrentGPSLocation();
            if (coords) {
              locationData = {
                type: LOCATION_TYPES.GPS,
                coordinates: { lat: coords.lat, lng: coords.lng },
                accuracy: coords.accuracy,
                displayName: `GPS (${coords.lat.toFixed(4)}°, ${coords.lng.toFixed(4)}°)`
              };
            } else {
              alert('Could not get GPS location. Please try another option.');
              return;
            }
          }
          break;

        case LOCATION_TYPES.DIVE_SITE:
          if (!selectedSite) {
            alert('Please select a dive site');
            return;
          }
          const site = USVI_DIVE_SITES.find(s => s.name === selectedSite);
          if (site) {
            locationData = {
              type: LOCATION_TYPES.DIVE_SITE,
              siteName: site.name,
              island: site.island,
              coordinates: { lat: site.lat, lng: site.lng },
              displayName: `${site.name}, ${site.island}`
            };
          }
          break;

        case LOCATION_TYPES.CUSTOM_SITE:
          if (!customSiteName.trim()) {
            alert('Please enter a site name');
            return;
          }
          locationData = {
            type: LOCATION_TYPES.CUSTOM_SITE,
            siteName: customSiteName,
            island: customSiteIsland,
            description: customSiteDescription,
            displayName: `${customSiteName}, ${customSiteIsland}`
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
            return;
          }
          const area = GENERAL_AREAS.find(a => a.name === selectedArea);
          if (area) {
            locationData = {
              type: LOCATION_TYPES.GENERAL_AREA,
              generalArea: area.name,
              approximateCoordinates: area.approximateCenter,
              displayName: area.name
            };
          }
          break;
      }

      if (locationData) {
        setLockedLocation(locationData);
        setStep('upload');
      }
    } catch (error) {
      console.error('Error locking location:', error);
      alert('Failed to set location. Please try again.');
    }
  };

  // Edit location - go back to location setup
  const handleEditLocation = () => {
    setStep('location');
  };

  // Handle file selection
  const handleFileSelect = (event) => {
    const files = Array.from(event.target.files);
    
    if (files.length === 0) return;
    
    if (files.length > 50) {
      alert('Please select 50 or fewer images at a time');
      return;
    }

    const imageData = files.map(file => ({
      file,
      preview: URL.createObjectURL(file),
      name: file.name,
      status: 'pending',
      result: null,
      selected: true,
      reviewQueue: false,
      timestamp: new Date().toISOString()
    }));

    setImages(imageData);
    setCurrentIndex(0);
  };

  // Process batch
  const processBatch = async () => {
    if (!model || images.length === 0) return;

    setProcessing(true);
    setStep('results');

    for (let i = 0; i < images.length; i++) {
      setCurrentIndex(i);
      const image = images[i];

      try {
        setImages(prev => prev.map((img, idx) => 
          idx === i ? { ...img, status: 'processing' } : img
        ));

        const result = await classifyImage(image.file);

        // Auto-uncheck low confidence images (< 60%)
        const autoSelected = result.confidence >= 60;

        const resultData = {
          ...image,
          status: 'complete',
          result: result,
          selected: autoSelected,
          processedAt: new Date().toISOString()
        };

        setImages(prev => prev.map((img, idx) => 
          idx === i ? resultData : img
        ));

      } catch (error) {
        console.error(`Error processing ${image.name}:`, error);
        
        setImages(prev => prev.map((img, idx) => 
          idx === i ? { ...img, status: 'error', error: error.message, selected: false } : img
        ));
      }

      await new Promise(resolve => setTimeout(resolve, 100));
    }

    setProcessing(false);
  };

  // Classify single image
  const classifyImage = async (file) => {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = async () => {
        try {
          const canvas = document.createElement('canvas');
          const ctx = canvas.getContext('2d');
          
          canvas.width = 224;
          canvas.height = 224;
          ctx.drawImage(img, 0, 0, 224, 224);
          
          const imageData = ctx.getImageData(0, 0, 224, 224);
          const { data } = imageData;
          
          const float32Data = new Float32Array(224 * 224 * 3);
          
          for (let i = 0; i < 224 * 224; i++) {
            float32Data[i * 3] = data[i * 4] / 255.0;
            float32Data[i * 3 + 1] = data[i * 4 + 1] / 255.0;
            float32Data[i * 3 + 2] = data[i * 4 + 2] / 255.0;
          }
          
          const tensor = new ort.Tensor('float32', float32Data, [1, 224, 224, 3]);
          const feeds = {};
          feeds[model.inputNames[0]] = tensor;
          const results = await model.run(feeds);
          
          const output = results[model.outputNames[0]];
          
          // Model outputs single healthy probability, not array of [bleached, healthy]
          const healthyProb = output.data[0];
          const bleachedProb = 1 - healthyProb;
          
          const isHealthy = healthyProb > 0.5;
          const prediction = isHealthy ? 'Healthy Coral' : 'Bleached Coral';
          const confidence = (isHealthy ? healthyProb : bleachedProb) * 100;
          
          resolve({
            prediction: prediction,
            confidence: confidence,
            allPredictions: {
              'Bleached Coral': bleachedProb * 100,
              'Healthy Coral': healthyProb * 100
            }
          });
          
        } catch (error) {
          reject(error);
        }
      };
      
      img.onerror = () => reject(new Error('Failed to load image'));
      img.src = URL.createObjectURL(file);
    });
  };

  // Toggle individual image selection
  const toggleImageSelection = (index) => {
    setImages(prev => prev.map((img, idx) => 
      idx === index ? { ...img, selected: !img.selected, reviewQueue: false } : img
    ));
  };

  // Toggle review queue flag
  const toggleReviewQueue = (index) => {
    setImages(prev => prev.map((img, idx) => 
      idx === index ? { ...img, reviewQueue: !img.reviewQueue, selected: false } : img
    ));
  };

  // Select/deselect all
  const toggleSelectAll = () => {
    const allSelected = images.every(img => img.selected || img.reviewQueue);
    setImages(prev => prev.map(img => ({ ...img, selected: !allSelected, reviewQueue: false })));
  };

  // Export CSV
  const exportResults = () => {
    const csvHeader = 'Filename,Classification,Confidence,Healthy Score,Bleached Score,Status,Action,Timestamp\n';
    const csvRows = images.map(img => {
      const action = img.reviewQueue ? 'Review Queue' : img.selected ? 'Save' : 'Reject';
      if (img.result) {
        return `"${img.name}","${img.result.prediction}",${img.result.confidence.toFixed(2)},${img.result.allPredictions['Healthy Coral'].toFixed(2)},${img.result.allPredictions['Bleached Coral'].toFixed(2)},"${img.status}","${action}","${img.processedAt}"`;
      } else {
        return `"${img.name}","N/A","N/A","N/A","N/A","${img.status}","${action}","${img.timestamp}"`;
      }
    }).join('\n');
    
    const csvContent = csvHeader + csvRows;
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `reef-monitor-batch-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Save batch to Firebase
  const handleSaveBatch = async () => {
    const selectedImages = images.filter(img => img.selected && img.result);
    const reviewImages = images.filter(img => img.reviewQueue && img.result);

    if (selectedImages.length === 0 && reviewImages.length === 0) {
      alert('No images selected to save');
      return;
    }

    try {
      await onBatchSave(selectedImages, reviewImages, lockedLocation, isSensitive);
      
      alert(`Saved ${selectedImages.length} observations and ${reviewImages.length} for review! 🪸`);
      
      // Cleanup images
      images.forEach(img => URL.revokeObjectURL(img.preview));
      
      // Reset everything and go back to home (single scan mode)
      setImages([]);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      setLockedLocation(null);
      
      // Call the cancel callback to return to single scan home
      onCancel();
      
    } catch (error) {
      console.error('Error saving batch:', error);
      alert('Failed to save batch. Please try again.');
      // Don't reset on error - let user try again
    }
  };

  // Get summary stats
  const getSummary = () => {
    const total = images.length;
    const completed = images.filter(img => img.status === 'complete').length;
    const selected = images.filter(img => img.selected).length;
    const reviewQueue = images.filter(img => img.reviewQueue).length;
    const rejected = images.filter(img => !img.selected && !img.reviewQueue && img.status === 'complete').length;
    const healthy = images.filter(img => img.result?.prediction.includes('Healthy')).length;
    const bleached = images.filter(img => img.result?.prediction.includes('Bleached')).length;
    const errors = images.filter(img => img.status === 'error').length;
    
    return { total, completed, selected, reviewQueue, rejected, healthy, bleached, errors };
  };

  const summary = getSummary();

  // Render location setup step
  const renderLocationSetup = () => (
    <div className="batch-location-setup">
      <h2>📍 Set Batch Location</h2>
      <p className="batch-subtitle">All images in this batch will be tagged with the same location</p>

      <div className="location-type-selector">
        <label className={locationType === LOCATION_TYPES.DIVE_SITE ? 'active' : ''}>
          <input
            type="radio"
            name="locationType"
            checked={locationType === LOCATION_TYPES.DIVE_SITE}
            onChange={() => setLocationType(LOCATION_TYPES.DIVE_SITE)}
          />
          <span>📍 Saved Dive Site</span>
        </label>

        <label className={locationType === LOCATION_TYPES.CUSTOM_SITE ? 'active' : ''}>
          <input
            type="radio"
            name="locationType"
            checked={locationType === LOCATION_TYPES.CUSTOM_SITE}
            onChange={() => setLocationType(LOCATION_TYPES.CUSTOM_SITE)}
          />
          <span>✏️ Custom Site</span>
        </label>

        <label className={locationType === LOCATION_TYPES.GENERAL_AREA ? 'active' : ''}>
          <input
            type="radio"
            name="locationType"
            checked={locationType === LOCATION_TYPES.GENERAL_AREA}
            onChange={() => setLocationType(LOCATION_TYPES.GENERAL_AREA)}
          />
          <span>🗺️ General Area</span>
        </label>

        <label className={locationType === LOCATION_TYPES.GPS ? 'active' : ''}>
          <input
            type="radio"
            name="locationType"
            checked={locationType === LOCATION_TYPES.GPS}
            onChange={() => setLocationType(LOCATION_TYPES.GPS)}
          />
          <span>📡 GPS Only</span>
        </label>
      </div>

      {/* Location type specific fields */}
      <div className="location-fields">
        {locationType === LOCATION_TYPES.DIVE_SITE && (
          <div className="field">
            <label>Select Dive Site:</label>
            <select value={selectedSite || ''} onChange={(e) => setSelectedSite(e.target.value)}>
              <option value="">Choose a site...</option>
              {USVI_DIVE_SITES.map(site => (
                <option key={site.name} value={site.name}>
                  {site.name} - {site.island}
                </option>
              ))}
            </select>
          </div>
        )}

        {locationType === LOCATION_TYPES.CUSTOM_SITE && (
          <>
            <div className="field">
              <label>Site Name: *</label>
              <input
                type="text"
                value={customSiteName}
                onChange={(e) => setCustomSiteName(e.target.value)}
                placeholder="e.g., Secret Reef"
              />
            </div>
            <div className="field">
              <label>Island:</label>
              <select value={customSiteIsland} onChange={(e) => setCustomSiteIsland(e.target.value)}>
                <option value="St. Thomas">St. Thomas</option>
                <option value="St. John">St. John</option>
                <option value="St. Croix">St. Croix</option>
              </select>
            </div>
            <div className="field">
              <label>Description:</label>
              <textarea
                value={customSiteDescription}
                onChange={(e) => setCustomSiteDescription(e.target.value)}
                placeholder="Optional details about this site..."
                rows="3"
              />
            </div>
            <div className="field checkbox-field">
              <label>
                <input
                  type="checkbox"
                  checked={useGPS}
                  onChange={(e) => setUseGPS(e.target.checked)}
                />
                Use GPS for coordinates
              </label>
            </div>
          </>
        )}

        {locationType === LOCATION_TYPES.GENERAL_AREA && (
          <div className="field">
            <label>Select Area:</label>
            <select value={selectedArea || ''} onChange={(e) => setSelectedArea(e.target.value)}>
              <option value="">Choose an area...</option>
              {GENERAL_AREAS.map(area => (
                <option key={area.name} value={area.name}>
                  {area.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {locationType === LOCATION_TYPES.GPS && (
          <div className="field">
            <p className="gps-info">📡 Device GPS will be used to tag this batch</p>
          </div>
        )}
      </div>

      {/* Sensitive location toggle */}
      <div className="field checkbox-field">
        <label>
          <input
            type="checkbox"
            checked={isSensitive}
            onChange={(e) => setIsSensitive(e.target.checked)}
          />
          🔒 Mark as sensitive location (coordinates hidden from public)
        </label>
      </div>

      <div className="location-actions">
        <button className="btn-secondary" onClick={onCancel}>
          Cancel
        </button>
        <button className="btn-primary" onClick={handleLockLocation}>
          Lock Location & Continue
        </button>
      </div>
    </div>
  );

  // Render upload step
  const renderUpload = () => (
    <div className="batch-upload">
      <div className="locked-location-header">
        <div className="location-info">
          <h3>🔒 {lockedLocation.displayName}</h3>
          {lockedLocation.coordinates && (
            <p className="coordinates">
              {lockedLocation.coordinates.lat.toFixed(4)}°N, {lockedLocation.coordinates.lng.toFixed(4)}°W
            </p>
          )}
          {isSensitive && <span className="sensitive-badge">🔒 Sensitive</span>}
        </div>
        <button className="btn-secondary btn-sm" onClick={handleEditLocation}>
          Edit Location
        </button>
      </div>

      <div className="upload-section">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          onChange={handleFileSelect}
          style={{ display: 'none' }}
          id="batch-file-input"
        />
        
        {images.length === 0 ? (
          <label htmlFor="batch-file-input" className="upload-dropzone">
            <Upload size={48} />
            <h3>Select Images</h3>
            <p>Choose up to 50 coral images from this location</p>
            <span className="btn-primary">Browse Files</span>
          </label>
        ) : (
          <>
            <div className="upload-header">
              <p>{images.length} image{images.length > 1 ? 's' : ''} selected</p>
              <div className="upload-actions">
                <label htmlFor="batch-file-input" className="btn-secondary btn-sm">
                  Change Files
                </label>
                <button className="btn-primary" onClick={processBatch}>
                  🚀 Analyze {images.length} Image{images.length > 1 ? 's' : ''}
                </button>
              </div>
            </div>

            <div className="preview-grid">
              {images.map((image, index) => (
                <div key={index} className="preview-card">
                  <img src={image.preview} alt={image.name} />
                  <p className="preview-name">{image.name}</p>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );

  // Render results step
  const renderResults = () => {
    if (!lockedLocation) {
      // Safety check - shouldn't happen, but prevents crash
      return <div>Error: Location data missing</div>;
    }
    
    return (
    <div className="batch-results">
      <div className="locked-location-header">
        <div className="location-info">
          <h3>🔒 {lockedLocation.displayName}</h3>
          {lockedLocation.coordinates && (
            <p className="coordinates">
              {lockedLocation.coordinates.lat.toFixed(4)}°N, {lockedLocation.coordinates.lng.toFixed(4)}°W
            </p>
          )}
        </div>
        <button className="btn-secondary btn-sm" onClick={handleEditLocation}>
          Edit Location
        </button>
      </div>

      {processing && (
        <div className="batch-progress">
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${((currentIndex + 1) / images.length) * 100}%` }}
            />
          </div>
          <p className="progress-text">
            Processing image {currentIndex + 1} of {images.length}...
          </p>
        </div>
      )}

      {!processing && summary.completed > 0 && (
        <>
          <div className="results-summary">
            <div className="results-instructions">
              ✓ <strong>Check</strong> images to save<span>•</span>👁️ Click <strong>Save for Review</strong> for uncertain results
            </div>

            <div className="summary-stats">
              <div className="stat">
                <span className="stat-label">Total</span>
                <span className="stat-value">{summary.total}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Completed</span>
                <span className="stat-value">{summary.completed}</span>
              </div>
              <div className="stat healthy">
                <span className="stat-label">Healthy</span>
                <span className="stat-value">{summary.healthy}</span>
              </div>
              <div className="stat bleached">
                <span className="stat-label">Bleached</span>
                <span className="stat-value">{summary.bleached}</span>
              </div>
            </div>

            <div className="action-summary">
              <div className="action-stat selected">
                <Check size={16} />
                <span>{summary.selected} to save</span>
              </div>
              <div className="action-stat review">
                <Eye size={16} />
                <span>{summary.reviewQueue} for review</span>
              </div>
              <div className="action-stat rejected">
                <X size={16} />
                <span>{summary.rejected} rejected</span>
              </div>
            </div>
          </div>

          <div className="results-actions">
            <button className="btn-secondary" onClick={toggleSelectAll}>
              {images.every(img => img.selected || img.reviewQueue) ? 'Deselect All' : 'Select All'}
            </button>
            <button className="btn-secondary" onClick={() => {
              images.forEach(img => URL.revokeObjectURL(img.preview));
              setImages([]);
              setStep('upload');
            }}>
              ← Start Over
            </button>
            <button className="btn-secondary" onClick={exportResults}>
              <Download size={16} /> Export CSV
            </button>
            <button 
              className="btn-primary" 
              onClick={handleSaveBatch}
              disabled={summary.selected === 0 && summary.reviewQueue === 0}
            >
              <Save size={16} /> Save Batch ({summary.selected + summary.reviewQueue})
            </button>
          </div>
        </>
      )}

      <div className="results-grid">
        {images.map((image, index) => (
          <div 
            key={index} 
            className={`result-card ${image.status} ${image.selected ? 'selected' : ''} ${image.reviewQueue ? 'review' : ''}`}
            onClick={() => image.status === 'complete' && toggleImageSelection(index)}
            style={{ cursor: image.status === 'complete' ? 'pointer' : 'default' }}
          >
            <div className="card-image-container">
              <img src={image.preview} alt={image.name} />
              
              {image.status === 'processing' && (
                <div className="processing-overlay">
                  <div className="spinner" />
                </div>
              )}
              
              {image.status === 'complete' && image.result && (
                <>
                  <div className={`result-badge ${image.result.prediction.includes('Healthy') ? 'healthy' : 'bleached'}`}>
                    {image.result.prediction.includes('Healthy') ? '🪸 Healthy' : '⚠️ Bleached'}
                  </div>
                  
                  {image.result.confidence < 60 && (
                    <div className="low-confidence-badge">
                      <AlertCircle size={14} /> Low Confidence
                    </div>
                  )}

                  {/* Small "Save for Review" icon button in top-right corner */}
                  {!image.reviewQueue && (
                    <button 
                      className="review-icon-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleReviewQueue(index);
                      }}
                      title="Save for review"
                    >
                      <Eye size={16} />
                    </button>
                  )}

                  {/* Show checkmark if selected */}
                  {image.selected && (
                    <div className="selected-indicator">
                      <Check size={24} />
                    </div>
                  )}

                  {/* Show eye if in review queue */}
                  {image.reviewQueue && (
                    <div className="review-indicator">
                      <Eye size={24} />
                    </div>
                  )}
                </>
              )}
              
              {image.status === 'error' && (
                <div className="result-badge error">Error</div>
              )}
            </div>
            
            <div className="card-details">
              <p className="card-filename">{image.name}</p>
              
              {image.result && (
                <div className="confidence-bar">
                  <span className="confidence-label">Confidence:</span>
                  <div className="confidence-bar-bg">
                    <div 
                      className={`confidence-bar-fill ${image.result.confidence >= 60 ? 'high' : 'low'}`}
                      style={{ width: `${image.result.confidence}%` }}
                    />
                  </div>
                  <span className="confidence-value">{image.result.confidence.toFixed(1)}%</span>
                </div>
              )}
              
              {image.status === 'error' && (
                <p className="card-error">{image.error}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
    );
  };

  return (
    <div className="batch-scanner">
      {step === 'location' && renderLocationSetup()}
      {step === 'upload' && renderUpload()}
      {step === 'results' && renderResults()}
    </div>
  );
};

export default BatchScanner;
