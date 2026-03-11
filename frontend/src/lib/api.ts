/**
 * API Client for communicating with the FastAPI backend
 * Updated to work with NextAuth.js session
 */
import type { AxiosError, AxiosRequestConfig, AxiosResponse } from 'axios'
import axios, { AxiosInstance } from 'axios'

import type {
  UploadResponse,
  TokenResponse,
  User,
  Image,
  PaginatedResponse,
  BatchAnalyzeResponse,
  BatchDeleteResponse,
} from '@/types'

// API base URL from environment variable
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'
const BATCH_ANALYZE_TIMEOUT_MS = 5 * 60 * 1000

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

// Token getter function type
let tokenGetter: (() => Promise<string | null>) | null = null
let pendingSessionToken: Promise<string | null> | null = null

async function getSessionAccessToken(): Promise<string | null> {
  if (typeof window === 'undefined') {
    return null
  }

  if (!pendingSessionToken) {
    pendingSessionToken = import('next-auth/react')
      .then(async ({ getSession }) => {
        const session = await getSession()
        return session?.accessToken ?? null
      })
      .finally(() => {
        pendingSessionToken = null
      })
  }

  return pendingSessionToken
}

async function resolveAccessToken(): Promise<string | null> {
  const token = tokenGetter ? await tokenGetter() : null
  if (token) {
    return token
  }

  return getSessionAccessToken()
}

/**
 * Set the token getter function (called from SessionProvider context)
 */
export function setTokenGetter(getter: () => Promise<string | null>): void {
  tokenGetter = getter
}

/**
 * Create axios instance with default configuration
 */
const createApiClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: `${API_URL}/api/v1`,
    timeout: 30000,
  })

  // Request interceptor - Add auth token
  client.interceptors.request.use(
    async (config) => {
      // Let browser/axios set multipart boundaries automatically for FormData.
      if (typeof FormData !== 'undefined' && config.data instanceof FormData && config.headers) {
        if (
          typeof (config.headers as { set?: (name: string, value?: string) => void }).set ===
          'function'
        ) {
          ;(config.headers as { set: (name: string, value?: string) => void }).set(
            'Content-Type',
            undefined
          )
        } else {
          delete (config.headers as Record<string, string>)['Content-Type']
        }
      }

      const token = await resolveAccessToken()
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    },
    (error) => Promise.reject(error)
  )

  // Response interceptor - Handle errors
  client.interceptors.response.use(
    (response) => response,
    async (error: AxiosError<ApiError>) => {
      // Handle 401 Unauthorized
      if (error.response?.status === 401) {
        // NextAuth will handle token refresh, so if we get 401,
        // the session might be invalid. Force sign out.
        if (typeof window !== 'undefined') {
          // Import signOut dynamically to avoid circular dependencies
          const { signOut } = await import('next-auth/react')
          await signOut({ callbackUrl: '/login' })
        }
      }

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
 * Authentication API
 * Note: Login is handled by NextAuth, these are for internal use
 */
export const authApi = {
  // Login is handled by NextAuth credentials provider
  // This method is kept for potential direct use but should not be used normally
  login: (email: string, password: string) =>
    api.post<TokenResponse>('/auth/login', { email, password }),

  // Register endpoint is removed from backend
  register: undefined,

  logout: () => api.post('/auth/logout'),

  refreshToken: (refreshToken: string) =>
    api.post<TokenResponse>('/auth/refresh', { refresh_token: refreshToken }),

  getMe: () => api.get<User>('/auth/me'),
}

/**
 * User API
 */
export const userApi = {
  getProfile: () => api.get('/users/me'),

  updateProfile: (data: { full_name?: string; email?: string }) => api.patch('/users/me', data),

  changePassword: (oldPassword: string, newPassword: string) =>
    api.post('/users/me/change-password', {
      old_password: oldPassword,
      new_password: newPassword,
    }),

  listUsers: (page: number = 1, pageSize: number = 20) =>
    api.get('/users/', { params: { page, page_size: pageSize } }),

  getUser: (userId: string) => api.get(`/users/${userId}`),
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
export type UploadProgressCallback = (progress: number) => void

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
