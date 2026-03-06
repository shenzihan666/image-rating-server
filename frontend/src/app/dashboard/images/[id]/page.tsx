"use client";

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Edit2,
  Trash2,
  Loader2,
  Image as ImageIcon,
  Calendar,
  FileImage,
  HardDrive,
  Check,
  X,
  Star,
  Sparkles,
  AlertCircle,
} from "lucide-react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";

import { imageApi, aiAnalyzeApi, type ApiError } from "@/lib/api";
import { getImageUrl } from "@/lib/image-url";
import { cn, formatDateTime, formatFileSize } from "@/lib/utils";
import type { Image } from "@/types";

interface AnalysisResult {
  image_id: string;
  model: string;
  score: number | null;
  details: {
    distribution?: Record<string, number>;
    min_score?: number;
    max_score?: number;
    [key: string]: unknown;
  };
  created_at: string;
}

export default function ImageDetailPage() {
  const router = useRouter();
  const params = useParams();
  const imageId = params.id as string;
  const [image, setImage] = useState<Image | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "success" | "error">("idle");

  // Analysis state
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  const fetchImage = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await imageApi.getImage(imageId);
      setImage(response.data);
      setEditTitle(response.data.title);
      setEditDescription(response.data.description || "");
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.detail || "Failed to load image");
      if (apiError.status === 401) {
        // Already handled by api interceptor
        return;
      }
      if (apiError.status === 404) {
        setError("Image not found");
      }
    } finally {
      setLoading(false);
    }
  }, [imageId]);

  useEffect(() => {
    fetchImage();
  }, [fetchImage]);

  const handleSave = async () => {
    if (!image) return;

    setSaveStatus("saving");
    try {
      const response = await imageApi.updateImage(imageId, {
        title: editTitle,
        description: editDescription || undefined,
      });
      setImage(response.data);
      setIsEditing(false);
      setSaveStatus("success");
      setTimeout(() => setSaveStatus("idle"), 2000);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.detail || "Failed to update image");
      setSaveStatus("error");
      setTimeout(() => setSaveStatus("idle"), 2000);
    }
  };

  const handleDelete = async () => {
    if (!image || !confirm("Are you sure you want to delete this image? This action cannot be undone.")) {
      return;
    }

    setIsDeleting(true);
    try {
      await imageApi.deleteImage(imageId);
      router.push("/dashboard/images");
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.detail || "Failed to delete image");
      setIsDeleting(false);
    }
  };

  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    setAnalysisError(null);
    try {
      const response = await aiAnalyzeApi.analyzeImage(imageId);
      setAnalysisResult(response.data as AnalysisResult);
    } catch (err) {
      const apiError = err as ApiError;
      setAnalysisError(apiError.detail || "Failed to analyze image");
    } finally {
      setIsAnalyzing(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[400px] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin mx-auto text-[#333333]" />
          <p className="mt-4 text-[#333333]/60">Loading image...</p>
        </div>
      </div>
    );
  }

  if (error || !image) {
    return (
      <div className="min-h-[400px] flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-4">
            <ImageIcon className="w-8 h-8 text-red-500" />
          </div>
          <p className="text-[#333333] font-medium">{error || "Image not found"}</p>
          <Link
            href="/dashboard/images"
            className="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-[#333333] text-white rounded-xl hover:bg-[#333333]/90 transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Gallery
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Link
          href="/dashboard/images"
          className="flex items-center gap-2 text-[#333333]/60 hover:text-[#333333] transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Gallery</span>
        </Link>

        <div className="flex items-center gap-2">
          {!isEditing ? (
            <>
              <button
                onClick={handleAnalyze}
                disabled={isAnalyzing}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-purple-500 to-pink-500 text-white font-medium hover:from-purple-600 hover:to-pink-600 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isAnalyzing ? (
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
                onClick={() => setIsEditing(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl border border-[#E0E0E0] text-[#333333] hover:bg-[#E0E0E0] transition-colors cursor-pointer"
              >
                <Edit2 className="w-4 h-4" />
                Edit
              </button>
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className="flex items-center gap-2 px-4 py-2 rounded-xl border border-red-200 text-red-600 hover:bg-red-50 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isDeleting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Trash2 className="w-4 h-4" />
                )}
                Delete
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => {
                  setIsEditing(false);
                  setEditTitle(image.title);
                  setEditDescription(image.description || "");
                }}
                className="flex items-center gap-2 px-4 py-2 rounded-xl border border-[#E0E0E0] text-[#333333] hover:bg-[#E0E0E0] transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saveStatus === "saving"}
                className={cn(
                  "flex items-center gap-2 px-4 py-2 rounded-xl font-medium transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed",
                  saveStatus === "success"
                    ? "bg-green-600 text-white"
                    : "bg-[#333333] text-white hover:bg-[#333333]/90"
                )}
              >
                {saveStatus === "saving" && <Loader2 className="w-4 h-4 animate-spin" />}
                {saveStatus === "success" && <Check className="w-4 h-4" />}
                {saveStatus === "success" ? "Saved!" : "Save"}
              </button>
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8">
        {/* Image Preview */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card rounded-2xl p-4"
        >
          <div className="aspect-square bg-[#E0E0E0] rounded-xl overflow-hidden">
            <img
              src={getImageUrl(image.file_path)}
              alt={image.title}
              className="w-full h-full object-contain"
            />
          </div>
        </motion.div>

        {/* Details */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="space-y-6"
        >
          {/* Title & Description */}
          <div className="glass-card rounded-2xl p-6 space-y-4">
            {!isEditing ? (
              <>
                <h1 className="text-2xl font-bold text-[#333333]">{image.title}</h1>
                {image.description && (
                  <p className="text-[#333333]/70">{image.description}</p>
                )}
                {!image.description && (
                  <p className="text-[#333333]/40 italic">No description</p>
                )}
              </>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-[#333333] mb-2">
                    Title
                  </label>
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className="w-full px-4 py-2 rounded-xl border border-[#E0E0E0] focus:outline-none focus:ring-2 focus:ring-[#333333]/20 focus:border-[#333333] transition-all"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#333333] mb-2">
                    Description
                  </label>
                  <textarea
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                    rows={4}
                    placeholder="Add a description..."
                    className="w-full px-4 py-2 rounded-xl border border-[#E0E0E0] focus:outline-none focus:ring-2 focus:ring-[#333333]/20 focus:border-[#333333] transition-all resize-none"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Metadata */}
          <div className="glass-card rounded-2xl p-6">
            <h2 className="text-sm font-medium text-[#333333]/60 uppercase tracking-wide mb-4">
              Image Details
            </h2>
            <div className="space-y-4">
              {/* Dimensions */}
              {image.width && image.height && (
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-[#333333]/10 flex items-center justify-center">
                    <FileImage className="w-5 h-5 text-[#333333]" />
                  </div>
                  <div>
                    <p className="text-sm text-[#333333]/60">Dimensions</p>
                    <p className="font-medium text-[#333333]">
                      {image.width} × {image.height} px
                    </p>
                  </div>
                </div>
              )}

              {/* File Size */}
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-[#333333]/10 flex items-center justify-center">
                  <HardDrive className="w-5 h-5 text-[#333333]" />
                </div>
                <div>
                  <p className="text-sm text-[#333333]/60">File Size</p>
                  <p className="font-medium text-[#333333]">
                    {formatFileSize(image.file_size)}
                  </p>
                </div>
              </div>

              {/* Upload Date */}
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-[#333333]/10 flex items-center justify-center">
                  <Calendar className="w-5 h-5 text-[#333333]" />
                </div>
                <div>
                  <p className="text-sm text-[#333333]/60">Uploaded</p>
                  <p className="font-medium text-[#333333]">
                    {formatDateTime(image.created_at)}
                  </p>
                </div>
              </div>

              {/* MIME Type */}
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-[#333333]/10 flex items-center justify-center">
                  <ImageIcon className="w-5 h-5 text-[#333333]" />
                </div>
                <div>
                  <p className="text-sm text-[#333333]/60">Type</p>
                  <p className="font-medium text-[#333333]">{image.mime_type}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Rating */}
          {image.rating_count > 0 && (
            <div className="glass-card rounded-2xl p-6">
              <h2 className="text-sm font-medium text-[#333333]/60 uppercase tracking-wide mb-4">
                Rating
              </h2>
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-yellow-100 flex items-center justify-center">
                  <Star className="w-6 h-6 text-yellow-600 fill-yellow-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-[#333333]">
                    {image.average_rating.toFixed(1)}
                  </p>
                  <p className="text-sm text-[#333333]/60">
                    {image.rating_count} {image.rating_count === 1 ? "rating" : "ratings"}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* AI Analysis Result */}
          {analysisResult && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-card rounded-2xl p-6 bg-gradient-to-br from-purple-50 to-pink-50 border-purple-100"
            >
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-medium text-purple-600 uppercase tracking-wide">
                  AI Analysis
                </h2>
                <span className="text-xs px-2 py-1 bg-purple-100 text-purple-600 rounded-full">
                  {analysisResult.model.toUpperCase()}
                </span>
              </div>

              {analysisResult.score !== null && (
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                    <Sparkles className="w-7 h-7 text-white" />
                  </div>
                  <div>
                    <p className="text-3xl font-bold text-[#333333]">
                      {analysisResult.score.toFixed(2)}
                    </p>
                    <p className="text-sm text-[#333333]/60">Quality Score</p>
                  </div>
                </div>
              )}

              {analysisResult.details.distribution && (
                <div className="mt-4">
                  <p className="text-xs text-[#333333]/50 mb-2">Score Distribution</p>
                  <div className="flex items-end gap-1 h-16">
                    {Object.entries(analysisResult.details.distribution).map(([score, probability]) => (
                      <div
                        key={score}
                        className="flex-1 flex flex-col items-center gap-1"
                      >
                        <div
                          className="w-full bg-gradient-to-t from-purple-500 to-pink-400 rounded-t-sm transition-all"
                          style={{ height: `${probability * 100}%` }}
                        />
                        <span className="text-xs text-[#333333]/50">{score}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <p className="text-xs text-[#333333]/40 mt-4">
                Analyzed at {new Date(analysisResult.created_at).toLocaleString()}
              </p>
            </motion.div>
          )}

          {/* Analysis Error */}
          {analysisError && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-card rounded-2xl p-6 bg-red-50 border-red-100"
            >
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-medium text-red-700">Analysis Failed</h3>
                  <p className="text-sm text-red-600 mt-1">{analysisError}</p>
                </div>
              </div>
            </motion.div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
