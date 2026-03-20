import type { NextConfig } from "next";

const rawAllowedDevOrigins = process.env.NEXT_ALLOWED_DEV_ORIGINS;
const allowedDevOrigins = rawAllowedDevOrigins
  ? rawAllowedDevOrigins.split(",").map((host) => host.trim()).filter(Boolean)
  : [];

type UploadsRemotePattern = {
  protocol: "http" | "https";
  hostname: string;
  port?: string;
  pathname: string;
};

function uploadsRemotePatterns(): UploadsRemotePattern[] {
  const raw = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
  try {
    const u = new URL(raw);
    const protocol = u.protocol === "https:" ? "https" : "http";
    const pattern: UploadsRemotePattern = {
      protocol,
      hostname: u.hostname,
      pathname: "/uploads/**",
    };
    if (u.port) {
      pattern.port = u.port;
    }
    return [pattern];
  } catch {
    return [
      {
        protocol: "http",
        hostname: "localhost",
        port: "8080",
        pathname: "/uploads/**",
      },
    ];
  }
}

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  images: {
    remotePatterns: uploadsRemotePatterns(),
  },
  ...(allowedDevOrigins?.length ? { allowedDevOrigins } : {}),
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080",
  },
  async rewrites() {
    return [
      {
        // Only proxy backend v1 API routes, preserve NextAuth /api/auth/* routes
        source: "/api/v1/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080"}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
