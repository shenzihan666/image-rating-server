"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Eye, EyeOff, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authApi } from "@/lib/api";
import { setTokens } from "@/lib/auth";
import { useAuthStore } from "@/store/auth-store";
import { toast } from "@/hooks/use-toast";

export default function LoginPage() {
  const router = useRouter();
  const { setUser } = useAuthStore();
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("password123");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const response = await authApi.login(email, password);
      const { access_token, refresh_token } = response.data;

      setTokens(access_token, refresh_token);

      const userResponse = await authApi.getMe();
      setUser(userResponse.data);

      toast({
        title: "Welcome back!",
        description: "You have successfully logged in.",
      });

      router.push("/dashboard");
    } catch (err: unknown) {
      const apiError = err as { detail?: string };
      setError(apiError.detail || "Login failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F5F5F5] bg-gradient-radial p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <div className="glass-card rounded-2xl p-8">
          <div className="mb-8">
            <h2 className="text-2xl font-semibold text-[#333333] mb-2">
              Sign in
            </h2>
            <p className="text-[#333333]/60">
              Enter your credentials to continue
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-[#333333] font-medium">
                Email
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={isLoading}
                className="h-12 bg-[#F5F5F5] border-0 rounded-xl placeholder:text-[#333333]/40 focus:ring-2 focus:ring-[#333333]/20"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-[#333333] font-medium">
                Password
              </Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={isLoading}
                  className="h-12 bg-[#F5F5F5] border-0 rounded-xl placeholder:text-[#333333]/40 focus:ring-2 focus:ring-[#333333]/20 pr-12"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-[#333333]/40 hover:text-[#333333] transition-colors cursor-pointer"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            {error && (
              <div className="p-3 rounded-xl bg-red-50 text-red-600 text-sm">
                {error}
              </div>
            )}

            <Button
              type="submit"
              disabled={isLoading}
              className="w-full h-12 bg-[#333333] hover:bg-[#000000] text-white rounded-xl font-medium transition-colors"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Signing in...
                </>
              ) : (
                "Sign in"
              )}
            </Button>
          </form>

          <div className="mt-6 p-4 rounded-xl bg-[#F5F5F5]">
            <p className="text-sm text-[#333333]/60 text-center">
              <span className="font-medium text-[#333333]">Demo:</span>{" "}
              demo@example.com / password123
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
