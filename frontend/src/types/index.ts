/**
 * TypeScript type definitions for the application
 */

/**
 * Image types
 */
export interface Image {
  id: string;
  title: string;
  description?: string;
  file_path: string;
  file_size: number;
  width?: number;
  height?: number;
  mime_type: string;
  hash_sha256?: string | null;
  average_rating: number;
  rating_count: number;
  created_at: string;
  updated_at: string;
  ai_score?: number | null;
  ai_model?: string | null;
  ai_analyzed_at?: string | null;
  ai_decision?: string | null;
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
