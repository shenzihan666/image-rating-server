"use client";

import { useEffect } from "react";
import { useSession } from "next-auth/react";

import { setTokenGetter } from "@/lib/api";

/**
 * Component that initializes the API client with the session token
 * This should be rendered inside SessionProvider
 */
export function ApiInitializer() {
  const { data: session } = useSession();

  useEffect(() => {
    // Set up the token getter function
    setTokenGetter(async () => {
      return session?.accessToken || null;
    });
  }, [session?.accessToken]);

  return null;
}
