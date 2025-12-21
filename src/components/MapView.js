import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { collection, getDocs } from 'firebase/firestore';
import { db } from '../firebase/config';
import { USVI_DIVE_SITES } from '../firebase/database';
import L from 'leaflet';

// Fix for default marker icons in webpack
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

// Custom colored markers
const createColorIcon = (color) => {
  return L.divIcon({
    className: 'custom-marker',
    html: `<div style="
      background-color: ${color};
      width: 20px;
      height: 20px;
      border-radius: 50%;
      border: 2px solid white;
      box-shadow: 0 2px 5px rgba(0,0,0,0.3);
    "></div>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10]
  });
};

const healthyIcon = createColorIcon('#22c55e'); // green
const bleachedIcon = createColorIcon('#ef4444'); // red

const MapView = ({ onBack }) => {
  const [observations, setObservations] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchObservations = async () => {
      try {
        const observationsRef = collection(db, 'observations');
        const querySnapshot = await getDocs(observationsRef);
        
        const obs = [];
        querySnapshot.forEach((doc) => {
          const data = doc.data();
          
          // CASE 1: Observation already has coordinates (new format)
          if (data.location?.coordinates && !data.isSensitive) {
            obs.push({
              id: doc.id,
              ...data
            });
          }
          // CASE 2: Legacy observation with dive site ID but no coordinates
          // Look up coordinates from USVI_DIVE_SITES array
          else if (data.location?.siteId && !data.isSensitive) {
            const site = USVI_DIVE_SITES.find(s => s.id === data.location.siteId);
            if (site) {
              // Temporarily add coordinates for map display
              // (doesn't modify Firebase, just for this session)
              obs.push({
                id: doc.id,
                ...data,
                location: {
                  ...data.location,
                  coordinates: { lat: site.lat, lng: site.lng }
                }
              });
              console.log(`✓ Added coordinates for legacy observation at ${site.name}`);
            }
          }
          // CASE 3: Custom sites with user-provided coordinates
          else if (data.location?.customSiteName && data.location?.coordinates && !data.isSensitive) {
            obs.push({
              id: doc.id,
              ...data
            });
          }
        });
        
        console.log(`Loaded ${obs.length} observations for map (including ${querySnapshot.size - obs.length} without location data)`);
        setObservations(obs);
        setLoading(false);
      } catch (error) {
        console.error('Error fetching observations:', error);
        setLoading(false);
      }
    };

    fetchObservations();
  }, []);

  // Center on USVI - shows all three islands
  const center = [17.9, -64.8];
  const zoom = 10;

  if (loading) {
    return (
      <div style={{ 
        padding: '20px', 
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}>
        Loading map...
      </div>
    );
  }

  return (
    <div style={{ position: 'relative', height: '100vh', width: '100%' }}>
      {/* Back button */}
      <button
        onClick={onBack}
        style={{
          position: 'absolute',
          top: '10px',
          left: '10px',
          zIndex: 1000,
          padding: '10px 15px',
          backgroundColor: 'white',
          border: 'none',
          borderRadius: '5px',
          boxShadow: '0 2px 5px rgba(0,0,0,0.3)',
          cursor: 'pointer',
          fontFamily: 'system-ui, -apple-system, sans-serif',
          fontSize: '16px'
        }}
      >
        ← Back
      </button>

      <MapContainer 
        center={center} 
        zoom={zoom} 
        style={{ height: '100%', width: '100%' }}
        zoomControl={true}
      >
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          attribution='Esri, DigitalGlobe, GeoEye'
          maxZoom={18}
        />
        
        {observations.map(obs => (
          <Marker
            key={obs.id}
            position={[obs.location.coordinates.lat, obs.location.coordinates.lng]}
            icon={obs.prediction === 'Healthy Coral' ? healthyIcon : bleachedIcon}
          >
            <Popup>
              <div style={{ minWidth: '150px', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
                {obs.imageUrl && (
                  <img 
                    src={obs.imageUrl} 
                    alt="coral observation" 
                    style={{ width: '100%', marginBottom: '8px', borderRadius: '4px' }}
                  />
                )}
                <p style={{ margin: '4px 0', fontWeight: 'bold' }}>
                  {obs.prediction}
                </p>
                <p style={{ margin: '4px 0', fontSize: '0.9em' }}>
                  Confidence: {parseFloat(obs.confidence).toFixed(1)}%
                </p>
                <p style={{ margin: '4px 0', fontSize: '0.85em', color: '#666' }}>
                  {new Date(obs.timestamp.seconds * 1000).toLocaleDateString()}
                </p>
                {(obs.location?.diveSite || obs.location?.siteName || obs.location?.customSiteName) && (
                  <p style={{ margin: '4px 0', fontSize: '0.85em' }}>
                    📍 {obs.location.diveSite || obs.location.siteName || obs.location.customSiteName}
                  </p>
                )}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
};

export default MapView;
