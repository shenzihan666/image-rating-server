/**
 * Logout button component
 */
"use client";

import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";
import { removeTokens } from "@/lib/auth";
import { useAuthStore } from "@/store/auth-store";

export function LogoutButton({ variant = "ghost" }: { variant?: "ghost" | "outline" | "default" }) {
  const router = useRouter();
  const { logout } = useAuthStore();

  const handleLogout = () => {
    removeTokens();
    logout();
    router.push("/login");
  };

  return (
    <Button variant={variant} onClick={handleLogout}>
      Logout
    </Button>
  );
}
