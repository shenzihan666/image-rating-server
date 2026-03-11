"use client";

import { motion } from "framer-motion";
import { Check, Sparkles } from "lucide-react";

import { getImageUrl } from "@/lib/image-url";
import { cn, formatRelativeTime, formatFileSize } from "@/lib/utils";
import type { Image } from "@/types";

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.04 },
  },
};

const item = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0 },
};

export interface ImagesCardViewProps {
  images: Image[];
  selectedIds: Set<string>;
  selectionMode: boolean;
  onSelectImage: (_id: string) => void;
  onOpenDetail: (_id: string) => void;
}

export function ImagesCardView({
  images,
  selectedIds,
  selectionMode,
  onSelectImage,
  onOpenDetail,
}: ImagesCardViewProps) {
  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
    >
      {images.map((image) => (
        <motion.div
          key={image.id}
          variants={item}
          className={cn(
            "glass-card rounded-2xl border border-[#E0E0E0] overflow-hidden p-0 shadow-sm cursor-pointer card-hover transition-all",
            selectedIds.has(image.id) && "ring-2 ring-purple-600 ring-offset-2"
          )}
          onClick={() =>
            selectionMode ? onSelectImage(image.id) : onOpenDetail(image.id)
          }
        >
          <div className="flex flex-col">
            <div className="relative aspect-square w-full bg-[#E0E0E0]">
              <img
                src={getImageUrl(image.file_path)}
                alt={image.title}
                className="h-full w-full object-cover"
                loading="lazy"
              />
              {selectionMode && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectImage(image.id);
                  }}
                  className={cn(
                    "absolute left-2 top-2 w-6 h-6 rounded-lg border-2 flex items-center justify-center transition-colors cursor-pointer bg-white/90",
                    selectedIds.has(image.id)
                      ? "bg-purple-600 border-purple-600"
                      : "border-[#333333]/40 hover:border-purple-600"
                  )}
                >
                  {selectedIds.has(image.id) && (
                    <Check className="w-4 h-4 text-white" />
                  )}
                </button>
              )}
            </div>
            <div className="flex flex-col gap-2 p-4">
              <h3 className="font-semibold text-[#333333] truncate">
                {image.title}
              </h3>
              <div className="grid gap-2 rounded-xl bg-white/70 px-3 py-2 text-sm text-[#333333]/65">
                {image.width && image.height && (
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-sm bg-[#333333]/10" />
                    {image.width} × {image.height}
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <span className="text-xs">📦</span>
                  {formatFileSize(image.file_size)}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs">📅</span>
                  {formatRelativeTime(image.created_at)}
                </div>
                {image.ai_score != null && (
                  <div className="flex items-center gap-2 text-purple-600">
                    <Sparkles className="w-3 h-3" />
                    {image.ai_score.toFixed(2)}
                    {image.ai_decision && (
                      <span
                        className={cn(
                          "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ml-1",
                          image.ai_decision === "合格"
                            ? "bg-green-100 text-green-700"
                            : "bg-red-100 text-red-700"
                        )}
                      >
                        {image.ai_decision}
                      </span>
                    )}
                  </div>
                )}
                {image.rating_count > 0 && image.ai_score == null && (
                  <div className="flex items-center gap-2 text-amber-600">
                    <span>★</span>
                    {image.average_rating.toFixed(1)}
                  </div>
                )}
              </div>
              {!selectionMode && (
                <span className="text-xs text-[#333333]/50">
                  Click to open details
                </span>
              )}
            </div>
          </div>
        </motion.div>
      ))}
    </motion.div>
  );
}
