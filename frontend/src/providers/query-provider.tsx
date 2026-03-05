"use client";

/**
 * Query Provider for data fetching (React Query alternative)
 * Using a simple implementation without React Query for now
 */
import type { ReactNode } from "react";

interface QueryProviderProps {
  children: ReactNode;
}

export function QueryProvider({ children }: QueryProviderProps) {
  // For now, this is a placeholder
  // You can add React Query or SWR here later
  return <>{children}</>;
}
