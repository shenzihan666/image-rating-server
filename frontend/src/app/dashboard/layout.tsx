"use client";

import { useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard,
  Upload,
  Settings,
  ChevronLeft,
  ChevronRight,
  Menu,
  X,
  Bot,
  Image as ImageIcon,
  MessageSquareText,
} from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/upload", label: "Upload", icon: Upload },
  { href: "/dashboard/images", label: "Images", icon: ImageIcon },
  { href: "/dashboard/ai-analyze", label: "AI Analyze Server", icon: Bot },
  {
    href: "/dashboard/ai-analyze/qwen3-vl/prompts",
    label: "Qwen Prompts",
    icon: MessageSquareText,
  },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  const isNavItemActive = (href: string) => {
    if (href === "/dashboard") {
      return pathname === href;
    }

    if (href === "/dashboard/ai-analyze") {
      return (
        pathname.startsWith("/dashboard/ai-analyze") &&
        !pathname.startsWith("/dashboard/ai-analyze/qwen3-vl/prompts")
      );
    }

    return pathname === href || pathname.startsWith(`${href}/`);
  };

  return (
    <div className="min-h-screen bg-[#F5F5F5] bg-gradient-radial">
      {/* Mobile Header */}
      <header className="lg:hidden fixed top-0 left-0 right-0 h-16 glass-card z-50 flex items-center justify-between px-4">
        <button
          onClick={() => setIsMobileOpen(true)}
          className="p-2 hover:bg-[#E0E0E0] rounded-lg transition-colors cursor-pointer"
        >
          <Menu className="w-5 h-5 text-[#333333]" />
        </button>

        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-[#333333] rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">IR</span>
          </div>
          <span className="font-semibold text-[#333333]">Image Rating</span>
        </div>

        <div className="w-9" />
      </header>

      {/* Mobile Sidebar Overlay */}
      <AnimatePresence>
        {isMobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsMobileOpen(false)}
              className="lg:hidden fixed inset-0 bg-black/20 z-50"
            />
            <motion.aside
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="lg:hidden fixed left-0 top-0 bottom-0 w-[280px] glass-sidebar z-50"
            >
              <div className="flex items-center justify-between p-6 border-b border-[#E0E0E0]">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-[#333333] rounded-xl flex items-center justify-center">
                    <span className="text-white font-bold">IR</span>
                  </div>
                  <span className="font-semibold text-[#333333]">Image Rating</span>
                </div>
                <button
                  onClick={() => setIsMobileOpen(false)}
                  className="p-2 hover:bg-[#E0E0E0] rounded-lg transition-colors cursor-pointer"
                >
                  <X className="w-5 h-5 text-[#333333]" />
                </button>
              </div>

              <nav className="p-4 space-y-1">
                {navItems.map((item) => {
                  const isActive = isNavItemActive(item.href);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => setIsMobileOpen(false)}
                      className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all cursor-pointer ${
                        isActive
                          ? "bg-[#333333] text-white"
                          : "text-[#333333]/70 hover:bg-[#E0E0E0] hover:text-[#333333]"
                      }`}
                    >
                      <item.icon className="w-5 h-5" />
                      <span className="font-medium">{item.label}</span>
                    </Link>
                  );
                })}
              </nav>
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Desktop Sidebar */}
      <aside
        className={`hidden lg:block fixed left-0 top-0 bottom-0 glass-sidebar z-40 transition-all duration-300 ${
          isCollapsed ? "w-20" : "w-[280px]"
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center justify-between p-6 border-b border-[#E0E0E0]">
            <AnimatePresence mode="wait">
              {!isCollapsed && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex items-center gap-3"
                >
                  <div className="w-10 h-10 bg-[#333333] rounded-xl flex items-center justify-center">
                    <span className="text-white font-bold">IR</span>
                  </div>
                  <span className="font-semibold text-[#333333]">Image Rating</span>
                </motion.div>
              )}
            </AnimatePresence>

            {isCollapsed && (
              <div className="w-10 h-10 bg-[#333333] rounded-xl flex items-center justify-center mx-auto">
                <span className="text-white font-bold">IR</span>
              </div>
            )}
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
            {navItems.map((item) => {
              const isActive = isNavItemActive(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all cursor-pointer ${
                    isCollapsed ? "justify-center" : ""
                  } ${
                    isActive
                      ? "bg-[#333333] text-white"
                      : "text-[#333333]/70 hover:bg-[#E0E0E0] hover:text-[#333333]"
                  }`}
                  title={isCollapsed ? item.label : undefined}
                >
                  <item.icon className="w-5 h-5 flex-shrink-0" />
                  <AnimatePresence mode="wait">
                    {!isCollapsed && (
                      <motion.span
                        initial={{ opacity: 0, width: 0 }}
                        animate={{ opacity: 1, width: "auto" }}
                        exit={{ opacity: 0, width: 0 }}
                        className="font-medium whitespace-nowrap overflow-hidden"
                      >
                        {item.label}
                      </motion.span>
                    )}
                  </AnimatePresence>
                </Link>
              );
            })}

            {!isCollapsed && (
              <div className="pt-4 mt-4 border-t border-[#E0E0E0]" />
            )}
          </nav>

          {/* Bottom Section */}
          <div className="p-4 border-t border-[#E0E0E0]">
            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className={`flex items-center gap-3 px-4 py-3 w-full rounded-xl text-[#333333]/70 hover:bg-[#E0E0E0] hover:text-[#333333] transition-all cursor-pointer ${
                isCollapsed ? "justify-center" : ""
              }`}
            >
              {isCollapsed ? (
                <ChevronRight className="w-5 h-5" />
              ) : (
                <>
                  <ChevronLeft className="w-5 h-5" />
                  <span className="font-medium">Collapse</span>
                </>
              )}
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main
        className={`transition-all duration-300 pt-16 lg:pt-0 min-h-screen ${
          isCollapsed ? "lg:pl-20" : "lg:pl-[280px]"
        }`}
      >
        <div className="p-6 lg:p-8">
          {children}
        </div>
      </main>
    </div>
  );
}
