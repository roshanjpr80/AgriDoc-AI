import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

interface QueuedPrediction {
  id: string;
  timestamp: number;
  imageBlob: Blob;
  mimeType: string;
  predictedClass: string;
  confidence: number;
  uncertain: boolean;
  farmerCorrect?: boolean;
  farmerComment?: string;
}

interface OfflineContextType {
  isOnline: boolean;
  queuedCount: number;
  queuePredictions: (predictions: Omit<QueuedPrediction, 'id' | 'timestamp'>[]) => Promise<void>;
  syncQueue: () => Promise<void>;
  clearQueue: () => Promise<void>;
  getQueue: () => Promise<QueuedPrediction[]>;
}

const OfflineContext = createContext<OfflineContextType | undefined>(undefined);

const DB_NAME = 'agridoc-offline';
const STORE_NAME = 'predictions';
const SYNC_ENDPOINT = '/sync';
const QUEUE_TTL_HOURS = 72;

async function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: 'id' });
        store.createIndex('timestamp', 'timestamp', { unique: false });
      }
    };
  });
}

export function OfflineProvider({ children }: { children: React.ReactNode }) {
  const [isOnline, setIsOnline] = useState(true);
  const [queuedCount, setQueuedCount] = useState(0);

  // Check online status
  const checkOnline = useCallback(async () => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 4000);
      const response = await fetch('/api/health', { signal: controller.signal });
      clearTimeout(timeoutId);
      setIsOnline(response.ok);
    } catch {
      setIsOnline(false);
    }
  }, []);

  // Periodic online check
  useEffect(() => {
    checkOnline();
    const interval = setInterval(checkOnline, 30000);
    window.addEventListener('online', checkOnline);
    window.addEventListener('offline', () => setIsOnline(false));
    return () => {
      clearInterval(interval);
      window.removeEventListener('online', checkOnline);
      window.removeEventListener('offline', () => setIsOnline(false));
    };
  }, [checkOnline]);

  // Load queue count on mount
  useEffect(() => {
    loadQueueCount();
  }, []);

  const loadQueueCount = useCallback(async () => {
    try {
      const db = await openDB();
      const tx = db.transaction(STORE_NAME, 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const countRequest = store.count();
      countRequest.onsuccess = () => setQueuedCount(countRequest.result);
      await new Promise<void>((resolve, reject) => {
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
      });
    } catch {
      setQueuedCount(0);
    }
  }, []);

  const queuePredictions = useCallback(async (predictions: Omit<QueuedPrediction, 'id' | 'timestamp'>[]) => {
    const db = await openDB();
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);

    const now = Date.now();
    const ttlMs = QUEUE_TTL_HOURS * 60 * 60 * 1000;

    for (const pred of predictions) {
      const id = crypto.randomUUID();
      const item: QueuedPrediction = {
        ...pred,
        id,
        timestamp: now,
      };

      // Convert blob to base64 for storage
      const base64 = await blobToBase64(pred.imageBlob);
      const itemToStore = { ...item, imageBase64: base64 };
      delete (itemToStore as any).imageBlob;

      store.put(itemToStore);
    }

    // Clean old entries
    const index = store.index('timestamp');
    const cutoff = now - ttlMs;
    const range = IDBKeyRange.upperBound(cutoff);
    const deleteRequest = index.openCursor(range);
    deleteRequest.onsuccess = (event) => {
      const cursor = (event.target as IDBRequest).result;
      if (cursor) {
        cursor.delete();
        cursor.continue();
      }
    };

    await new Promise<void>((resolve, reject) => {
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });

    await loadQueueCount();
  }, [loadQueueCount]);

  const getQueue = useCallback(async (): Promise<QueuedPrediction[]> => {
    const db = await openDB();
    const tx = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    const request = store.getAll();

    return new Promise((resolve, reject) => {
      request.onsuccess = () => {
        const items = request.result.map(item => ({
          ...item,
          imageBlob: base64ToBlob(item.imageBase64, item.mimeType),
        }));
        delete (items[0] as any)?.imageBase64;
        resolve(items as QueuedPrediction[]);
      };
      request.onerror = () => reject(request.error);
    });
  }, []);

  const syncQueue = useCallback(async () => {
    if (!isOnline) return;

    const queue = await getQueue();
    if (!queue.length) return;

    const apiBase = localStorage.getItem('agridoc_api_base') || 'http://localhost:9998';
    const apiKey = localStorage.getItem('agridoc_api_key') || '';

    const items = await Promise.all(queue.map(async (item) => ({
      id: item.id,
      ts: item.timestamp,
      image_b64: await blobToBase64(item.imageBlob),
      mime_type: item.mimeType,
      predicted_class: item.predictedClass,
      confidence: item.confidence,
      uncertain: item.uncertain,
      farmer_correct: item.farmerCorrect,
      farmer_comment: item.farmerComment || '',
    })));

    try {
      const response = await fetch(`${apiBase}${SYNC_ENDPOINT}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
        body: JSON.stringify({ device_id: getDeviceId(), items }),
      });

      if (!response.ok) throw new Error('Sync failed');

      const result = await response.json();

      // Remove synced items from queue
      const db = await openDB();
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);

      [...result.synced, ...result.merged].forEach(id => store.delete(id));

      await new Promise<void>((resolve, reject) => {
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
      });

      await loadQueueCount();
      return result;
    } catch (error) {
      console.error('Sync failed:', error);
      throw error;
    }
  }, [isOnline, getQueue, loadQueueCount]);

  const clearQueue = useCallback(async () => {
    const db = await openDB();
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    store.clear();

    await new Promise<void>((resolve, reject) => {
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });

    await loadQueueCount();
  }, [loadQueueCount]);

  return (
    <OfflineContext.Provider value={{
      isOnline,
      queuedCount,
      queuePredictions,
      syncQueue,
      clearQueue,
      getQueue,
    }}>
      {children}
    </OfflineContext.Provider>
  );
}

export function useOffline() {
  const context = useContext(OfflineContext);
  if (!context) throw new Error('useOffline must be used within OfflineProvider');
  return context;
}

// Helper functions
function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve((reader.result as string).split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

function base64ToBlob(base64: string, mimeType: string): Blob {
  const byteCharacters = atob(base64);
  const byteArrays = [];
  for (let i = 0; i < byteCharacters.length; i += 512) {
    const slice = byteCharacters.slice(i, i + 512);
    const byteNumbers = new Array(slice.length);
    for (let j = 0; j < slice.length; j++) {
      byteNumbers[j] = slice.charCodeAt(j);
    }
    byteArrays.push(new Uint8Array(byteNumbers));
  }
  return new Blob(byteArrays, { type: mimeType });
}

function getDeviceId(): string {
  let deviceId = localStorage.getItem('agridoc_device_id');
  if (!deviceId) {
    deviceId = crypto.randomUUID();
    localStorage.setItem('agridoc_device_id', deviceId);
  }
  return deviceId;
}