/**
 * TypeScript type definitions for the application
 */

/**
 * User types
 */
export interface User {
  user_id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at?: string;
}

export interface UserCreate {
  email: string;
  password: string;
  full_name: string;
}

export interface UserUpdate {
  full_name?: string;
  email?: string;
}

/**
 * Auth types
 */
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

/**
 * Image types
 */
export interface Image {
  id: string;
  user_id: string;
  title: string;
  description?: string;
  file_path: string;
  file_size: number;
  width?: number;
  height?: number;
  mime_type: string;
  average_rating: number;
  rating_count: number;
  created_at: string;
  updated_at: string;
  ai_score?: number | null;
  ai_model?: string | null;
  ai_analyzed_at?: string | null;
}

/**
 * Rating types
 */
export interface Rating {
  id: string;
  user_id: string;
  image_id: string;
  score: number;
  comment?: string;
  created_at: string;
}

/**
 * API Response types
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

/**
 * Form types
 */
export interface FormErrors {
  [key: string]: string[] | string | undefined;
}

/**
 * App context types
 */
export interface AppState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

/**
 * Upload types
 */
export type UploadStatus = "success" | "duplicated" | "failed";

export interface ImageMetadata {
  image_id: string;
  file_name: string;
  file_size: number;
  mime_type: string;
  width?: number;
  height?: number;
  file_path: string;
  hash_sha256: string;
}

export interface UploadResult {
  status: UploadStatus;
  original_filename: string;
  metadata?: ImageMetadata;
  error_message?: string;
  is_duplicate: boolean;
}

export interface UploadResponse {
  success: boolean;
  total: number;
  succeeded: number;
  duplicated: number;
  failed: number;
  results: UploadResult[];
  message: string;
}

export type UploadItemStatus = "pending" | "uploading" | "success" | "duplicated" | "failed";

export interface UploadListItem {
  id: string;
  file?: File;
  file_name: string;
  file_size: number;
  file_type: string;
  preview?: string;
  status: UploadItemStatus;
  progress: number;
  result?: UploadResult;
  created_at: string;
  updated_at: string;
}

/**
 * Batch operation types
 */
export interface ImageAnalyzeResponse {
  image_id: string;
  model: string;
  score: number | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface BatchAnalyzeResponse {
  success: boolean;
  total: number;
  succeeded: number;
  failed: number;
  results: ImageAnalyzeResponse[];
  message: string;
}

export interface BatchDeleteResponse {
  success: boolean;
  total: number;
  deleted: number;
  failed: number;
  errors: string[];
  message: string;
}

