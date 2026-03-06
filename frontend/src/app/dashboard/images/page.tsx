"use client";

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Search,
  Image as ImageIcon,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Trash2,
  X,
  Check,
  Calendar,
  ChevronDown,
  CheckSquare,
  Square,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { imageApi, batchAnalyzeApi, type ApiError } from "@/lib/api";
import { getImageUrl } from "@/lib/image-url";
import { cn, formatRelativeTime, formatFileSize } from "@/lib/utils";
import type { Image, BatchAnalyzeResponse, BatchDeleteResponse } from "@/types";

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

interface ImagesResponse {
  items: Image[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export default function ImagesPage() {
  const router = useRouter();
  const [images, setImages] = useState<Image[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [totalPages, setTotalPages] = useState(0);
  const [total, setTotal] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchInput, setSearchInput] = useState("");

  // Selection mode state
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [selectAll, setSelectAll] = useState(false);

  // Batch operation state
  const [batchAnalyzing, setBatchAnalyzing] = useState(false);
  const [batchDeleting, setBatchDeleting] = useState(false);

  // Date filter state
  const [showDateFilter, setShowDateFilter] = useState(false);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const fetchImages = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await imageApi.getImages({
        page,
        page_size: pageSize,
        search: searchQuery || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      });
      const data = response.data as ImagesResponse;
      setImages(data.items);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.detail || "Failed to load images");
      if (apiError.status === 401) {
        return;
      }
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, searchQuery, dateFrom, dateTo]);

  useEffect(() => {
    fetchImages();
  }, [fetchImages]);

  // Reset selection when page changes
  useEffect(() => {
    setSelectedIds(new Set());
    setSelectAll(false);
  }, [page, searchQuery, dateFrom, dateTo]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchQuery(searchInput);
    setPage(1);
  };

  const handleClearSearch = () => {
    setSearchInput("");
    setSearchQuery("");
    setPage(1);
  };

  const toggleSelectionMode = () => {
    setSelectionMode(!selectionMode);
    if (selectionMode) {
      // Exiting selection mode, clear selection
      setSelectedIds(new Set());
      setSelectAll(false);
    }
  };

  const handleSelectAll = () => {
    if (selectAll) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(images.map((img) => img.id)));
    }
    setSelectAll(!selectAll);
  };

  const handleSelectImage = (imageId: string) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(imageId)) {
      newSelected.delete(imageId);
    } else {
      newSelected.add(imageId);
    }
    setSelectedIds(newSelected);
    setSelectAll(newSelected.size === images.length);
  };

  const handleClearSelection = () => {
    setSelectedIds(new Set());
    setSelectAll(false);
  };

  const handleBatchAnalyze = async () => {
    if (selectedIds.size === 0) return;

    setBatchAnalyzing(true);

    try {
      const response = await batchAnalyzeApi.batchAnalyze(
        Array.from(selectedIds),
        false
      );
      const result = response.data as BatchAnalyzeResponse;

      alert(result.message || `Analyzed ${result.succeeded} images`);

      await fetchImages();
      handleClearSelection();
    } catch (err) {
      const apiError = err as ApiError;
      alert(apiError.detail || "Failed to analyze images");
    } finally {
      setBatchAnalyzing(false);
    }
  };

  const handleBatchDelete = async () => {
    if (selectedIds.size === 0) return;

    const confirmed = window.confirm(
      `Are you sure you want to delete ${selectedIds.size} image${selectedIds.size > 1 ? "s" : ""}? This action cannot be undone.`
    );
    if (!confirmed) return;

    setBatchDeleting(true);

    try {
      const response = await imageApi.batchDelete(Array.from(selectedIds));
      const result = response.data as BatchDeleteResponse;

      alert(result.message || `Deleted ${result.deleted} images`);

      await fetchImages();
      handleClearSelection();
    } catch (err) {
      const apiError = err as ApiError;
      alert(apiError.detail || "Failed to delete images");
    } finally {
      setBatchDeleting(false);
    }
  };

  const handleApplyDateFilter = () => {
    setPage(1);
    fetchImages();
    setShowDateFilter(false);
  };

  const handleClearDateFilter = () => {
    setDateFrom("");
    setDateTo("");
    setPage(1);
    setShowDateFilter(false);
  };

  const goToPage = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setPage(newPage);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  if (loading) {
    return (
      <div className="min-h-[400px] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin mx-auto text-[#333333]" />
          <p className="mt-4 text-[#333333]/60">Loading images...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-[400px] flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-4">
            <ImageIcon className="w-8 h-8 text-red-500" />
          </div>
          <p className="text-[#333333] font-medium">{error}</p>
          <button
            onClick={fetchImages}
            className="mt-4 px-4 py-2 bg-[#333333] text-white rounded-xl hover:bg-[#333333]/90 transition-colors cursor-pointer"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <div>
            <h1 className="text-2xl lg:text-3xl font-bold text-[#333333]">
              Images
            </h1>
            <p className="text-[#333333]/60 mt-1">
              {total} {total === 1 ? "image" : "images"} uploaded
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {/* Selection Mode Toggle */}
          <button
            onClick={toggleSelectionMode}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-xl transition-colors cursor-pointer",
              selectionMode
                ? "bg-purple-600 text-white hover:bg-purple-700"
                : "bg-[#E0E0E0] text-[#333333] hover:bg-[#E0E0E0]/80"
            )}
          >
            {selectionMode ? (
              <>
                <X className="w-4 h-4" />
                <span className="hidden sm:inline">Cancel</span>
              </>
            ) : (
              <>
                <CheckSquare className="w-4 h-4" />
                <span className="hidden sm:inline">Select</span>
              </>
            )}
          </button>

          {/* Search Bar */}
          <form onSubmit={handleSearch} className="flex items-center gap-2">
            <div className="relative flex-1 sm:w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#333333]/40" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search images..."
                className="w-full pl-9 pr-8 py-2 rounded-xl border border-[#E0E0E0] bg-white focus:outline-none focus:ring-2 focus:ring-[#333333]/20 focus:border-[#333333] transition-all"
              />
              {searchInput && (
                <button
                  type="button"
                  onClick={handleClearSearch}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-[#333333]/40 hover:text-[#333333] transition-colors cursor-pointer"
                >
                  ×
                </button>
              )}
            </div>
            <button
              type="submit"
              className="px-4 py-2 bg-[#333333] text-white rounded-xl hover:bg-[#333333]/90 transition-colors cursor-pointer"
            >
              Search
            </button>
          </form>

          {/* Date Filter Toggle */}
          <div className="relative">
            <button
              onClick={() => setShowDateFilter(!showDateFilter)}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-xl transition-colors cursor-pointer",
                (dateFrom || dateTo)
                  ? "bg-purple-100 text-purple-700 hover:bg-purple-200"
                  : "bg-[#E0E0E0] text-[#333333] hover:bg-[#E0E0E0]/80"
              )}
            >
              <Calendar className="w-4 h-4" />
              <span className="hidden sm:inline">Filter</span>
              <ChevronDown className="w-4 h-4" />
            </button>

            {/* Date Filter Dropdown */}
            {showDateFilter && (
              <div className="absolute right-0 top-full mt-2 w-64 bg-white rounded-xl shadow-lg border border-[#E0E0E0] p-4 z-10">
                <h3 className="font-medium text-[#333333] mb-3">Date Range</h3>
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm text-[#333333]/60 mb-1">From</label>
                    <input
                      type="date"
                      value={dateFrom}
                      onChange={(e) => setDateFrom(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-[#E0E0E0] focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-[#333333]/60 mb-1">To</label>
                    <input
                      type="date"
                      value={dateTo}
                      onChange={(e) => setDateTo(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-[#E0E0E0] focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                    />
                  </div>
                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={handleApplyDateFilter}
                      className="flex-1 px-3 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors cursor-pointer"
                    >
                      Apply
                    </button>
                    <button
                      onClick={handleClearDateFilter}
                      className="px-3 py-2 bg-[#E0E0E0] text-[#333333] rounded-lg hover:bg-[#E0E0E0]/80 transition-colors cursor-pointer"
                    >
                      Clear
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Selection Mode Header Bar */}
      {selectionMode && (
        <motion.div
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className="glass-card rounded-2xl p-4"
        >
          <div className="flex items-center justify-between gap-4">
            {/* Select All Button */}
            <button
              onClick={handleSelectAll}
              className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-[#E0E0E0] transition-colors cursor-pointer"
            >
              <div className={cn(
                "w-5 h-5 rounded border-2 flex items-center justify-center transition-colors",
                selectAll
                  ? "bg-purple-600 border-purple-600"
                  : "border-[#333333]/30 hover:border-purple-600"
              )}>
                {selectAll && <Check className="w-3 h-3 text-white" />}
              </div>
              <span className="text-sm text-[#333333]">
                {selectAll ? "Deselect All" : "Select All"}
              </span>
            </button>

            {/* Selection Count and Actions */}
            <div className="flex items-center gap-3">
              {selectedIds.size > 0 && (
                <>
                  <span className="text-sm text-[#333333]/60">
                    {selectedIds.size} selected
                  </span>
                  <div className="h-4 w-px bg-[#E0E0E0]" />
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleBatchAnalyze}
                      disabled={batchAnalyzing || batchDeleting}
                      className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-xl hover:from-purple-700 hover:to-pink-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer text-sm"
                    >
                      {batchAnalyzing ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Analyzing...
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-4 h-4" />
                          Analyze
                        </>
                      )}
                    </button>
                    <button
                      onClick={handleBatchDelete}
                      disabled={batchAnalyzing || batchDeleting}
                      className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded-xl hover:bg-red-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer text-sm"
                    >
                      {batchDeleting ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Deleting...
                        </>
                      ) : (
                        <>
                          <Trash2 className="w-4 h-4" />
                          Delete
                        </>
                      )}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </motion.div>
      )}

      {/* Images List */}
      {images.length > 0 ? (
        <>
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
                  {/* Checkbox (always visible in selection mode) */}
                  {selectionMode && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSelectImage(image.id);
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

                  {/* Thumbnail */}
                  <div
                    className="w-20 h-20 sm:w-24 sm:h-24 flex-shrink-0 bg-[#E0E0E0] rounded-xl overflow-hidden"
                    onClick={() => {
                      if (selectionMode) {
                        handleSelectImage(image.id);
                      } else {
                        router.push(`/dashboard/images/${image.id}`);
                      }
                    }}
                  >
                    <img
                      src={getImageUrl(image.file_path)}
                      alt={image.title}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  </div>

                  {/* Info */}
                  <div
                    className="flex-1 min-w-0"
                    onClick={() => {
                      if (selectionMode) {
                        handleSelectImage(image.id);
                      } else {
                        router.push(`/dashboard/images/${image.id}`);
                      }
                    }}
                  >
                    <h3 className="font-medium text-[#333333] truncate">
                      {image.title}
                    </h3>
                    <div className="flex flex-wrap items-center gap-3 mt-1.5 text-sm text-[#333333]/50">
                      {image.width && image.height && (
                        <span className="flex items-center gap-1">
                          <span className="w-3 h-3 rounded-sm bg-[#333333]/10"></span>
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
                      {image.ai_score && (
                        <span className="flex items-center gap-1 text-purple-600">
                          <Sparkles className="w-3 h-3" />
                          {image.ai_score.toFixed(2)}
                        </span>
                      )}
                      {image.rating_count > 0 && !image.ai_score && (
                        <span className="flex items-center gap-1 text-amber-600">
                          <span>★</span>
                          {image.average_rating.toFixed(1)}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Arrow */}
                  {!selectionMode && (
                    <div
                      className="text-[#333333]/30"
                      onClick={() => router.push(`/dashboard/images/${image.id}`)}
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

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <button
                onClick={() => goToPage(page - 1)}
                disabled={page === 1}
                className={cn(
                  "p-2 rounded-xl transition-colors cursor-pointer",
                  page === 1
                    ? "text-[#333333]/30 cursor-not-allowed"
                    : "text-[#333333] hover:bg-[#E0E0E0]"
                )}
              >
                <ChevronLeft className="w-5 h-5" />
              </button>

              <div className="flex items-center gap-1">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let pageNum;
                  if (totalPages <= 5) {
                    pageNum = i + 1;
                  } else if (page <= 3) {
                    pageNum = i + 1;
                  } else if (page >= totalPages - 2) {
                    pageNum = totalPages - 4 + i;
                  } else {
                    pageNum = page - 2 + i;
                  }

                  return (
                    <button
                      key={pageNum}
                      onClick={() => goToPage(pageNum)}
                      className={cn(
                        "w-10 h-10 rounded-xl font-medium transition-colors cursor-pointer",
                        page === pageNum
                          ? "bg-[#333333] text-white"
                          : "text-[#333333] hover:bg-[#E0E0E0]"
                      )}
                    >
                      {pageNum}
                    </button>
                  );
                })}
              </div>

              <button
                onClick={() => goToPage(page + 1)}
                disabled={page === totalPages}
                className={cn(
                  "p-2 rounded-xl transition-colors cursor-pointer",
                  page === totalPages
                    ? "text-[#333333]/30 cursor-not-allowed"
                    : "text-[#333333] hover:bg-[#E0E0E0]"
                )}
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          )}
        </>
      ) : (
        /* Empty State */
        <div className="text-center py-16">
          <div className="w-20 h-20 rounded-full bg-[#E0E0E0] flex items-center justify-center mx-auto mb-4">
            <ImageIcon className="w-10 h-10 text-[#333333]/30" />
          </div>
          <h3 className="text-lg font-medium text-[#333333]">
            {searchQuery || dateFrom || dateTo ? "No images found" : "No images yet"}
          </h3>
          <p className="text-[#333333]/60 mt-1">
            {searchQuery || dateFrom || dateTo
              ? "Try adjusting your filters"
              : "Upload your first image to get started"}
          </p>
          {!searchQuery && !dateFrom && !dateTo && (
            <Link
              href="/dashboard/upload"
              className="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-[#333333] text-white rounded-xl hover:bg-[#333333]/90 transition-colors cursor-pointer"
            >
              Upload Images
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
