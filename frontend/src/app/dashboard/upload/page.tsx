"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  Check,
  CheckCircle,
  Clock3,
  FileImage,
  Image as ImageIcon,
  Loader2,
  Trash2,
  Upload,
  XCircle,
} from "lucide-react";

import { uploadApi, type ApiError } from "@/lib/api";
import { loadUploadInbox, saveUploadInbox } from "@/lib/upload-persistence";
import { cn, computeFileHash, formatFileSize, formatRelativeTime } from "@/lib/utils";
import type { UploadItemStatus, UploadListItem } from "@/types";

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"];
const MAX_BATCH_FILES = 10;
const MAX_ITEMS = 100;

type FilterKey = "all" | "ready" | "completed" | "failed";

const statusStyles: Record<UploadItemStatus, string> = {
  pending: "bg-slate-100 text-slate-700 border-slate-200",
  uploading: "bg-sky-100 text-sky-700 border-sky-200",
  success: "bg-emerald-100 text-emerald-700 border-emerald-200",
  duplicated: "bg-amber-100 text-amber-700 border-amber-200",
  failed: "bg-rose-100 text-rose-700 border-rose-200",
};

const statusIcons = {
  pending: Clock3,
  uploading: Loader2,
  success: CheckCircle,
  duplicated: AlertTriangle,
  failed: XCircle,
} satisfies Record<UploadItemStatus, React.ComponentType<{ className?: string }>>;

const statusLabels: Record<UploadItemStatus, string> = {
  pending: "Ready",
  uploading: "Uploading",
  success: "Uploaded",
  duplicated: "Duplicate",
  failed: "Failed",
};

function getUploadFailureMessage(status?: number): string {
  if (status === 401 || status === 403) {
    return "Session expired or permission denied.";
  }
  if (status === 422) {
    return "The upload payload is invalid or the file is empty.";
  }
  return "Upload failed. Please try again.";
}

function createUploadId(): string {
  return typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function createPreview(file?: File): string | undefined {
  return file ? URL.createObjectURL(file) : undefined;
}

function revokePreview(item: Pick<UploadListItem, "preview">): void {
  if (item.preview) {
    URL.revokeObjectURL(item.preview);
  }
}

function isUploadable(item: UploadListItem): boolean {
  return (item.status === "pending" || item.status === "failed") && Boolean(item.file);
}

function isCompleted(item: UploadListItem): boolean {
  return item.status === "success" || item.status === "duplicated";
}

function compareItems(a: UploadListItem, b: UploadListItem): number {
  const order: Record<UploadItemStatus, number> = {
    uploading: 0,
    pending: 1,
    failed: 2,
    duplicated: 3,
    success: 4,
  };

  const byStatus = order[a.status] - order[b.status];
  if (byStatus !== 0) {
    return byStatus;
  }

  return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
}

function chunkItems<T>(items: T[], size: number): T[][] {
  const chunks: T[][] = [];
  for (let index = 0; index < items.length; index += size) {
    chunks.push(items.slice(index, index + size));
  }
  return chunks;
}

function buildUploadItem(file: File): UploadListItem {
  const timestamp = new Date().toISOString();
  return {
    id: createUploadId(),
    file,
    file_name: file.name,
    file_size: file.size,
    file_type: file.type,
    preview: createPreview(file),
    status: "pending",
    progress: 0,
    created_at: timestamp,
    updated_at: timestamp,
  };
}

function attachPreviews(items: UploadListItem[]): UploadListItem[] {
  return items.map((item) => ({
    ...item,
    preview: item.preview ?? createPreview(item.file),
  }));
}

function trimItems(items: UploadListItem[]): UploadListItem[] {
  if (items.length <= MAX_ITEMS) {
    return items;
  }

  const sorted = [...items].sort(compareItems);
  const keep = sorted.slice(0, MAX_ITEMS);
  const keepIds = new Set(keep.map((item) => item.id));

  items.forEach((item) => {
    if (!keepIds.has(item.id)) {
      revokePreview(item);
    }
  });

  return keep;
}

export default function UploadPage() {
  const [items, setItems] = useState<UploadListItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [selectionMode, setSelectionMode] = useState(false);
  const [filter, setFilter] = useState<FilterKey>("all");
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isHydrated, setIsHydrated] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const itemsRef = useRef<UploadListItem[]>([]);

  useEffect(() => {
    itemsRef.current = items;
  }, [items]);

  useEffect(() => {
    let active = true;

    void (async () => {
      try {
        const storedItems = attachPreviews(await loadUploadInbox());
        if (!active) {
          storedItems.forEach(revokePreview);
          return;
        }
        setItems(storedItems);
      } catch (error) {
        console.error("Failed to restore upload inbox", error);
        if (active) {
          setNotice("Local upload queue could not be restored.");
        }
      } finally {
        if (active) {
          setIsHydrated(true);
        }
      }
    })();

    return () => {
      active = false;
      itemsRef.current.forEach(revokePreview);
    };
  }, []);

  useEffect(() => {
    if (!isHydrated) {
      return;
    }

    void saveUploadInbox(items).catch((error) => {
      console.error("Failed to persist upload inbox", error);
      setNotice("Changes were made, but local persistence failed.");
    });
  }, [items, isHydrated]);

  useEffect(() => {
    setSelectedIds((prev) => {
      const activeIds = new Set(items.map((item) => item.id));
      const next = new Set([...prev].filter((id) => activeIds.has(id)));
      return next.size === prev.size ? prev : next;
    });

    if (items.length === 0) {
      setSelectionMode(false);
    }
  }, [items]);

  const validateFiles = useCallback((fileList: FileList | File[]): { valid: File[]; errors: string[] } => {
    const valid: File[] = [];
    const errors: string[] = [];

    Array.from(fileList).forEach((file) => {
      if (!ACCEPTED_TYPES.includes(file.type)) {
        errors.push(`${file.name}: unsupported file type.`);
        return;
      }

      valid.push(file);
    });

    return { valid, errors };
  }, []);

  const addFiles = useCallback((fileList: FileList | File[]) => {
    const { valid, errors } = validateFiles(fileList);

    if (errors.length > 0) {
      setNotice(errors.join(" "));
    } else {
      setNotice(null);
    }

    if (valid.length === 0) {
      return;
    }

    const newItems = valid.map(buildUploadItem);
    setItems((prev) => trimItems([...newItems, ...prev]));
  }, [validateFiles]);

  const handleDragEnter = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.stopPropagation();
  }, []);

  const handleDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(false);

    if (event.dataTransfer.files.length > 0) {
      addFiles(event.dataTransfer.files);
    }
  }, [addFiles]);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      addFiles(event.target.files);
      event.target.value = "";
    }
  };

  const removeItems = useCallback((ids: Iterable<string>) => {
    const idSet = new Set(ids);
    setItems((prev) => {
      prev.forEach((item) => {
        if (idSet.has(item.id)) {
          revokePreview(item);
        }
      });
      return prev.filter((item) => !idSet.has(item.id));
    });
    setSelectedIds((prev) => new Set([...prev].filter((id) => !idSet.has(id))));
  }, []);

  const updateItems = useCallback((ids: Set<string>, updater: (_item: UploadListItem) => UploadListItem) => {
    setItems((prev) => prev.map((item) => (ids.has(item.id) ? updater(item) : item)));
  }, []);

  const uploadItemsByIds = useCallback(async (ids: Iterable<string>) => {
    if (isUploading) {
      return;
    }

    const requestedIds = new Set(ids);
    const uploadableItems = items.filter((item) => requestedIds.has(item.id) && isUploadable(item));
    if (uploadableItems.length === 0) {
      return;
    }

    setNotice(null);
    setIsUploading(true);

    const batches = chunkItems(uploadableItems, MAX_BATCH_FILES);

    for (const batch of batches) {
      const batchIds = new Set(batch.map((item) => item.id));
      const startedAt = new Date().toISOString();

      updateItems(batchIds, (item) => ({
        ...item,
        status: "uploading",
        progress: 0,
        updated_at: startedAt,
      }));

      try {
        const hashes = await Promise.all(
          batch.map(async (item) => ({
            id: item.id,
            hash: await computeFileHash(item.file as File),
          }))
        );

        const response = await uploadApi.uploadImages(
          batch.map((item) => item.file as File),
          hashes.map((hashItem) => hashItem.hash),
          (progress) => {
            updateItems(batchIds, (item) => ({
              ...item,
              progress,
              updated_at: new Date().toISOString(),
            }));
          }
        );

        const completedAt = new Date().toISOString();
        const resultsById = new Map(batch.map((item, index) => [item.id, response.data.results[index]]));

        updateItems(batchIds, (item) => {
          const result = resultsById.get(item.id);
          if (!result) {
            return item;
          }

          return {
            ...item,
            status: result.status,
            progress: 100,
            result,
            updated_at: completedAt,
          };
        });
      } catch (error) {
        console.error("Upload error", error);
        const message = getUploadFailureMessage((error as ApiError | undefined)?.status);
        const failedAt = new Date().toISOString();

        updateItems(batchIds, (item) => ({
          ...item,
          status: "failed",
          progress: 0,
          result: {
            status: "failed",
            original_filename: item.file_name,
            error_message: message,
            is_duplicate: false,
          },
          updated_at: failedAt,
        }));
      }
    }

    setIsUploading(false);
    setSelectionMode(false);
    setSelectedIds(new Set());
  }, [isUploading, items, updateItems]);

  const handleUploadAll = async () => {
    await uploadItemsByIds(items.filter(isUploadable).map((item) => item.id));
  };

  const handleUploadSelected = async () => {
    await uploadItemsByIds(selectedIds);
  };

  const handleClearCompleted = () => {
    removeItems(items.filter(isCompleted).map((item) => item.id));
  };

  const toggleSelectionMode = () => {
    setSelectionMode((prev) => {
      if (prev) {
        setSelectedIds(new Set());
      }
      return !prev;
    });
  };

  const toggleSelectAllVisible = () => {
    const visibleIds = displayItems.map((item) => item.id);
    const allVisibleSelected = visibleIds.length > 0 && visibleIds.every((id) => selectedIds.has(id));

    setSelectedIds((prev) => {
      const next = new Set(prev);
      visibleIds.forEach((id) => {
        if (allVisibleSelected) {
          next.delete(id);
        } else {
          next.add(id);
        }
      });
      return next;
    });
  };

  const toggleItemSelection = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const readyCount = useMemo(() => items.filter(isUploadable).length, [items]);
  const completedCount = useMemo(() => items.filter(isCompleted).length, [items]);
  const failedCount = useMemo(() => items.filter((item) => item.status === "failed").length, [items]);
  const hasUploading = useMemo(() => items.some((item) => item.status === "uploading"), [items]);

  const summary = useMemo(() => ({
    total: items.length,
    ready: readyCount,
    completed: completedCount,
    failed: failedCount,
    uploading: items.filter((item) => item.status === "uploading").length,
  }), [completedCount, failedCount, items, readyCount]);

  const filters = useMemo(() => ([
    { key: "all" as const, label: "All", count: items.length },
    { key: "ready" as const, label: "Ready", count: readyCount },
    { key: "completed" as const, label: "Completed", count: completedCount },
    { key: "failed" as const, label: "Failed", count: failedCount },
  ]), [completedCount, failedCount, items.length, readyCount]);

  const displayItems = useMemo(() => {
    const filtered = items.filter((item) => {
      if (filter === "ready") {
        return isUploadable(item);
      }
      if (filter === "completed") {
        return isCompleted(item);
      }
      if (filter === "failed") {
        return item.status === "failed";
      }
      return true;
    });

    return [...filtered].sort(compareItems);
  }, [filter, items]);

  const selectedItems = useMemo(() => items.filter((item) => selectedIds.has(item.id)), [items, selectedIds]);
  const selectedReadyCount = useMemo(() => selectedItems.filter(isUploadable).length, [selectedItems]);
  const allVisibleSelected = displayItems.length > 0 && displayItems.every((item) => selectedIds.has(item.id));

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <motion.div
        className={cn(
          "relative overflow-hidden rounded-[28px] border border-[#E6E1DA] bg-[linear-gradient(135deg,rgba(255,255,255,0.96),rgba(248,244,238,0.92))] p-8 shadow-[0_25px_80px_rgba(34,34,34,0.08)]",
          isDragging && "border-[#222222] bg-[linear-gradient(135deg,rgba(255,255,255,1),rgba(240,232,220,0.98))]"
        )}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(244,193,78,0.18),transparent_36%),radial-gradient(circle_at_bottom_left,rgba(34,34,34,0.08),transparent_42%)]" />
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ACCEPTED_TYPES.join(",")}
          onChange={handleFileSelect}
          className="hidden"
        />

        <div className="relative flex flex-col gap-8 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-2xl space-y-3">
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[#333333]/45">Upload workspace</p>
            <h1 className="text-[clamp(2rem,4vw,3.25rem)] font-semibold tracking-[-0.05em] text-[#222222]">Upload</h1>
            <p className="max-w-xl text-sm leading-6 text-[#333333]/62">
              Choose local image files and keep the queue moving from one place.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 lg:justify-end">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="group relative isolate min-w-[220px] cursor-pointer overflow-hidden rounded-[24px] border border-[#222222]/10 bg-[#222222] px-6 py-4 text-left text-white shadow-[0_24px_60px_rgba(34,34,34,0.22)] transition duration-200 hover:-translate-y-0.5 hover:shadow-[0_28px_70px_rgba(34,34,34,0.28)]"
            >
              <span className="pointer-events-none absolute inset-0 bg-[linear-gradient(135deg,rgba(255,255,255,0.2),transparent_45%,rgba(244,193,78,0.34))] opacity-90 transition duration-200 group-hover:opacity-100" />
              <span className="relative flex items-center gap-4">
                <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/12 ring-1 ring-white/14 backdrop-blur-sm">
                  <Upload className="h-5 w-5" />
                </span>
                <span className="flex flex-col items-start">
                  <span className="text-base font-semibold tracking-[0.02em]">Upload</span>
                  <span className="text-xs uppercase tracking-[0.22em] text-white/70">Choose local files</span>
                </span>
              </span>
            </button>
            <button
              type="button"
              onClick={handleUploadAll}
              disabled={readyCount === 0 || isUploading}
              className={cn(
                "cursor-pointer rounded-2xl border px-5 py-3 text-sm font-medium transition",
                readyCount > 0 && !isUploading
                  ? "border-[#222222]/15 bg-white text-[#222222] hover:border-[#222222]/35 hover:bg-[#222222]/[0.03]"
                  : "cursor-not-allowed border-[#DDD6CC] bg-[#F3EEE7] text-[#333333]/35"
              )}
            >
              {isUploading ? "Uploading..." : "Start upload"}
            </button>
          </div>
        </div>
      </motion.div>

      {notice && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {notice}
        </div>
      )}

      <div className="overflow-hidden rounded-[28px] border border-[#E6E1DA] bg-white shadow-[0_20px_70px_rgba(34,34,34,0.06)]">
        <div className="border-b border-[#ECE6DD] px-6 py-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-xl font-semibold text-[#222222]">Upload inbox</h2>
              <p className="mt-1 text-sm text-[#333333]/58">
                {summary.total} items tracked locally. Pending files and completed results stay in the same list.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={toggleSelectionMode}
                disabled={items.length === 0 || hasUploading}
                className={cn(
                  "cursor-pointer rounded-2xl px-4 py-2 text-sm font-medium transition",
                  selectionMode
                    ? "bg-[#222222] text-white hover:bg-[#111111]"
                    : "border border-[#E6E1DA] bg-white text-[#222222] hover:bg-[#F6F1EA]",
                  (items.length === 0 || hasUploading) && "cursor-not-allowed opacity-45"
                )}
              >
                {selectionMode ? "Cancel selection" : "Select"}
              </button>
              <button
                onClick={handleClearCompleted}
                disabled={completedCount === 0 || hasUploading}
                className={cn(
                  "cursor-pointer rounded-2xl border px-4 py-2 text-sm font-medium transition",
                  completedCount > 0 && !hasUploading
                    ? "border-[#E6E1DA] bg-white text-[#222222] hover:bg-[#F6F1EA]"
                    : "cursor-not-allowed border-[#EEE8DF] bg-[#F8F4EE] text-[#333333]/35"
                )}
              >
                Clear completed
              </button>
            </div>
          </div>

          <div className="mt-5 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex flex-wrap gap-2">
              {filters.map((option) => (
                <button
                  key={option.key}
                  onClick={() => setFilter(option.key)}
                  className={cn(
                    "cursor-pointer rounded-full px-4 py-2 text-sm font-medium transition",
                    filter === option.key
                      ? "bg-[#222222] text-white"
                      : "bg-[#F5F0E8] text-[#333333]/70 hover:bg-[#EBE4D9]"
                  )}
                >
                  {option.label} ({option.count})
                </button>
              ))}
            </div>

            <div className="text-sm text-[#333333]/55">
              {isHydrated ? "Saved locally between refreshes." : "Restoring local queue..."}
            </div>
          </div>

          {selectionMode && (
            <div className="mt-4 flex flex-wrap items-center gap-3 rounded-2xl border border-[#ECE6DD] bg-[#FAF7F2] px-4 py-3">
              <button
                onClick={toggleSelectAllVisible}
                className="flex cursor-pointer items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-[#222222] transition hover:bg-white"
              >
                <span
                  className={cn(
                    "flex h-5 w-5 items-center justify-center rounded border-2 transition",
                    allVisibleSelected ? "border-[#222222] bg-[#222222] text-white" : "border-[#C8C0B4] bg-white"
                  )}
                >
                  {allVisibleSelected && <Check className="h-3.5 w-3.5" />}
                </span>
                Select visible
              </button>

              <span className="text-sm text-[#333333]/60">{selectedIds.size} selected</span>
              <span className="hidden h-4 w-px bg-[#E4DDD2] sm:block" />
              <span className="text-sm text-[#333333]/60">{selectedReadyCount} ready to upload</span>

              <div className="ml-auto flex flex-wrap gap-2">
                <button
                  onClick={handleUploadSelected}
                  disabled={selectedReadyCount === 0 || isUploading}
                  className={cn(
                    "cursor-pointer rounded-xl px-4 py-2 text-sm font-medium transition",
                    selectedReadyCount > 0 && !isUploading
                      ? "bg-[#222222] text-white hover:bg-[#111111]"
                      : "cursor-not-allowed bg-[#ECE5DA] text-[#333333]/35"
                  )}
                >
                  Upload selected
                </button>
                <button
                  onClick={() => removeItems(selectedIds)}
                  disabled={selectedIds.size === 0 || hasUploading}
                  className={cn(
                    "cursor-pointer rounded-xl px-4 py-2 text-sm font-medium transition",
                    selectedIds.size > 0 && !hasUploading
                      ? "bg-rose-500 text-white hover:bg-rose-600"
                      : "cursor-not-allowed bg-[#ECE5DA] text-[#333333]/35"
                  )}
                >
                  Remove selected
                </button>
              </div>
            </div>
          )}
        </div>

        {displayItems.length > 0 ? (
          <div className="divide-y divide-[#F0EAE1]">
            <AnimatePresence initial={false}>
              {displayItems.map((item) => {
                const StatusIcon = statusIcons[item.status];
                const selected = selectedIds.has(item.id);
                const canUploadThisItem = isUploadable(item) && !isUploading;

                return (
                  <motion.div
                    key={item.id}
                    layout
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    className={cn(
                      "flex flex-col gap-4 px-6 py-5 transition-colors lg:flex-row lg:items-center",
                      selected && "bg-[#FBF7F1]",
                      !selected && "hover:bg-[#FCFAF7]"
                    )}
                  >
                    <div className="flex items-start gap-4 lg:flex-1">
                      {selectionMode && (
                        <button
                          onClick={() => toggleItemSelection(item.id)}
                          className={cn(
                            "mt-2 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-lg border-2 transition",
                            selected ? "border-[#222222] bg-[#222222] text-white" : "border-[#C8C0B4] bg-white"
                          )}
                        >
                          {selected && <Check className="h-3.5 w-3.5" />}
                        </button>
                      )}

                      <div className="relative h-14 w-14 flex-shrink-0 overflow-hidden rounded-2xl border border-[#E7E0D7] bg-[#F3EEE7]">
                        {item.preview ? (
                          <img src={item.preview} alt={item.file_name} className="h-full w-full object-cover" />
                        ) : (
                          <div className="flex h-full w-full items-center justify-center">
                            <FileImage className="h-6 w-6 text-[#333333]/35" />
                          </div>
                        )}
                      </div>

                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="truncate text-base font-medium text-[#222222]">{item.file_name}</p>
                          {!item.file && item.status !== "success" && item.status !== "duplicated" && (
                            <span className="rounded-full bg-rose-50 px-2.5 py-1 text-xs font-medium text-rose-700">
                              File missing
                            </span>
                          )}
                        </div>
                        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-[#333333]/55">
                          <span>{formatFileSize(item.file_size)}</span>
                          <span>{item.file_type.replace("image/", "").toUpperCase() || "Image"}</span>
                          <span>Updated {formatRelativeTime(item.updated_at)}</span>
                        </div>

                        {item.status === "uploading" && (
                          <div className="mt-3 h-2 overflow-hidden rounded-full bg-[#EEE7DC]">
                            <motion.div
                              className="h-full rounded-full bg-[#222222]"
                              initial={{ width: 0 }}
                              animate={{ width: `${item.progress}%` }}
                              transition={{ duration: 0.25 }}
                            />
                          </div>
                        )}

                        {item.result?.error_message && item.status === "failed" && (
                          <p className="mt-2 text-sm text-rose-600">{item.result.error_message}</p>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 lg:justify-end">
                      <div
                        className={cn(
                          "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-medium",
                          statusStyles[item.status]
                        )}
                      >
                        <StatusIcon className={cn("h-4 w-4", item.status === "uploading" && "animate-spin")} />
                        <span>{statusLabels[item.status]}</span>
                        {item.status === "uploading" && <span>{item.progress}%</span>}
                      </div>

                      {!selectionMode && (
                        <>
                          {canUploadThisItem && (
                            <button
                              onClick={() => void uploadItemsByIds([item.id])}
                              className="cursor-pointer rounded-xl border border-[#D8D0C4] px-3 py-2 text-sm font-medium text-[#222222] transition hover:bg-[#F6F1EA]"
                            >
                              Upload
                            </button>
                          )}
                          <button
                            onClick={() => removeItems([item.id])}
                            disabled={hasUploading}
                            className={cn(
                              "cursor-pointer rounded-xl p-2 text-[#333333]/45 transition hover:bg-[#F6F1EA] hover:text-rose-500",
                              hasUploading && "cursor-not-allowed opacity-35"
                            )}
                            aria-label={`Remove ${item.file_name}`}
                          >
                            <Trash2 className="h-4.5 w-4.5" />
                          </button>
                        </>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        ) : (
          <div className="px-6 py-16 text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-3xl bg-[#F3EEE7] text-[#333333]/35">
              <ImageIcon className="h-8 w-8" />
            </div>
            <h3 className="mt-5 text-lg font-semibold text-[#222222]">Nothing in this view</h3>
            <p className="mt-2 text-sm text-[#333333]/55">
              {items.length === 0
                ? "Add images above to start building your persistent upload queue."
                : "Change the filter or add more files to populate this list."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
