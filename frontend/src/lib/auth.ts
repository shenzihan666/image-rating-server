/**
 * NextAuth.js - Main export
 * This file exports the NextAuth handlers and utilities
 */
import NextAuth from "next-auth";

import { authConfig } from "./auth.config";

export const { handlers, signIn, signOut, auth } = NextAuth(authConfig);
