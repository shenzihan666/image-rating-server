"use client";

import { motion } from "framer-motion";
import { Image, Star } from "lucide-react";

// Mock data
const mockStats = [
  { label: "Total Images", value: "1,284", icon: Image, change: "+12%" },
  { label: "Your Ratings", value: "456", icon: Star, change: "+8%" },
];

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl lg:text-3xl font-bold text-[#333333]">
          Dashboard
        </h1>
        <p className="text-[#333333]/60 mt-1">
          Welcome back! Here&apos;s what&apos;s happening with your images.
        </p>
      </div>

      {/* Stats Grid */}
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="grid grid-cols-2 gap-4 lg:gap-6"
      >
        {mockStats.map((stat) => (
          <motion.div
            key={stat.label}
            variants={item}
            className="glass-card rounded-2xl p-5 lg:p-6 card-hover"
          >
            <div className="flex items-start justify-between">
              <div className="w-10 h-10 lg:w-12 lg:h-12 rounded-xl bg-[#F5F5F5] flex items-center justify-center">
                <stat.icon className="w-5 h-5 lg:w-6 lg:h-6 text-[#333333]" />
              </div>
              <span className="text-xs font-medium text-green-600 bg-green-50 px-2 py-1 rounded-full">
                {stat.change}
              </span>
            </div>
            <div className="mt-4">
              <div className="text-2xl lg:text-3xl font-bold text-[#333333]">
                {stat.value}
              </div>
              <div className="text-sm text-[#333333]/60 mt-1">{stat.label}</div>
            </div>
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
}
