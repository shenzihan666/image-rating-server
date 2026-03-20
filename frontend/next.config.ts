import type { NextConfig } from "next";

const rawAllowedDevOrigins = process.env.NEXT_ALLOWED_DEV_ORIGINS;
const allowedDevOrigins = rawAllowedDevOrigins
  ? rawAllowedDevOrigins.split(",").map((host) => host.trim()).filter(Boolean)
  : [];

/** Where the Next.js process reaches the FastAPI app (never a public browser URL). */
function backendBase(): string {
  return (
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://127.0.0.1:8080"
  ).replace(/\/$/, "");
}

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  ...(allowedDevOrigins?.length ? { allowedDevOrigins } : {}),
  async rewrites() {
    const base = backendBase();
    return [
      {
        source: "/api/v1/:path*",
        destination: `${base}/api/v1/:path*`,
      },
      {
        source: "/uploads/:path*",
        destination: `${base}/uploads/:path*`,
      },
    ];
  },
};

export default nextConfig;
