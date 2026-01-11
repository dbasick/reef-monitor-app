// Add this function to your firebase/database.js file

import { db, storage, auth } from './config';
import { collection, addDoc, serverTimestamp } from 'firebase/firestore';
import { ref, uploadBytes, getDownloadURL } from 'firebase/storage';

/**
 * Save batch observations to Firebase
 * @param {Array} selectedImages - Images selected for normal observations
 * @param {Array} reviewImages - Images flagged for review queue
 * @param {Object} location - Location data for entire batch
 * @param {Boolean} isSensitive - Whether location is sensitive
 */
export const saveBatchObservations = async (selectedImages, reviewImages, location, isSensitive) => {
  const userId = auth.currentUser?.uid;
  
  if (!userId) {
    throw new Error('User not authenticated');
  }

  const batchId = `batch_${Date.now()}`;
  
  try {
    // Save regular observations
    const savedObservations = await Promise.all(
      selectedImages.map(async (imageData, index) => {
        try {
          // Upload image to Storage
          const imageRef = ref(
            storage, 
            `observations/${userId}/${batchId}/${imageData.name}`
          );
          await uploadBytes(imageRef, imageData.file);
          const imageUrl = await getDownloadURL(imageRef);

          // Prepare observation data
          const observationData = {
            prediction: imageData.result.prediction,
            confidence: parseFloat(imageData.result.confidence),
            allPredictions: imageData.result.allPredictions,
            timestamp: serverTimestamp(),
            imageUrl,
            userId,
            batchId,
            batchIndex: index,
            locationType: location.type,
            location: {
              ...(location.siteName && { siteName: location.siteName }),
              ...(location.island && { island: location.island }),
              ...(location.description && { description: location.description }),
              ...(location.generalArea && { generalArea: location.generalArea }),
              ...(location.coordinates && { coordinates: location.coordinates }),
              ...(location.approximateCoordinates && { approximateCoordinates: location.approximateCoordinates }),
              ...(location.accuracy && { accuracy: location.accuracy })
            },
            isSensitive,
            source: 'batch'
          };

          // Save to Firestore
          const docRef = await addDoc(collection(db, 'observations'), observationData);
          
          return { success: true, id: docRef.id };
        } catch (error) {
          console.error(`Failed to save image ${imageData.name}:`, error);
          return { success: false, error: error.message };
        }
      })
    );

    // Save review queue items
    const savedReviews = await Promise.all(
      reviewImages.map(async (imageData, index) => {
        try {
          // Upload image to Storage
          const imageRef = ref(
            storage, 
            `needs_review/${userId}/${batchId}/${imageData.name}`
          );
          await uploadBytes(imageRef, imageData.file);
          const imageUrl = await getDownloadURL(imageRef);

          // Prepare review data
          const reviewData = {
            prediction: imageData.result.prediction,
            confidence: parseFloat(imageData.result.confidence),
            allPredictions: imageData.result.allPredictions,
            timestamp: serverTimestamp(),
            imageUrl,
            userId,
            batchId,
            batchIndex: index,
            locationType: location.type,
            location: {
              ...(location.siteName && { siteName: location.siteName }),
              ...(location.island && { island: location.island }),
              ...(location.description && { description: location.description }),
              ...(location.generalArea && { generalArea: location.generalArea }),
              ...(location.coordinates && { coordinates: location.coordinates }),
              ...(location.approximateCoordinates && { approximateCoordinates: location.approximateCoordinates }),
              ...(location.accuracy && { accuracy: location.accuracy })
            },
            isSensitive,
            reviewStatus: 'pending', // 'pending', 'approved', 'rejected'
            reviewReason: 'low_confidence',
            source: 'batch'
          };

          // Save to needs_review collection
          const docRef = await addDoc(collection(db, 'needs_review'), reviewData);
          
          return { success: true, id: docRef.id };
        } catch (error) {
          console.error(`Failed to save review image ${imageData.name}:`, error);
          return { success: false, error: error.message };
        }
      })
    );

    // Count successes
    const observationSuccesses = savedObservations.filter(r => r.success).length;
    const reviewSuccesses = savedReviews.filter(r => r.success).length;

    console.log(`Batch save complete: ${observationSuccesses}/${selectedImages.length} observations, ${reviewSuccesses}/${reviewImages.length} reviews`);

    return {
      batchId,
      observations: observationSuccesses,
      reviews: reviewSuccesses,
      total: observationSuccesses + reviewSuccesses
    };

  } catch (error) {
    console.error('Error in saveBatchObservations:', error);
    throw error;
  }
};
