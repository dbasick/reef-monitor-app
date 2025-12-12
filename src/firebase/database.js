import { 
  collection, 
  addDoc, 
  query, 
  where, 
  orderBy, 
  limit,
  getDocs,
  Timestamp 
} from 'firebase/firestore';
import { ref, uploadBytes, getDownloadURL } from 'firebase/storage';
import imageCompression from 'browser-image-compression';
import { db, storage, auth } from './config';

/**
 * Location type options for observations
 */
export const LOCATION_TYPES = {
  GPS: 'gps',
  DIVE_SITE: 'dive_site',
  CUSTOM_SITE: 'custom_site',
  GENERAL: 'general'
};

/**
 * Popular USVI dive sites
 */
export const USVI_DIVE_SITES = [
  { id: 'coki_beach', name: 'Coki Beach', island: 'St. Thomas' },
  { id: 'cow_and_calf', name: 'Cow and Calf Rocks', island: 'St. Thomas' },
  { id: 'wreck_alley', name: 'Wreck Alley', island: 'St. Thomas' },
  { id: 'french_cap', name: 'French Cap', island: 'St. Thomas' },
  { id: 'hull_bay', name: 'Hull Bay', island: 'St. Thomas' },
  { id: 'frederiksted_pier', name: 'Frederiksted Pier', island: 'St. Croix' },
  { id: 'salt_river', name: 'Salt River Canyon', island: 'St. Croix' },
  { id: 'cane_bay', name: 'Cane Bay Wall', island: 'St. Croix' },
  { id: 'trunk_bay', name: 'Trunk Bay', island: 'St. John' },
  { id: 'haulover_bay', name: 'Haulover Bay', island: 'St. John' },
];

/**
 * General areas for privacy
 */
export const GENERAL_AREAS = [
  { id: 'st_thomas_north', name: 'St. Thomas - North Shore' },
  { id: 'st_thomas_south', name: 'St. Thomas - South Shore' },
  { id: 'st_thomas_east', name: 'St. Thomas - East End' },
  { id: 'st_thomas_west', name: 'St. Thomas - West End' },
  { id: 'st_croix_north', name: 'St. Croix - North Shore' },
  { id: 'st_croix_south', name: 'St. Croix - South Shore' },
  { id: 'st_john_north', name: 'St. John - North Shore' },
  { id: 'st_john_south', name: 'St. John - South Shore' },
  { id: 'water_island', name: 'Water Island' },
];

/**
 * Compress image before upload
 */
async function compressImage(file) {
  const options = {
    maxSizeMB: 1,
    maxWidthOrHeight: 1920,
    useWebWorker: true,
    fileType: 'image/jpeg'
  };
  
  try {
    return await imageCompression(file, options);
  } catch (error) {
    console.error('Image compression failed:', error);
    return file;
  }
}

/**
 * Get current GPS coordinates
 */
function getCurrentLocation() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve(null);
      return;
    }
    
    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
          accuracy: position.coords.accuracy
        });
      },
      (error) => {
        console.warn('Geolocation error:', error);
        resolve(null);
      },
      { timeout: 5000, maximumAge: 60000 }
    );
  });
}

/**
 * Save coral observation to cloud database
 */
export async function saveObservation(data) {
  try {
    const {
      imageFile,
      prediction,
      confidence,
      locationType,
      locationData,
      notes = '',
      isSensitive = false,
      waterTemp,
      depth
    } = data;

    // 1. Compress and upload image
    const compressedImage = await compressImage(imageFile);
    const imageId = `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const imageRef = ref(storage, `coral-images/${imageId}.jpg`);
    
    const metadata = {
      contentType: 'image/jpeg',
      customMetadata: {
        userId: auth.currentUser?.uid || 'anonymous',
        prediction: prediction,
        timestamp: new Date().toISOString()
      }
    };
    
    await uploadBytes(imageRef, compressedImage, metadata);
    const imageUrl = await getDownloadURL(imageRef);

    // 2. Build location object
    let location = { type: locationType };

    switch (locationType) {
      case LOCATION_TYPES.GPS:
        location = {
          ...location,
          coordinates: locationData.coordinates,
          accuracy: locationData.accuracy,
          siteName: locationData.siteName || null
        };
        break;
        
      case LOCATION_TYPES.DIVE_SITE:
        location = {
          ...location,
          siteId: locationData.siteId,
          siteName: locationData.siteName,
          island: locationData.island
        };
        break;
        
      case LOCATION_TYPES.CUSTOM_SITE:
        location = {
          ...location,
          customSiteName: locationData.customSiteName,
          island: locationData.island || null,
          coordinates: locationData.coordinates || null,
          description: locationData.description || null
        };
        break;
        
      case LOCATION_TYPES.GENERAL:
        location = {
          ...location,
          areaId: locationData.areaId,
          areaName: locationData.areaName
        };
        break;
    }

    // 3. Create observation document
    const observation = {
      userId: auth.currentUser?.uid || 'anonymous',
      timestamp: Timestamp.now(),
      prediction: prediction,
      confidence: confidence,
      imageUrl: imageUrl,
      imageId: imageId,
      location: location,
      isSensitive: isSensitive,
      ...(waterTemp && { waterTemp: waterTemp }),
      ...(depth && { depth: depth }),
      notes: notes,
      deviceInfo: {
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        isIOS: /iPhone|iPad|iPod/.test(navigator.userAgent)
      }
    };

    // 4. Save to Firestore
    const docRef = await addDoc(collection(db, 'observations'), observation);
    
    console.log('✅ Observation saved to cloud:', docRef.id);
    
    return {
      success: true,
      id: docRef.id,
      imageUrl: imageUrl
    };
    
  } catch (error) {
    console.error('❌ Failed to save observation:', error);
    
    return {
      success: false,
      error: error.message,
      queuedForRetry: false
    };
  }
}

/**
 * Query observations from cloud database
 */
export async function queryObservations(filters = {}) {
  try {
    let q = collection(db, 'observations');
    const constraints = [];

    if (filters.prediction) {
      constraints.push(where('prediction', '==', filters.prediction));
    }

    if (filters.locationType) {
      constraints.push(where('location.type', '==', filters.locationType));
    }

    if (filters.siteId) {
      constraints.push(where('location.siteId', '==', filters.siteId));
    }

    if (filters.startDate) {
      constraints.push(where('timestamp', '>=', Timestamp.fromDate(new Date(filters.startDate))));
    }
    if (filters.endDate) {
      constraints.push(where('timestamp', '<=', Timestamp.fromDate(new Date(filters.endDate))));
    }

    constraints.push(orderBy('timestamp', 'desc'));
    constraints.push(limit(filters.limit || 50));

    q = query(q, ...constraints);
    const snapshot = await getDocs(q);
    
    return snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data(),
      timestamp: doc.data().timestamp.toDate()
    }));
    
  } catch (error) {
    console.error('Failed to query observations:', error);
    return [];
  }
}
