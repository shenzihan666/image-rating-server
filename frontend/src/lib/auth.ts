/**
 * Authentication utilities for token management
 */

const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";

/**
 * Get access token from localStorage
 */
export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

/**
 * Get refresh token from localStorage
 */
export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

/**
 * Set tokens in localStorage
 */
export function setTokens(accessToken: string, refreshToken: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

/**
 * Remove tokens from localStorage
 */
export function removeTokens(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  return !!getAccessToken();
}

/**
 * Decode JWT token (without verification - for getting user info only)
 */
export function decodeToken(token: string): Record<string, unknown> | null {
  try {
    const base64Url = token.split(".")[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = atob(base64);
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

/**
 * Get user info from access token
 */
export function getUserFromToken(): {
  user_id: string;
  email?: string;
  is_active?: boolean;
} | null {
  const token = getAccessToken();
  if (!token) return null;

  const decoded = decodeToken(token);
  if (!decoded) return null;

  return {
    user_id: decoded.sub as string,
    email: decoded.email as string | undefined,
    is_active: decoded.is_active as boolean | undefined,
  };
}
