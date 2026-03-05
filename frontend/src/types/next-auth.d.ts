/* eslint-disable no-unused-vars */
/**
 * NextAuth.js Type Declarations
 * Extends the default session and user types
 */
import type { DefaultSession } from "next-auth";

declare module "next-auth" {
  interface Session {
    accessToken: string;
    refreshToken: string;
    user: {
      id: string;
    } & DefaultSession["user"];
  }

  interface User {
    accessToken: string;
    refreshToken: string;
    expiresIn: number;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken: string;
    refreshToken: string;
    expiresIn: number;
    accessTokenExpires: number;
    id: string;
  }
}
