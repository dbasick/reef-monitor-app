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
import { signInAnonymously } from 'firebase/auth';
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
 * Popular USVI dive sites with GPS coordinates
 */
export const USVI_DIVE_SITES = [
  // ST. THOMAS
  { 
    id: 'coki_beach', 
    name: 'Coki Beach', 
    island: 'St. Thomas',
    lat: 18.35167,
    lng: -64.86583
  },
  { 
    id: 'cow_and_calf', 
    name: 'Cow and Calf Rocks', 
    island: 'St. Thomas',
    lat: 18.30430,
    lng: -64.84662
  },
  { 
    id: 'wreck_alley', 
    name: 'Wreck Alley', 
    island: 'St. Thomas',
    lat: 18.31000,
    lng: -64.95000
  },
  { 
    id: 'french_cap', 
    name: 'French Cap', 
    island: 'St. Thomas',
    lat: 18.2330,
    lng: -64.8529
  },
  { 
    id: 'hull_bay', 
    name: 'Hull Bay', 
    island: 'St. Thomas',
    lat: 18.37087,
    lng: -64.95269
  },
  { 
    id: 'lovango_south', 
    name: 'Lovango (South)', 
    island: 'St. Thomas',
    lat: 18.3603,
    lng: -64.8045
  },
  { 
    id: 'lovango_north', 
    name: 'Lovango (North)', 
    island: 'St. Thomas',
    lat: 18.3648,
    lng: -64.8031
  },
  
  // ST. CROIX
  { 
    id: 'frederiksted_pier', 
    name: 'Frederiksted Pier', 
    island: 'St. Croix',
    lat: 17.71380,
    lng: -64.88931
  },
  { 
    id: 'salt_river', 
    name: 'Salt River Canyon', 
    island: 'St. Croix',
    lat: 17.78470,
    lng: -64.75637
  },
  { 
    id: 'cane_bay', 
    name: 'Cane Bay Wall', 
    island: 'St. Croix',
    lat: 17.77422,
    lng: -64.81373
  },
  
  // ST. JOHN
  { 
    id: 'trunk_bay', 
    name: 'Trunk Bay', 
    island: 'St. John',
    lat: 18.35426,
    lng: -64.76942
  },
  { 
    id: 'haulover_bay', 
    name: 'Haulover Bay', 
    island: 'St. John',
    lat: 18.34885,
    lng: -64.67806
  },
  { 
    id: 'annaberg', 
    name: 'Annaberg', 
    island: 'St. John',
    lat: 18.36421,
    lng: -64.72506
  },
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
 * Ensure user is authenticated (anonymously if needed)
 * This is required for Firebase Storage uploads
 */
async function ensureAuth() {
  if (!auth.currentUser) {
    try {
      console.log('🔐 No user signed in, signing in anonymously...');
      await signInAnonymously(auth);
      console.log('✅ Anonymous sign-in successful:', auth.currentUser.uid);
    } catch (error) {
      console.error('❌ Anonymous sign-in failed:', error);
      throw new Error('Authentication required for uploads');
    }
  } else {
    console.log('✅ User already authenticated:', auth.currentUser.uid);
  }
}

/**
 * Compress image before upload
 */
async function compressImage(file) {
  // Validate that we have a proper File/Blob
  if (!file || !(file instanceof Blob || file instanceof File)) {
    console.error('Invalid file type passed to compressImage:', typeof file);
    throw new Error('Invalid image file');
  }

  const options = {
    maxSizeMB: 1,
    maxWidthOrHeight: 1920,
    useWebWorker: true,
    fileType: 'image/jpeg'
  };
  
  try {
    console.log('🗜️ Compressing image:', file.name, file.size, 'bytes');
    const compressed = await imageCompression(file, options);
    console.log('✅ Compressed to:', compressed.size, 'bytes');
    return compressed;
  } catch (error) {
    console.error('❌ Image compression failed:', error);
    // Return original file if compression fails
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
  console.log('🔍 saveObservation called with full data:', JSON.stringify(data, null, 2));
  try {
    // CRITICAL: Ensure user is authenticated before any Firebase operations
    await ensureAuth();
    
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

    console.log('📦 Extracted values:');
    console.log('  - imageFile:', imageFile ? 'exists' : 'MISSING');
    console.log('  - locationType:', locationType);
    console.log('  - locationData:', JSON.stringify(locationData, null, 2));

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
        // Find the selected dive site to get its coordinates
        const selectedSite = USVI_DIVE_SITES.find(s => s.id === locationData.siteId);
        location = {
          ...location,
          siteId: locationData.siteId,
          siteName: locationData.siteName,
          island: locationData.island,
          // Automatically add coordinates if site is pre-populated
          coordinates: selectedSite ? { lat: selectedSite.lat, lng: selectedSite.lng } : null
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
