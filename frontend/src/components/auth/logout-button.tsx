/**
 * Logout button component using NextAuth
 */
"use client";

import { signOut } from "next-auth/react";
import { Button } from "@/components/ui/button";

export function LogoutButton({ variant = "ghost" }: { variant?: "ghost" | "outline" | "default" }) {
  const handleLogout = () => {
    signOut({ callbackUrl: "/login" });
  };

  return (
    <Button variant={variant} onClick={handleLogout}>
      Logout
    </Button>
  );
}
