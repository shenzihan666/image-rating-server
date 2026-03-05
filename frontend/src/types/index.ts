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
