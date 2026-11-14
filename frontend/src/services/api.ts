import { useAuth } from '../contexts/AuthContext';
import { useOffline } from '../contexts/OfflineContext';

export interface PredictionResult {
  diagnosis: string;
  confidence: number;
  predictions: Array<{
    class: string;
    confidence: number;
  }>;
  uncertain: boolean;
  confidence_floor: number;
  gradcam_url?: string;
}

export interface AdviceResult {
  advice: string;
  source?: string;
  disclaimer?: string;
  care_level?: string;
}

export interface RAGResult {
  answer: string;
  sources?: string[];
}

export interface ModelInfo {
  runtime: string;
  classes: number;
  confidence_floor: number;
  input_size: number;
  model_version: string;
}

export interface ClassesResult {
  classes: string[];
}

export interface AgriPulseResult {
  plan: string;
  reasons: string[];
  predicted_class: string;
  confidence: number;
  advice: string;
  sell_recommendation: string;
  weather_risk: string;
  decisions: string[];
}

export interface SyncResult {
  synced: string[];
  merged: string[];
  rejected: string[];
  server_predictions: Record<string, {
    predicted_class: string;
    confidence: number;
    uncertain: boolean;
  }>;
}

export interface HealthResult {
  status: string;
  model: ModelInfo;
}

class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: string
  ) {
    super(message);
    this.name = 'APIError';
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  auth: { apiKey: string; apiBase: string }
): Promise<T> {
  const { apiKey, apiBase } = auth;
  const url = `${apiBase}${endpoint}`;

  const headers = new Headers(options.headers);
  headers.set('X-API-Key', apiKey);

  // Don't set Content-Type for FormData - browser will set it with boundary
  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let detail = '';
    try {
      const errorData = await response.json();
      detail = errorData.detail || errorData.error || JSON.stringify(errorData);
    } catch {
      detail = await response.text();
    }
    throw new APIError(
      detail || `HTTP ${response.status}`,
      response.status,
      detail
    );
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}

// Hook-based API service
export function useAPI() {
  const { apiKey, apiBase } = useAuth();
  const { queuePredictions, isOnline } = useOffline();

  const predict = async (
    file: File,
    options: { top_k?: number; include_cam?: boolean } = {}
  ): Promise<PredictionResult> => {
    const formData = new FormData();
    formData.append('file', file);
    if (options.top_k) formData.append('top_k', String(options.top_k));
    if (options.include_cam) formData.append('include_cam', 'true');

    try {
      const result = await request<PredictionResult>('/predict', {
        method: 'POST',
        body: formData,
      }, { apiKey, apiBase });

      // Queue for offline sync if needed
      if (!isOnline) {
        await queuePredictions([{
          imageBlob: file,
          mimeType: file.type,
          predictedClass: result.diagnosis,
          confidence: result.confidence,
          uncertain: result.uncertain,
        }]);
      }

      return result;
    } catch (error) {
      // Queue for offline retry
      if (!isOnline) {
        await queuePredictions([{
          imageBlob: file,
          mimeType: file.type,
          predictedClass: 'pending',
          confidence: 0,
          uncertain: true,
        }]);
      }
      throw error;
    }
  };

  const getAdvice = async (classLabel: string, lang: string = 'en'): Promise<AdviceResult> => {
    const formData = new FormData();
    formData.append('class_label', classLabel);
    formData.append('lang', lang);
    return request<AdviceResult>('/advice', {
      method: 'POST',
      body: formData,
    }, { apiKey, apiBase });
  };

  const askRAG = async (query: string, lang: string = 'en'): Promise<RAGResult> => {
    const formData = new FormData();
    formData.append('query', query);
    formData.append('lang', lang);
    return request<RAGResult>('/rag', {
      method: 'POST',
      body: formData,
    }, { apiKey, apiBase });
  };

  const runAgriPulse = async (
    file: File,
    options: { language?: string; district?: string; offline?: boolean } = {}
  ): Promise<AgriPulseResult> => {
    const formData = new FormData();
    formData.append('file', file);
    if (options.language) formData.append('language', options.language);
    if (options.district) formData.append('district', options.district);
    if (options.offline) formData.append('offline', 'true');
    return request<AgriPulseResult>('/agripulse', {
      method: 'POST',
      body: formData,
    }, { apiKey, apiBase });
  };

  const getModelInfo = async (): Promise<ModelInfo> => {
    return request<ModelInfo>('/model-info', {}, { apiKey, apiBase });
  };

  const getClasses = async (): Promise<string[]> => {
    const result = await request<ClassesResult>('/classes', {}, { apiKey, apiBase });
    return result.classes;
  };

  const getHealth = async (): Promise<HealthResult> => {
    return request<HealthResult>('/health', {}, { apiKey, apiBase });
  };

  const getReadiness = async (): Promise<{ status: string; model?: ModelInfo; error?: string }> => {
    try {
      return await request('/ready', {}, { apiKey, apiBase });
    } catch (error) {
      if (error instanceof APIError && error.status === 503) {
        return { status: 'not ready', error: error.detail };
      }
      throw error;
    }
  };

  const submitFeedback = async (
    classLabel: string,
    correct: boolean,
    comment: string = ''
  ): Promise<{ status: string }> => {
    const formData = new FormData();
    formData.append('class_label', classLabel);
    formData.append('correct', String(correct));
    formData.append('comment', comment);
    return request('/feedback', {
      method: 'POST',
      body: formData,
    }, { apiKey, apiBase });
  };

  const deleteMyData = async (): Promise<{ status: string }> => {
    return request('/data', {
      method: 'DELETE',
    }, { apiKey, apiBase });
  };

  const syncOfflineQueue = async (): Promise<SyncResult> => {
    return request<SyncResult>('/sync', {
      method: 'POST',
      body: JSON.stringify({
        device_id: localStorage.getItem('agridoc_device_id') || '',
        items: [], // Will be filled by the offline context
      }),
    }, { apiKey, apiBase });
  };

  return {
    predict,
    getAdvice,
    askRAG,
    runAgriPulse,
    getModelInfo,
    getClasses,
    getHealth,
    getReadiness,
    submitFeedback,
    deleteMyData,
    syncOfflineQueue,
  };
}

// Export APIError for error handling
export { APIError };