"use client";

import NextImage from "next/image";
import { motion } from "framer-motion";
import { Check, Sparkles } from "lucide-react";

import { getImageUrl } from "@/lib/image-url";
import { cn, formatRelativeTime, formatFileSize } from "@/lib/utils";
import type { Image } from "@/types";

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },
  },
};

const item = {
  hidden: { opacity: 0, x: -20 },
  show: { opacity: 1, x: 0 },
};

export interface ImagesTableViewProps {
  images: Image[];
  selectedIds: Set<string>;
  selectionMode: boolean;
  onSelectImage: (_id: string) => void;
  onOpenDetail: (_id: string) => void;
}

export function ImagesTableView({
  images,
  selectedIds,
  selectionMode,
  onSelectImage,
  onOpenDetail,
}: ImagesTableViewProps) {
  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="space-y-3"
    >
      {images.map((image) => (
        <motion.div
          key={image.id}
          variants={item}
          whileHover={{ x: 4 }}
          className={cn(
            "glass-card rounded-2xl overflow-hidden cursor-pointer card-hover transition-all",
            selectedIds.has(image.id) && "ring-2 ring-purple-600 ring-offset-2"
          )}
        >
          <div className="flex items-center gap-4 p-3">
            {selectionMode && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectImage(image.id);
                }}
                className={cn(
                  "w-6 h-6 rounded-lg border-2 flex items-center justify-center transition-colors flex-shrink-0 cursor-pointer",
                  selectedIds.has(image.id)
                    ? "bg-purple-600 border-purple-600"
                    : "border-[#333333]/30 hover:border-purple-600"
                )}
              >
                {selectedIds.has(image.id) && (
                  <Check className="w-4 h-4 text-white" />
                )}
              </button>
            )}

            <div
              className="relative w-20 h-20 sm:w-24 sm:h-24 flex-shrink-0 bg-[#E0E0E0] rounded-xl overflow-hidden"
              onClick={() =>
                selectionMode ? onSelectImage(image.id) : onOpenDetail(image.id)
              }
            >
              <NextImage
                src={getImageUrl(image.file_path)}
                alt={image.title}
                fill
                className="object-cover"
                sizes="96px"
              />
            </div>

            <div
              className="flex-1 min-w-0"
              onClick={() =>
                selectionMode ? onSelectImage(image.id) : onOpenDetail(image.id)
              }
            >
              <h3 className="font-medium text-[#333333] truncate">
                {image.title}
              </h3>
              <div className="flex flex-wrap items-center gap-3 mt-1.5 text-sm text-[#333333]/50">
                {image.width && image.height && (
                  <span className="flex items-center gap-1">
                    <span className="w-3 h-3 rounded-sm bg-[#333333]/10" />
                    {image.width} × {image.height}
                  </span>
                )}
                <span className="flex items-center gap-1">
                  <span className="text-xs">📦</span>
                  {formatFileSize(image.file_size)}
                </span>
                <span className="flex items-center gap-1">
                  <span className="text-xs">📅</span>
                  {formatRelativeTime(image.created_at)}
                </span>
                {image.ai_score != null && (
                  <span className="flex items-center gap-1 text-purple-600">
                    <Sparkles className="w-3 h-3" />
                    {image.ai_score.toFixed(2)}
                  </span>
                )}
                {image.ai_decision && (
                  <span
                    className={cn(
                      "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                      image.ai_decision === "合格"
                        ? "bg-green-100 text-green-700"
                        : "bg-red-100 text-red-700"
                    )}
                  >
                    {image.ai_decision}
                  </span>
                )}
                {image.rating_count > 0 && image.ai_score == null && (
                  <span className="flex items-center gap-1 text-amber-600">
                    <span>★</span>
                    {image.average_rating.toFixed(1)}
                  </span>
                )}
              </div>
            </div>

            {!selectionMode && (
              <div
                className="text-[#333333]/30 cursor-pointer"
                onClick={() => onOpenDetail(image.id)}
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              </div>
            )}
          </div>
        </motion.div>
      ))}
    </motion.div>
  );
}
