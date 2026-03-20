/**
 * API Client for communicating with the FastAPI backend
 */
import type { AxiosError, AxiosRequestConfig, AxiosResponse } from 'axios'
import axios, { AxiosInstance } from 'axios'

import type {
  UploadResponse,
  Image,
  PaginatedResponse,
  BatchAnalyzeResponse,
  BatchDeleteResponse,
} from '@/types'

const BATCH_ANALYZE_TIMEOUT_MS = 5 * 60 * 1000

/** Backend URL only for server-side requests; browser uses same-origin `/api/v1` via rewrites. */
function resolveServerBackendBase(): string {
  return (
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    'http://127.0.0.1:8080'
  ).replace(/\/$/, '')
}

// API response interface
export interface ApiResponse<T = unknown> {
  data: T
  message?: string
}

// API error interface
export interface ApiError {
  detail: string
  status?: number
}

/**
 * Create axios instance with default configuration
 */
const createApiClient = (): AxiosInstance => {
  const client = axios.create({
    timeout: 30000,
  })

  // Request interceptor - same-origin API in the browser; absolute URL on the server only
  client.interceptors.request.use(
    async (config) => {
      const base =
        typeof window !== 'undefined'
          ? '/api/v1'
          : `${resolveServerBackendBase()}/api/v1`
      config.baseURL = base

      // Let browser/axios set multipart boundaries automatically for FormData.
      if (typeof FormData !== 'undefined' && config.data instanceof FormData && config.headers) {
        if (
          typeof (config.headers as { set?: (_name: string, _value?: string) => void }).set ===
          'function'
        ) {
          ;(config.headers as { set: (_name: string, _value?: string) => void }).set(
            'Content-Type',
            undefined
          )
        } else {
          delete (config.headers as Record<string, string>)['Content-Type']
        }
      }
      return config
    },
    (error) => Promise.reject(error)
  )

  // Response interceptor - Handle errors
  client.interceptors.response.use(
    (response) => response,
    async (error: AxiosError<ApiError>) => {
      // Return formatted error
      const apiError: ApiError = {
        detail: error.response?.data?.detail || error.message || 'An error occurred',
        status: error.response?.status,
      }

      return Promise.reject(apiError)
    }
  )

  return client
}

// Export singleton instance
export const apiClient = createApiClient()

/**
 * API methods
 */
export const api = {
  get: <T = unknown>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> =>
    apiClient.get<T>(url, config),

  post: <T = unknown>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<AxiosResponse<T>> => apiClient.post<T>(url, data, config),

  put: <T = unknown>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<AxiosResponse<T>> => apiClient.put<T>(url, data, config),

  patch: <T = unknown>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<AxiosResponse<T>> => apiClient.patch<T>(url, data, config),

  delete: <T = unknown>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> =>
    apiClient.delete<T>(url, config),
}

/**
 * AI Model interface
 */
export interface AIModel {
  name: string
  description: string
  is_active: boolean
  is_loaded: boolean
  configurable: boolean
  configured: boolean
}

export interface AIModelConfigField {
  key: string
  label: string
  field_type: 'text' | 'password' | 'url'
  required: boolean
  secret: boolean
  placeholder?: string | null
  help_text?: string | null
}

export interface AIModelDetail extends AIModel {
  config_fields: AIModelConfigField[]
  config: Record<string, string>
  configured_secret_fields: string[]
}

export interface AIModelConnectionTestResponse {
  ok: boolean
  status: string
  message: string
  details: Record<string, unknown>
}

export interface AIPromptVersionSummary {
  id: string
  prompt_id: string
  version_number: number
  commit_message?: string | null
  created_by?: string | null
  created_at: string
}

export interface AIPromptVersionDetail extends AIPromptVersionSummary {
  system_prompt: string
  user_prompt: string
}

export interface AIPromptSummary {
  id: string
  model_name: string
  name: string
  description?: string | null
  is_active: boolean
  current_version_id?: string | null
  current_version_number?: number | null
  created_at: string
  updated_at: string
}

export interface AIPromptDetail extends AIPromptSummary {
  current_version?: AIPromptVersionDetail | null
}

export interface CreateAIPromptPayload {
  model_name: string
  name: string
  description?: string | null
  is_active: boolean
  system_prompt: string
  user_prompt: string
  commit_message?: string | null
  created_by?: string | null
}

export interface UpdateAIPromptPayload {
  name?: string
  description?: string | null
  is_active?: boolean
}

export interface CreateAIPromptVersionPayload {
  system_prompt: string
  user_prompt: string
  commit_message?: string | null
  created_by?: string | null
}

/**
 * AI Analyze API
 */
export const aiAnalyzeApi = {
  getModels: () => api.get<AIModel[]>('/ai/models'),

  getModel: (modelName: string) =>
    api.get<AIModelDetail>(`/ai/models/${encodeURIComponent(modelName)}`),

  setActiveModel: (modelName: string) => api.post('/ai/models/active', { model_name: modelName }),

  getActiveModel: () => api.get<AIModel | null>('/ai/models/active'),

  deactivateActiveModel: () => api.delete('/ai/models/active'),

  updateModelConfig: (modelName: string, config: Record<string, string | null>) =>
    api.put<AIModelDetail>(`/ai/models/${encodeURIComponent(modelName)}/config`, { config }),

  testConnection: (modelName: string) =>
    api.post<AIModelConnectionTestResponse>(
      `/ai/models/${encodeURIComponent(modelName)}/test-connection`
    ),

  getImageAnalysis: (imageId: string) =>
    api.get('/images/' + imageId + '/analysis'),

  analyzeImage: (imageId: string, forceNew: boolean = false) =>
    api.post('/ai/analyze/' + imageId, { force_new: forceNew }),
}

export const aiPromptApi = {
  listPrompts: (modelName?: string) =>
    api.get<AIPromptSummary[]>('/ai/prompts', {
      params: modelName ? { model_name: modelName } : undefined,
    }),

  getPrompt: (promptId: string) =>
    api.get<AIPromptDetail>(`/ai/prompts/${encodeURIComponent(promptId)}`),

  createPrompt: (payload: CreateAIPromptPayload) =>
    api.post<AIPromptDetail>('/ai/prompts', payload),

  updatePrompt: (promptId: string, payload: UpdateAIPromptPayload) =>
    api.patch<AIPromptDetail>(`/ai/prompts/${encodeURIComponent(promptId)}`, payload),

  deletePrompt: (promptId: string) =>
    api.delete<{ deleted: boolean; prompt_id: string }>(
      `/ai/prompts/${encodeURIComponent(promptId)}`
    ),

  listPromptVersions: (promptId: string) =>
    api.get<AIPromptVersionSummary[]>(`/ai/prompts/${encodeURIComponent(promptId)}/versions`),

  getPromptVersion: (promptId: string, versionId: string) =>
    api.get<AIPromptVersionDetail>(
      `/ai/prompts/${encodeURIComponent(promptId)}/versions/${encodeURIComponent(versionId)}`
    ),

  createPromptVersion: (promptId: string, payload: CreateAIPromptVersionPayload) =>
    api.post<AIPromptVersionDetail>(
      `/ai/prompts/${encodeURIComponent(promptId)}/versions`,
      payload
    ),
}

/**
 * Upload progress callback type
 */
export type UploadProgressCallback = (_progress: number) => void

/**
 * Upload API
 */
export const uploadApi = {
  /**
   * Upload images with optional pre-computed hashes
   */
  uploadImages: async (
    files: File[],
    hashes?: string[],
    onProgress?: UploadProgressCallback
  ): Promise<AxiosResponse<UploadResponse>> => {
    const formData = new FormData()

    // Append files
    files.forEach((file) => {
      formData.append('images', file)
    })

    // Append hashes if provided
    if (hashes && hashes.length > 0) {
      formData.append('hashes', JSON.stringify(hashes))
    }

    return apiClient.post<UploadResponse>('/upload', formData, {
      timeout: 120000, // 2 minutes for large uploads
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(progress)
        }
      },
    })
  },
}

/**
 * Images API
 */
export const imageApi = {
  getImages: (params?: {
    page?: number
    page_size?: number
    search?: string
    date_from?: string
    date_to?: string
  }) => api.get<PaginatedResponse<Image>>('/images', { params }),

  getImage: (id: string) => api.get<Image>(`/images/${id}`),

  updateImage: (
    id: string,
    data: {
      title?: string
      description?: string
    }
  ) => api.patch<Image>(`/images/${id}`, data),

  deleteImage: (id: string) => api.delete(`/images/${id}`),

  batchDelete: (imageIds: string[]) =>
    api.post<BatchDeleteResponse>('/images/batch/delete', { image_ids: imageIds }),
}

/**
 * Batch AI Analyze API
 */
export const batchAnalyzeApi = {
  batchAnalyze: (imageIds: string[], forceNew?: boolean) =>
    api.post<BatchAnalyzeResponse>(
      '/ai/analyze/batch',
      {
        image_ids: imageIds,
        force_new: forceNew ?? false,
      },
      {
        timeout: BATCH_ANALYZE_TIMEOUT_MS,
      }
    ),
}
