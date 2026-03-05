/**
 * NextAuth.js Middleware
 * Protects routes and handles authentication redirects
 */
import { auth } from "@/lib/auth";

export default auth;

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
