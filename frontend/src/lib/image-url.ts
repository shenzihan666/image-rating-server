/**
 * Image URL helper utilities
 */

/**
 * Get the full URL for an uploaded image file.
 *
 * @param filePath - Relative file path (e.g., "2025/03/06/uuid.jpg")
 * @returns Full URL to the image
 */
export function getImageUrl(filePath: string): string {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
  return `${apiUrl}/uploads/${filePath}`;
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
