import React from 'react';
import { MapPin, Navigation, Map, Lock } from 'lucide-react';
import { LOCATION_TYPES, USVI_DIVE_SITES, GENERAL_AREAS } from '../firebase/database';

export default function LocationPicker({
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
  notes,
  setNotes,
  onSave,
  onCancel,
  saving
}) {
  return (
    <div className="location-modal">
      <div className="location-modal-content">
        <h3>📍 Where was this scan taken?</h3>
        
        {/* Location Type Selector */}
        <div className="location-type-selector">
          <button
            className={locationType === LOCATION_TYPES.GPS ? 'active' : ''}
            onClick={() => setLocationType(LOCATION_TYPES.GPS)}
          >
            <Navigation size={20} />
            GPS
          </button>
          <button
            className={locationType === LOCATION_TYPES.DIVE_SITE ? 'active' : ''}
            onClick={() => setLocationType(LOCATION_TYPES.DIVE_SITE)}
          >
            <MapPin size={20} />
            Dive Site
          </button>
          <button
            className={locationType === LOCATION_TYPES.CUSTOM_SITE ? 'active' : ''}
            onClick={() => setLocationType(LOCATION_TYPES.CUSTOM_SITE)}
          >
            <MapPin size={20} />
            New Site
          </button>
          <button
            className={locationType === LOCATION_TYPES.GENERAL ? 'active' : ''}
            onClick={() => setLocationType(LOCATION_TYPES.GENERAL)}
          >
            <Map size={20} />
            General
          </button>
        </div>

        {/* GPS Option */}
        {locationType === LOCATION_TYPES.GPS && (
          <div className="location-option">
            <p>Share exact GPS coordinates</p>
            <label>
              <input
                type="checkbox"
                checked={useGPS}
                onChange={(e) => setUseGPS(e.target.checked)}
              />
              Use my current location
            </label>
          </div>
        )}

        {/* Dive Site Option */}
        {locationType === LOCATION_TYPES.DIVE_SITE && (
          <div className="location-option">
            <p>Select a known dive site</p>
            <select 
              value={selectedSite || ''} 
              onChange={(e) => setSelectedSite(e.target.value)}
              className="site-selector"
            >
              <option value="">-- Select Dive Site --</option>
              {USVI_DIVE_SITES.map(site => (
                <option key={site.id} value={site.id}>
                  {site.name} ({site.island})
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Custom Site Option */}
        {locationType === LOCATION_TYPES.CUSTOM_SITE && (
          <div className="location-option">
            <p>Create a new dive site</p>
            <input
              type="text"
              placeholder="Site name (e.g., 'Secret Garden')"
              value={customSiteName}
              onChange={(e) => setCustomSiteName(e.target.value)}
              className="custom-site-input"
            />
            <select 
              value={customSiteIsland} 
              onChange={(e) => setCustomSiteIsland(e.target.value)}
              className="island-selector"
            >
              <option value="St. Thomas">St. Thomas</option>
              <option value="St. Croix">St. Croix</option>
              <option value="St. John">St. John</option>
              <option value="Water Island">Water Island</option>
            </select>
            <textarea
              placeholder="Optional: Describe this site..."
              value={customSiteDescription}
              onChange={(e) => setCustomSiteDescription(e.target.value)}
              className="custom-site-description"
              rows={2}
            />
            <label className="custom-site-gps">
              <input
                type="checkbox"
                checked={useGPS}
                onChange={(e) => setUseGPS(e.target.checked)}
              />
              📍 Also save GPS coordinates
            </label>
            <div className="info-box">
              💡 This site will be added to the community database!
            </div>
          </div>
        )}

        {/* General Area Option */}
        {locationType === LOCATION_TYPES.GENERAL && (
          <div className="location-option">
            <p>Select a general area</p>
            <select 
              value={selectedArea || ''} 
              onChange={(e) => setSelectedArea(e.target.value)}
              className="area-selector"
            >
              <option value="">-- Select Area --</option>
              {GENERAL_AREAS.map(area => (
                <option key={area.id} value={area.id}>
                  {area.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Sensitive Location Toggle */}
        <div className="sensitive-toggle">
          <label>
            <Lock size={16} />
            <input
              type="checkbox"
              checked={isSensitive}
              onChange={(e) => setIsSensitive(e.target.checked)}
            />
            Sensitive location (rare species)
          </label>
        </div>

        {/* Notes */}
        <textarea
          placeholder="Add notes (depth, conditions, etc.)"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className="notes-input"
          rows={3}
        />

        {/* Action Buttons */}
        <div className="modal-actions">
          <button onClick={onCancel} disabled={saving} className="cancel-btn">
            Cancel
          </button>
          <button onClick={onSave} disabled={saving} className="save-btn">
            {saving ? 'Saving...' : 'Save to Cloud'}
          </button>
        </div>
      </div>
    </div>
  );
}
