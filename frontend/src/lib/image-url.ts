/**
 * Image URL helper utilities
 */

/**
 * Public path for an uploaded image (same-origin; Next rewrites `/uploads/*` to the API).
 *
 * @param filePath - Relative file path (e.g., "2025/03/06/uuid.jpg")
 */
export function getImageUrl(filePath: string): string {
  return `/uploads/${filePath}`;
}

/**
 * Get a thumbnail URL for an image (currently returns the same URL).
 * In the future, this could generate thumbnails on the backend.
 *
 * @param filePath - Relative file path
 * @returns Full URL to the thumbnail
 */
export function getThumbnailUrl(filePath: string): string {
  // Currently returns the same URL - thumbnails could be implemented later
  return getImageUrl(filePath);
}
