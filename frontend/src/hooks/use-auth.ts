"use client";

/**
 * Custom hook for authentication state management
 */
import { useCallback, useEffect, useMemo } from "react";

import { getUserFromToken, isAuthenticated, removeTokens } from "@/lib/auth";
import { useAuthStore } from "@/store/auth-store";
import { authApi } from "@/lib/api";

export function useAuth() {
  const { user, setUser, setLoading, logout: storeLogout } = useAuthStore();

  // Initialize auth state on mount
  useEffect(() => {
    const initAuth = async () => {
      setLoading(true);

      if (isAuthenticated()) {
        try {
          // Try to fetch current user data
          const response = await authApi.getMe();
          setUser(response.data);
        } catch {
          // If request fails, try to get from token
          const tokenUser = getUserFromToken();
          if (tokenUser) {
            setUser({
              user_id: tokenUser.user_id,
              email: tokenUser.email || "",
              full_name: "User",
              is_active: tokenUser.is_active ?? true,
            });
          } else {
            // Invalid token, clear it
            removeTokens();
            storeLogout();
          }
        }
      }

      setLoading(false);
    };

    initAuth();
  }, [setUser, setLoading, storeLogout]);

  const logout = useCallback(() => {
    removeTokens();
    storeLogout();
    authApi.logout().catch(console.error);
  }, [storeLogout]);

  const isAuthenticatedUser = useMemo(() => !!user, [user]);

  return {
    user,
    isAuthenticated: isAuthenticatedUser,
    logout,
  };
}
