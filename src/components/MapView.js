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

// Custom colored markers with count badge
const createMarkerWithBadge = (color, count) => {
  return L.divIcon({
    className: 'custom-marker-with-badge',
    html: `
      <div style="position: relative;">
        <div style="
          background-color: ${color};
          width: 25px;
          height: 25px;
          border-radius: 50%;
          border: 3px solid white;
          box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        "></div>
        ${count > 1 ? `
          <div style="
            position: absolute;
            top: -8px;
            right: -8px;
            background-color: #2563eb;
            color: white;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            font-weight: bold;
            border: 2px solid white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
          ">${count}</div>
        ` : ''}
      </div>
    `,
    iconSize: [25, 25],
    iconAnchor: [12, 12]
  });
};

const MapView = ({ onBack }) => {
  const [observationGroups, setObservationGroups] = useState({});
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
          else if (data.location?.siteId && !data.isSensitive) {
            const site = USVI_DIVE_SITES.find(s => s.id === data.location.siteId);
            if (site) {
              obs.push({
                id: doc.id,
                ...data,
                location: {
                  ...data.location,
                  coordinates: { lat: site.lat, lng: site.lng }
                }
              });
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
        
        // Group observations by location (within ~10 meters)
        const grouped = {};
        obs.forEach(observation => {
          const lat = observation.location.coordinates.lat.toFixed(4);
          const lng = observation.location.coordinates.lng.toFixed(4);
          const key = `${lat},${lng}`;
          
          if (!grouped[key]) {
            grouped[key] = [];
          }
          grouped[key].push(observation);
        });
        
        console.log(`Loaded ${obs.length} observations grouped into ${Object.keys(grouped).length} locations`);
        setObservationGroups(grouped);
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
        
        {Object.entries(observationGroups).map(([locationKey, observations]) => {
          const firstObs = observations[0];
          const healthyCount = observations.filter(o => o.prediction === 'Healthy Coral').length;
          const bleachedCount = observations.length - healthyCount;
          const markerColor = healthyCount > bleachedCount ? '#22c55e' : '#ef4444';
          
          return (
            <Marker
              key={locationKey}
              position={[firstObs.location.coordinates.lat, firstObs.location.coordinates.lng]}
              icon={createMarkerWithBadge(markerColor, observations.length)}
            >
              <Popup maxWidth={400} maxHeight={500}>
                <div style={{ 
                  fontFamily: 'system-ui, -apple-system, sans-serif',
                  maxHeight: '450px',
                  overflowY: 'auto'
                }}>
                  <h3 style={{ margin: '0 0 8px 0', fontSize: '16px' }}>
                    📍 {firstObs.location.siteName || firstObs.location.customSiteName || 'Unknown Site'}
                  </h3>
                  <p style={{ margin: '0 0 12px 0', fontSize: '13px', color: '#666' }}>
                    {observations.length} observation{observations.length > 1 ? 's' : ''} at this location
                    {observations.length > 1 && ` (${healthyCount} healthy, ${bleachedCount} bleached)`}
                  </p>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {observations.map((obs, idx) => (
                      <div key={obs.id} style={{
                        borderBottom: idx < observations.length - 1 ? '1px solid #e5e7eb' : 'none',
                        paddingBottom: '12px'
                      }}>
                        {obs.imageUrl && (
                          <img 
                            src={obs.imageUrl} 
                            alt="coral observation" 
                            style={{ 
                              width: '100%', 
                              marginBottom: '6px', 
                              borderRadius: '4px',
                              cursor: 'pointer'
                            }}
                            onClick={() => window.open(obs.imageUrl, '_blank')}
                          />
                        )}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ 
                            fontWeight: 'bold', 
                            color: obs.prediction === 'Healthy Coral' ? '#22c55e' : '#ef4444',
                            fontSize: '14px'
                          }}>
                            {obs.prediction === 'Healthy Coral' ? '🪸 Healthy' : '⚠️ Bleached'}
                          </span>
                          <span style={{ fontSize: '13px', color: '#666' }}>
                            {parseFloat(obs.confidence).toFixed(1)}%
                          </span>
                        </div>
                        <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: '#999' }}>
                          {new Date(obs.timestamp.seconds * 1000).toLocaleDateString()} at {new Date(obs.timestamp.seconds * 1000).toLocaleTimeString()}
                        </p>
                        {obs.source === 'batch' && obs.batchId && (
                          <p style={{ margin: '2px 0 0 0', fontSize: '11px', color: '#3b82f6' }}>
                            📦 Batch scan
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
};

export default MapView;
