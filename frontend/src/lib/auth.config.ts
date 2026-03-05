/**
 * NextAuth.js Configuration
 * Base configuration for authentication
 */
import type { NextAuthConfig } from "next-auth";
import Credentials from "next-auth/providers/credentials";

// API base URL from environment variable
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export const authConfig: NextAuthConfig = {
  secret: process.env.AUTH_SECRET || process.env.NEXTAUTH_SECRET,
  providers: [
    Credentials({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      authorize: async (credentials) => {
        try {
          const response = await fetch(`${API_URL}/api/v1/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email: credentials?.email,
              password: credentials?.password,
            }),
          });

          if (!response.ok) {
            return null;
          }

          const data = await response.json();

          // Get user info from the /auth/me endpoint
          const userResponse = await fetch(`${API_URL}/api/v1/auth/me`, {
            method: "GET",
            headers: {
              Authorization: `Bearer ${data.access_token}`,
            },
          });

          let userData = null;
          if (userResponse.ok) {
            userData = await userResponse.json();
          }

          return {
            id: userData?.user_id || data.user_id || "unknown",
            email: credentials?.email as string,
            name: userData?.full_name || "User",
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
            expiresIn: data.expires_in,
          };
        } catch (error) {
          console.error("Auth error:", error);
          return null;
        }
      },
    }),
  ],
  pages: {
    signIn: "/login",
    error: "/login",
  },
  callbacks: {
    authorized({ auth, request: { nextUrl } }) {
      const isLoggedIn = !!auth?.user;
      const isOnDashboard = nextUrl.pathname.startsWith("/dashboard");
      const isOnLogin = nextUrl.pathname === "/login";

      if (isOnDashboard) {
        if (isLoggedIn) return true;
        return false; // Redirect unauthenticated users to login page
      }

      if (isOnLogin && isLoggedIn) {
        return Response.redirect(new URL("/dashboard", nextUrl));
      }

      return true;
    },
    jwt: async ({ token, user, trigger, session }) => {
      // Initial sign in - user contains the data returned from authorize
      if (user) {
        token.accessToken = user.accessToken;
        token.refreshToken = user.refreshToken;
        token.expiresIn = user.expiresIn;
        token.id = user.id;
        token.email = user.email;
        token.name = user.name;
        // Set token expiration based on backend's expires_in (convert to milliseconds)
        token.accessTokenExpires = Date.now() + (user.expiresIn || 3600) * 1000;
      }

      // Handle session update (e.g., when user updates profile)
      if (trigger === "update" && session) {
        token.name = session.name;
        token.email = session.email;
      }

      // Check if access token is expired
      if (token.accessTokenExpires && Date.now() > (token.accessTokenExpires as number)) {
        // Try to refresh the token
        try {
          const response = await fetch(`${API_URL}/api/v1/auth/refresh`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              refresh_token: token.refreshToken,
            }),
          });

          if (response.ok) {
            const data = await response.json();
            token.accessToken = data.access_token;
            token.refreshToken = data.refresh_token;
            token.expiresIn = data.expires_in;
            token.accessTokenExpires = Date.now() + data.expires_in * 1000;
          } else {
            // Refresh failed, return null to sign out
            return null;
          }
        } catch (error) {
          console.error("Token refresh error:", error);
          return null;
        }
      }

      return token;
    },
    session: async ({ session, token }) => {
      // Pass tokens and user info to the client session
      if (token) {
        session.accessToken = token.accessToken as string;
        session.refreshToken = token.refreshToken as string;
        session.user = {
          ...session.user,
          id: token.id as string,
          email: token.email as string,
          name: token.name as string,
        };
      }
      return session;
    },
  },
  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  debug: process.env.NODE_ENV === "development",
};
