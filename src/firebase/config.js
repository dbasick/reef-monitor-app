import { initializeApp } from 'firebase/app';
import { getFirestore } from 'firebase/firestore';
import { getStorage } from 'firebase/storage';
import { getAuth, signInAnonymously } from 'firebase/auth';

// Your Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyD0JXHO4DzfHocbMb7DzxFkMnllIEjt2n0",
  authDomain: "reef-health-monitor-c7263.firebaseapp.com",
  projectId: "reef-health-monitor-c7263",
  storageBucket: "reef-health-monitor-c7263.firebasestorage.app",
  messagingSenderId: "930786260606",
  appId: "1:930786260606:web:e0f0a3323cb8d2bd724a2f"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);
const storage = getStorage(app);
const auth = getAuth(app);

// Sign in anonymously for privacy (no login required)
signInAnonymously(auth).catch((error) => {
  console.warn('Anonymous auth failed:', error);
});

export { db, storage, auth };
