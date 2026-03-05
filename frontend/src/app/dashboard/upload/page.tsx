"use client";

import { useCallback, useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload,
  X,
  Image as ImageIcon,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Loader2,
  FileImage,
} from "lucide-react";

import { uploadApi } from "@/lib/api";
import { cn, formatFileSize, computeFileHash, formatRelativeTime } from "@/lib/utils";
import type { UploadHistoryItem, UploadResult } from "@/types";

// Supported image types
const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"];
const MAX_FILES = 10;

// Status badge styles
const statusStyles = {
  pending: "bg-gray-100 text-gray-600 border-gray-200",
  uploading: "bg-blue-100 text-blue-600 border-blue-200",
  success: "bg-green-100 text-green-600 border-green-200",
  duplicated: "bg-amber-100 text-amber-600 border-amber-200",
  failed: "bg-red-100 text-red-600 border-red-200",
};

const statusIcons = {
  pending: null,
  uploading: Loader2,
  success: CheckCircle,
  duplicated: AlertTriangle,
  failed: XCircle,
};

const statusLabels = {
  pending: "Pending",
  uploading: "Uploading",
  success: "Success",
  duplicated: "Duplicate",
  failed: "Failed",
};

export default function UploadPage() {
  const [files, setFiles] = useState<UploadHistoryItem[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadHistory, setUploadHistory] = useState<
    Array<{ file: File; result: UploadResult; timestamp: Date }>
  >([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load upload history from localStorage
  useEffect(() => {
    const savedHistory = localStorage.getItem("uploadHistory");
    if (savedHistory) {
      try {
        const parsed = JSON.parse(savedHistory);
        setUploadHistory(
          parsed.map((item: { fileName: string; fileSize: number; result: UploadResult; timestamp: string }) => ({
            file: { name: item.fileName, size: item.fileSize } as File,
            result: item.result,
            timestamp: new Date(item.timestamp),
          }))
        );
      } catch {
        // Ignore parsing errors
      }
    }
  }, []);

  // Save upload history to localStorage
  const saveToHistory = (file: File, result: UploadResult) => {
    const updated = [
      { file, result, timestamp: new Date() },
      ...uploadHistory.slice(0, 49), // Keep last 50 items
    ];

    setUploadHistory(updated);

    // Save to localStorage (without File objects)
    const storableHistory = updated.map((item) => ({
      fileName: item.file.name,
      fileSize: item.file.size,
      result: item.result,
      timestamp: item.timestamp.toISOString(),
    }));
    localStorage.setItem("uploadHistory", JSON.stringify(storableHistory));
  };

  // Validate files
  const validateFiles = useCallback((fileList: FileList | File[]): { valid: File[]; errors: string[] } => {
    const valid: File[] = [];
    const errors: string[] = [];
    const fileArray = Array.from(fileList);

    fileArray.forEach((file) => {
      if (!ACCEPTED_TYPES.includes(file.type)) {
        errors.push(`${file.name}: Unsupported file type`);
      } else {
        valid.push(file);
      }
    });

    if (valid.length > MAX_FILES) {
      errors.push(`Maximum ${MAX_FILES} files allowed. Only first ${MAX_FILES} will be uploaded.`);
      return { valid: valid.slice(0, MAX_FILES), errors };
    }

    return { valid, errors };
  }, []);

  // Add files to upload queue
  const addFiles = useCallback((fileList: FileList | File[]) => {
    const { valid } = validateFiles(fileList);

    const newFiles: UploadHistoryItem[] = valid.map((file) => ({
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      file,
      preview: URL.createObjectURL(file),
      status: "pending",
      progress: 0,
    }));

    setFiles((prev) => [...prev, ...newFiles]);
  }, [validateFiles]);

  // Handle drag events
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      const droppedFiles = e.dataTransfer.files;
      if (droppedFiles.length > 0) {
        addFiles(droppedFiles);
      }
    },
    [addFiles]
  );

  // Handle file input change
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      addFiles(e.target.files);
      e.target.value = ""; // Reset input
    }
  };

  // Remove file from queue
  const removeFile = (id: string) => {
    setFiles((prev) => {
      const file = prev.find((f) => f.id === id);
      if (file?.preview) {
        URL.revokeObjectURL(file.preview);
      }
      return prev.filter((f) => f.id !== id);
    });
  };

  // Upload all files
  const uploadAllFiles = async () => {
    if (files.length === 0 || isUploading) return;

    setIsUploading(true);

    // Mark all as uploading
    setFiles((prev) =>
      prev.map((f) => (f.status === "pending" ? { ...f, status: "uploading" as const } : f))
    );

    try {
      // Compute hashes for all files
      const pendingFiles = files.filter((f) => f.status === "uploading");
      const hashes = await Promise.all(
        pendingFiles.map(async (f) => ({
          id: f.id,
          hash: await computeFileHash(f.file),
        }))
      );

      // Upload files
      const response = await uploadApi.uploadImages(
        pendingFiles.map((f) => f.file),
        hashes.map((h) => h.hash),
        (progress) => {
          // Update progress for all files
          setFiles((prev) =>
            prev.map((f) =>
              f.status === "uploading" ? { ...f, progress } : f
            )
          );
        }
      );

      // Process results
      const results = response.data.results;

      setFiles((prev) => {
        const updated = [...prev];
        results.forEach((result) => {
          const pendingFile = pendingFiles.find(
            (f) => f.file.name === result.original_filename
          );
          if (pendingFile) {
            const index = updated.findIndex((f) => f.id === pendingFile.id);
            if (index !== -1) {
              updated[index] = {
                ...updated[index],
                status: result.status,
                progress: 100,
                result,
              };

              // Save to history
              saveToHistory(updated[index].file, result);
            }
          }
        });
        return updated;
      });
    } catch (error) {
      console.error("Upload error:", error);
      // Mark all uploading files as failed
      setFiles((prev) =>
        prev.map((f) =>
          f.status === "uploading"
            ? {
                ...f,
                status: "failed" as const,
                result: {
                  status: "failed",
                  original_filename: f.file.name,
                  error_message: "Upload failed. Please try again.",
                  is_duplicate: false,
                },
              }
            : f
        )
      );
    } finally {
      setIsUploading(false);
    }
  };

  // Clear completed files
  const clearCompleted = () => {
    setFiles((prev) => {
      prev.forEach((f) => {
        if (f.preview) {
          URL.revokeObjectURL(f.preview);
        }
      });
      return prev.filter((f) => f.status === "pending");
    });
  };

  const pendingCount = files.filter((f) => f.status === "pending").length;
  const hasUploading = files.some((f) => f.status === "uploading");

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-[#333333]">Upload Images</h1>
        <p className="text-[#333333]/60 mt-1">
          Upload and manage your images for AI quality analysis
        </p>
      </div>

      {/* Drop Zone */}
      <motion.div
        className={cn(
          "relative glass-card rounded-2xl p-8 transition-all duration-300",
          isDragging && "ring-2 ring-[#333333] ring-offset-2 bg-[#333333]/5"
        )}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ACCEPTED_TYPES.join(",")}
          onChange={handleFileSelect}
          className="hidden"
        />

        <div
          className="flex flex-col items-center justify-center cursor-pointer py-8"
          onClick={() => fileInputRef.current?.click()}
        >
          <div className="w-16 h-16 rounded-full bg-[#333333]/10 flex items-center justify-center mb-4">
            <Upload className="w-8 h-8 text-[#333333]/60" />
          </div>
          <p className="text-lg font-medium text-[#333333] mb-2">
            Drop images here or click to select
          </p>
          <p className="text-sm text-[#333333]/50">
            Supports: JPG, PNG, GIF, WEBP (Max {MAX_FILES} files)
          </p>
        </div>
      </motion.div>

      {/* Selected Files */}
      <AnimatePresence>
        {files.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="glass-card rounded-2xl overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-[#E0E0E0]">
              <div className="flex items-center gap-3">
                <h2 className="font-medium text-[#333333]">
                  Selected Files ({files.length})
                </h2>
                {pendingCount > 0 && (
                  <span className="text-sm text-[#333333]/50">
                    ({pendingCount} pending)
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={clearCompleted}
                  className="px-3 py-1.5 text-sm text-[#333333]/60 hover:text-[#333333] transition-colors cursor-pointer"
                >
                  Clear completed
                </button>
                <button
                  onClick={uploadAllFiles}
                  disabled={pendingCount === 0 || isUploading}
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 rounded-xl font-medium transition-all cursor-pointer",
                    pendingCount > 0 && !isUploading
                      ? "bg-[#333333] text-white hover:bg-[#333333]/90"
                      : "bg-[#E0E0E0] text-[#333333]/50 cursor-not-allowed"
                  )}
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4" />
                      Upload All
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* File List */}
            <div className="divide-y divide-[#E0E0E0]">
              <AnimatePresence>
                {files.map((file, index) => {
                  const StatusIcon = statusIcons[file.status];
                  return (
                    <motion.div
                      key={file.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                      transition={{ delay: index * 0.05 }}
                      className="flex items-center gap-4 p-4 hover:bg-[#333333]/5 transition-colors"
                    >
                      {/* Preview */}
                      <div className="w-12 h-12 rounded-lg overflow-hidden bg-[#E0E0E0] flex-shrink-0">
                        {file.preview ? (
                          <img
                            src={file.preview}
                            alt={file.file.name}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <FileImage className="w-6 h-6 text-[#333333]/40" />
                          </div>
                        )}
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-[#333333] truncate">
                          {file.file.name}
                        </p>
                        <p className="text-sm text-[#333333]/50">
                          {formatFileSize(file.file.size)}
                        </p>

                        {/* Progress Bar */}
                        {file.status === "uploading" && (
                          <div className="mt-2 h-1.5 bg-[#E0E0E0] rounded-full overflow-hidden">
                            <motion.div
                              className="h-full bg-[#333333]"
                              initial={{ width: 0 }}
                              animate={{ width: `${file.progress}%` }}
                              transition={{ duration: 0.3 }}
                            />
                          </div>
                        )}

                        {/* Error Message */}
                        {file.status === "failed" && file.result?.error_message && (
                          <p className="text-sm text-red-500 mt-1">
                            {file.result.error_message}
                          </p>
                        )}
                      </div>

                      {/* Status Badge */}
                      <div
                        className={cn(
                          "flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium border",
                          statusStyles[file.status]
                        )}
                      >
                        {StatusIcon && (
                          <StatusIcon
                            className={cn(
                              "w-4 h-4",
                              file.status === "uploading" && "animate-spin"
                            )}
                          />
                        )}
                        {statusLabels[file.status]}
                        {file.status === "uploading" && ` ${file.progress}%`}
                      </div>

                      {/* Remove Button */}
                      {!hasUploading && (
                        <button
                          onClick={() => removeFile(file.id)}
                          className="p-1.5 text-[#333333]/40 hover:text-red-500 transition-colors cursor-pointer"
                        >
                          <X className="w-5 h-5" />
                        </button>
                      )}
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Upload History */}
      {uploadHistory.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card rounded-2xl overflow-hidden"
        >
          <div className="flex items-center justify-between p-4 border-b border-[#E0E0E0]">
            <h2 className="font-medium text-[#333333]">Upload History</h2>
            <button
              onClick={() => {
                setUploadHistory([]);
                localStorage.removeItem("uploadHistory");
              }}
              className="text-sm text-[#333333]/60 hover:text-[#333333] transition-colors cursor-pointer"
            >
              Clear history
            </button>
          </div>

          <div className="divide-y divide-[#E0E0E0] max-h-[400px] overflow-y-auto">
            {uploadHistory.map((item, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: index * 0.03 }}
                className="flex items-center gap-4 p-4 hover:bg-[#333333]/5 transition-colors"
              >
                {/* Icon */}
                <div className="w-10 h-10 rounded-lg bg-[#E0E0E0] flex items-center justify-center flex-shrink-0">
                  <ImageIcon className="w-5 h-5 text-[#333333]/40" />
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-[#333333] truncate">
                    {item.file.name}
                  </p>
                  <p className="text-sm text-[#333333]/50">
                    {formatFileSize(item.file.size)}
                  </p>
                </div>

                {/* Status */}
                <div
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium border",
                    statusStyles[item.result.status]
                  )}
                >
                  {item.result.status === "success" && (
                    <>
                      <CheckCircle className="w-4 h-4" />
                      Success
                    </>
                  )}
                  {item.result.status === "duplicated" && (
                    <>
                      <AlertTriangle className="w-4 h-4" />
                      Duplicate
                    </>
                  )}
                  {item.result.status === "failed" && (
                    <>
                      <XCircle className="w-4 h-4" />
                      Failed
                    </>
                  )}
                </div>

                {/* Time */}
                <span className="text-sm text-[#333333]/40">
                  {formatRelativeTime(item.timestamp)}
                </span>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Empty State */}
      {files.length === 0 && uploadHistory.length === 0 && (
        <div className="text-center py-12">
          <div className="w-20 h-20 rounded-full bg-[#E0E0E0] flex items-center justify-center mx-auto mb-4">
            <ImageIcon className="w-10 h-10 text-[#333333]/30" />
          </div>
          <p className="text-[#333333]/60">No images uploaded yet</p>
          <p className="text-sm text-[#333333]/40 mt-1">
            Drop images above or click to select files
          </p>
        </div>
      )}
    </div>
  );
}
