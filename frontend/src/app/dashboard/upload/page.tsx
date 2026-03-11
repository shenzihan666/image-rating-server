'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
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
} from 'lucide-react'

import { uploadApi, type ApiError } from '@/lib/api'
import { loadUploadInbox, saveUploadInbox } from '@/lib/upload-persistence'
import { cn, computeFileHash, formatFileSize, formatRelativeTime } from '@/lib/utils'
import type { UploadItemStatus, UploadListItem } from '@/types'

const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
const MAX_BATCH_FILES = 10
const MAX_ITEMS = 100

type FilterKey = 'all' | 'ready' | 'completed' | 'failed'

const statusStyles: Record<UploadItemStatus, string> = {
  pending: 'border-slate-200 bg-slate-100 text-slate-700',
  uploading: 'border-sky-200 bg-sky-100 text-sky-700',
  success: 'border-emerald-200 bg-emerald-100 text-emerald-700',
  duplicated: 'border-amber-200 bg-amber-100 text-amber-700',
  failed: 'border-rose-200 bg-rose-100 text-rose-700',
}

const statusIcons = {
  pending: Clock3,
  uploading: Loader2,
  success: CheckCircle,
  duplicated: AlertTriangle,
  failed: XCircle,
} satisfies Record<UploadItemStatus, React.ComponentType<{ className?: string }>>

const statusLabels: Record<UploadItemStatus, string> = {
  pending: 'Ready',
  uploading: 'Uploading',
  success: 'Uploaded',
  duplicated: 'Duplicate',
  failed: 'Failed',
}

const buttonBaseClass =
  'inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-45'

const neutralButtonClass = 'bg-[#E0E0E0] text-[#333333] hover:bg-[#D5D5D5]'
const outlineButtonClass = 'border border-[#E0E0E0] bg-white text-[#333333] hover:bg-[#F6F6F6]'
const primaryButtonClass = 'bg-[#333333] text-white hover:bg-[#262626]'
const destructiveButtonClass = 'bg-rose-500 text-white hover:bg-rose-600'

function getUploadFailureMessage(status?: number): string {
  if (status === 401 || status === 403) {
    return 'Session expired or permission denied.'
  }
  if (status === 422) {
    return 'The upload payload is invalid or the file is empty.'
  }
  return 'Upload failed. Please try again.'
}

function createUploadId(): string {
  return typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

function createPreview(file?: File): string | undefined {
  return file ? URL.createObjectURL(file) : undefined
}

function revokePreview(item: Pick<UploadListItem, 'preview'>): void {
  if (item.preview) {
    URL.revokeObjectURL(item.preview)
  }
}

function isUploadable(item: UploadListItem): boolean {
  return (item.status === 'pending' || item.status === 'failed') && Boolean(item.file)
}

function isCompleted(item: UploadListItem): boolean {
  return item.status === 'success' || item.status === 'duplicated'
}

function compareItems(a: UploadListItem, b: UploadListItem): number {
  const order: Record<UploadItemStatus, number> = {
    uploading: 0,
    pending: 1,
    failed: 2,
    duplicated: 3,
    success: 4,
  }

  const byStatus = order[a.status] - order[b.status]
  if (byStatus !== 0) {
    return byStatus
  }

  return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
}

function chunkItems<T>(items: T[], size: number): T[][] {
  const chunks: T[][] = []
  for (let index = 0; index < items.length; index += size) {
    chunks.push(items.slice(index, index + size))
  }
  return chunks
}

function buildUploadItem(file: File): UploadListItem {
  const timestamp = new Date().toISOString()
  return {
    id: createUploadId(),
    file,
    file_name: file.name,
    file_size: file.size,
    file_type: file.type,
    preview: createPreview(file),
    status: 'pending',
    progress: 0,
    created_at: timestamp,
    updated_at: timestamp,
  }
}

function attachPreviews(items: UploadListItem[]): UploadListItem[] {
  return items.map((item) => ({
    ...item,
    preview: item.preview ?? createPreview(item.file),
  }))
}

function trimItems(items: UploadListItem[]): UploadListItem[] {
  if (items.length <= MAX_ITEMS) {
    return items
  }

  const sorted = [...items].sort(compareItems)
  const keep = sorted.slice(0, MAX_ITEMS)
  const keepIds = new Set(keep.map((item) => item.id))

  items.forEach((item) => {
    if (!keepIds.has(item.id)) {
      revokePreview(item)
    }
  })

  return keep
}

export default function UploadPage() {
  const [items, setItems] = useState<UploadListItem[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [selectionMode, setSelectionMode] = useState(false)
  const [filter, setFilter] = useState<FilterKey>('all')
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [isHydrated, setIsHydrated] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const itemsRef = useRef<UploadListItem[]>([])

  useEffect(() => {
    itemsRef.current = items
  }, [items])

  useEffect(() => {
    let active = true

    void (async () => {
      try {
        const storedItems = attachPreviews(await loadUploadInbox())
        if (!active) {
          storedItems.forEach(revokePreview)
          return
        }
        setItems(storedItems)
      } catch (error) {
        console.error('Failed to restore upload inbox', error)
        if (active) {
          setNotice('Local upload queue could not be restored.')
        }
      } finally {
        if (active) {
          setIsHydrated(true)
        }
      }
    })()

    return () => {
      active = false
      itemsRef.current.forEach(revokePreview)
    }
  }, [])

  useEffect(() => {
    if (!isHydrated) {
      return
    }

    void saveUploadInbox(items).catch((error) => {
      console.error('Failed to persist upload inbox', error)
      setNotice('Changes were made, but local persistence failed.')
    })
  }, [items, isHydrated])

  useEffect(() => {
    setSelectedIds((prev) => {
      const activeIds = new Set(items.map((item) => item.id))
      const next = new Set([...prev].filter((id) => activeIds.has(id)))
      return next.size === prev.size ? prev : next
    })

    if (items.length === 0) {
      setSelectionMode(false)
    }
  }, [items])

  const validateFiles = useCallback(
    (fileList: FileList | File[]): { valid: File[]; errors: string[] } => {
      const valid: File[] = []
      const errors: string[] = []

      Array.from(fileList).forEach((file) => {
        if (!ACCEPTED_TYPES.includes(file.type)) {
          errors.push(`${file.name}: unsupported file type.`)
          return
        }

        valid.push(file)
      })

      return { valid, errors }
    },
    []
  )

  const addFiles = useCallback(
    (fileList: FileList | File[]) => {
      const { valid, errors } = validateFiles(fileList)

      if (errors.length > 0) {
        setNotice(errors.join(' '))
      } else {
        setNotice(null)
      }

      if (valid.length === 0) {
        return
      }

      const newItems = valid.map(buildUploadItem)
      setItems((prev) => trimItems([...newItems, ...prev]))
    },
    [validateFiles]
  )

  const handleDragEnter = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragging(false)
  }, [])

  const handleDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
  }, [])

  const handleDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()
      event.stopPropagation()
      setIsDragging(false)

      if (event.dataTransfer.files.length > 0) {
        addFiles(event.dataTransfer.files)
      }
    },
    [addFiles]
  )

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      addFiles(event.target.files)
      event.target.value = ''
    }
  }

  const removeItems = useCallback((ids: Iterable<string>) => {
    const idSet = new Set(ids)
    setItems((prev) => {
      prev.forEach((item) => {
        if (idSet.has(item.id)) {
          revokePreview(item)
        }
      })
      return prev.filter((item) => !idSet.has(item.id))
    })
    setSelectedIds((prev) => new Set([...prev].filter((id) => !idSet.has(id))))
  }, [])

  const updateItems = useCallback(
    (ids: Set<string>, updater: (_item: UploadListItem) => UploadListItem) => {
      setItems((prev) => prev.map((item) => (ids.has(item.id) ? updater(item) : item)))
    },
    []
  )

  const uploadItemsByIds = useCallback(
    async (ids: Iterable<string>) => {
      if (isUploading) {
        return
      }

      const requestedIds = new Set(ids)
      const uploadableItems = items.filter(
        (item) => requestedIds.has(item.id) && isUploadable(item)
      )
      if (uploadableItems.length === 0) {
        return
      }

      setNotice(null)
      setIsUploading(true)

      const batches = chunkItems(uploadableItems, MAX_BATCH_FILES)

      for (const batch of batches) {
        const batchIds = new Set(batch.map((item) => item.id))
        const startedAt = new Date().toISOString()

        updateItems(batchIds, (item) => ({
          ...item,
          status: 'uploading',
          progress: 0,
          updated_at: startedAt,
        }))

        try {
          const hashes = await Promise.all(
            batch.map(async (item) => ({
              id: item.id,
              hash: await computeFileHash(item.file as File),
            }))
          )

          const response = await uploadApi.uploadImages(
            batch.map((item) => item.file as File),
            hashes.map((hashItem) => hashItem.hash),
            (progress) => {
              updateItems(batchIds, (item) => ({
                ...item,
                progress,
                updated_at: new Date().toISOString(),
              }))
            }
          )

          const completedAt = new Date().toISOString()
          const resultsById = new Map(
            batch.map((item, index) => [item.id, response.data.results[index]])
          )

          updateItems(batchIds, (item) => {
            const result = resultsById.get(item.id)
            if (!result) {
              return item
            }

            return {
              ...item,
              status: result.status,
              progress: 100,
              result,
              updated_at: completedAt,
            }
          })
        } catch (error) {
          console.error('Upload error', error)
          const message = getUploadFailureMessage((error as ApiError | undefined)?.status)
          const failedAt = new Date().toISOString()

          updateItems(batchIds, (item) => ({
            ...item,
            status: 'failed',
            progress: 0,
            result: {
              status: 'failed',
              original_filename: item.file_name,
              error_message: message,
              is_duplicate: false,
            },
            updated_at: failedAt,
          }))
        }
      }

      setIsUploading(false)
      setSelectionMode(false)
      setSelectedIds(new Set())
    },
    [isUploading, items, updateItems]
  )

  const handleUploadSelected = async () => {
    await uploadItemsByIds(selectedIds)
  }

  const handleClearCompleted = () => {
    removeItems(items.filter(isCompleted).map((item) => item.id))
  }

  const toggleSelectionMode = () => {
    setSelectionMode((prev) => {
      if (prev) {
        setSelectedIds(new Set())
      }
      return !prev
    })
  }

  const toggleSelectAllVisible = () => {
    const visibleIds = displayItems.map((item) => item.id)
    const allVisibleSelected =
      visibleIds.length > 0 && visibleIds.every((id) => selectedIds.has(id))

    setSelectedIds((prev) => {
      const next = new Set(prev)
      visibleIds.forEach((id) => {
        if (allVisibleSelected) {
          next.delete(id)
        } else {
          next.add(id)
        }
      })
      return next
    })
  }

  const toggleItemSelection = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const readyCount = useMemo(() => items.filter(isUploadable).length, [items])
  const completedCount = useMemo(() => items.filter(isCompleted).length, [items])
  const failedCount = useMemo(
    () => items.filter((item) => item.status === 'failed').length,
    [items]
  )
  const hasUploading = useMemo(() => items.some((item) => item.status === 'uploading'), [items])

  const filters = useMemo(
    () => [
      { key: 'all' as const, label: 'All', count: items.length },
      { key: 'ready' as const, label: 'Ready', count: readyCount },
      { key: 'completed' as const, label: 'Completed', count: completedCount },
      { key: 'failed' as const, label: 'Failed', count: failedCount },
    ],
    [completedCount, failedCount, items.length, readyCount]
  )

  const displayItems = useMemo(() => {
    const filtered = items.filter((item) => {
      if (filter === 'ready') {
        return isUploadable(item)
      }
      if (filter === 'completed') {
        return isCompleted(item)
      }
      if (filter === 'failed') {
        return item.status === 'failed'
      }
      return true
    })

    return [...filtered].sort(compareItems)
  }, [filter, items])

  const selectedItems = useMemo(
    () => items.filter((item) => selectedIds.has(item.id)),
    [items, selectedIds]
  )
  const selectedReadyCount = useMemo(
    () => selectedItems.filter(isUploadable).length,
    [selectedItems]
  )
  const allVisibleSelected =
    displayItems.length > 0 && displayItems.every((item) => selectedIds.has(item.id))

  return (
    <div className="space-y-6">
      <motion.section
        className={cn(
          'glass-card relative overflow-hidden rounded-2xl border border-[#E0E0E0] p-6 lg:p-8',
          isDragging && 'border-[#333333]/35 shadow-[0_20px_48px_rgba(0,0,0,0.12)]'
        )}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(51,51,51,0.08),transparent_34%),radial-gradient(circle_at_bottom_left,rgba(255,255,255,0.85),transparent_45%)]" />
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ACCEPTED_TYPES.join(',')}
          onChange={handleFileSelect}
          className="hidden"
        />

        <div className="relative flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
          <div className="space-y-5">
            <div className="flex items-start gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#333333] text-white shadow-sm">
                <Upload className="h-6 w-6" />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[#333333]/45">
                  Upload workspace
                </p>
                <h1 className="mt-2 text-2xl font-bold text-[#333333] lg:text-3xl">Upload</h1>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-[#333333]/60">
                  Add local image files, keep failed uploads visible, and manage the queue from the
                  same dashboard language as the rest of the app.
                </p>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-3 xl:w-[280px]">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className={cn(
                buttonBaseClass,
                primaryButtonClass,
                'h-14 justify-start px-5 text-left'
              )}
            >
              <span className="bg-white/12 flex h-10 w-10 items-center justify-center rounded-xl">
                <Upload className="h-5 w-5" />
              </span>
              <span className="flex flex-col items-start">
                <span className="text-base font-semibold">Choose files</span>
                <span className="text-xs uppercase tracking-[0.18em] text-white/70">
                  Drag and drop also works
                </span>
              </span>
            </button>

            <div className="rounded-2xl border border-dashed border-[#D8D8D8] bg-white/70 px-4 py-3 text-sm leading-6 text-[#333333]/60">
              {isDragging
                ? 'Drop files here to add them into the queue.'
                : `Accepts JPG, PNG, GIF, and WEBP. Uploads are processed in batches of ${MAX_BATCH_FILES}.`}
            </div>
          </div>
        </div>
      </motion.section>

      {notice && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {notice}
        </div>
      )}

      <div className="glass-card overflow-hidden rounded-2xl border border-[#E0E0E0]">
        <div className="border-b border-[#E0E0E0] px-5 py-5 lg:px-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-xl font-semibold text-[#333333]">Upload inbox</h2>
              <p className="mt-1 text-sm text-[#333333]/60">
                Pending files, completed uploads, and failures stay in one persistent queue.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={toggleSelectionMode}
                disabled={items.length === 0 || hasUploading}
                className={cn(
                  buttonBaseClass,
                  selectionMode ? primaryButtonClass : neutralButtonClass
                )}
              >
                {selectionMode ? 'Cancel selection' : 'Select'}
              </button>
              <button
                onClick={handleClearCompleted}
                disabled={completedCount === 0 || hasUploading}
                className={cn(buttonBaseClass, outlineButtonClass)}
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
                    'inline-flex cursor-pointer items-center rounded-full px-4 py-2 text-sm font-medium transition-colors',
                    filter === option.key
                      ? 'bg-[#333333] text-white'
                      : 'bg-[#E9E9E9] text-[#333333]/70 hover:bg-[#DDDDDD]'
                  )}
                >
                  {option.label} ({option.count})
                </button>
              ))}
            </div>

            <div className="text-sm text-[#333333]/55">
              {isHydrated ? 'Saved locally between refreshes.' : 'Restoring local queue...'}
            </div>
          </div>

          {selectionMode && (
            <div className="mt-4 flex flex-wrap items-center gap-3 rounded-2xl border border-[#E0E0E0] bg-[#F7F7F7] px-4 py-3">
              <button
                onClick={toggleSelectAllVisible}
                className="inline-flex cursor-pointer items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-[#333333] transition-colors hover:bg-white"
              >
                <span
                  className={cn(
                    'flex h-5 w-5 items-center justify-center rounded-md border-2 transition-colors',
                    allVisibleSelected
                      ? 'border-[#333333] bg-[#333333] text-white'
                      : 'border-[#333333]/30 bg-white'
                  )}
                >
                  {allVisibleSelected && <Check className="h-3.5 w-3.5" />}
                </span>
                Select visible
              </button>

              <span className="text-sm text-[#333333]/60">{selectedIds.size} selected</span>
              <span className="hidden h-4 w-px bg-[#DADADA] sm:block" />
              <span className="text-sm text-[#333333]/60">
                {selectedReadyCount} ready to upload
              </span>

              <div className="ml-auto flex flex-wrap gap-2">
                <button
                  onClick={handleUploadSelected}
                  disabled={selectedReadyCount === 0 || isUploading}
                  className={cn(buttonBaseClass, primaryButtonClass)}
                >
                  Upload selected
                </button>
                <button
                  onClick={() => removeItems(selectedIds)}
                  disabled={selectedIds.size === 0 || hasUploading}
                  className={cn(buttonBaseClass, destructiveButtonClass)}
                >
                  Remove selected
                </button>
              </div>
            </div>
          )}
        </div>

        {displayItems.length > 0 ? (
          <div className="divide-y divide-[#ECECEC]">
            <AnimatePresence initial={false}>
              {displayItems.map((item) => {
                const StatusIcon = statusIcons[item.status]
                const selected = selectedIds.has(item.id)
                const canUploadThisItem = isUploadable(item) && !isUploading

                return (
                  <motion.div
                    key={item.id}
                    layout
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    className={cn(
                      'flex flex-col gap-4 px-5 py-5 transition-colors lg:flex-row lg:items-center lg:px-6',
                      selected ? 'bg-[#F2F2F2]' : 'hover:bg-[#FAFAFA]'
                    )}
                  >
                    <div className="flex items-start gap-4 lg:flex-1">
                      {selectionMode && (
                        <button
                          onClick={() => toggleItemSelection(item.id)}
                          className={cn(
                            'mt-2 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-lg border-2 transition-colors',
                            selected
                              ? 'border-[#333333] bg-[#333333] text-white'
                              : 'border-[#333333]/30 bg-white'
                          )}
                        >
                          {selected && <Check className="h-3.5 w-3.5" />}
                        </button>
                      )}

                      <div className="relative h-14 w-14 flex-shrink-0 overflow-hidden rounded-xl border border-[#E0E0E0] bg-[#EFEFEF]">
                        {item.preview ? (
                          <img
                            src={item.preview}
                            alt={item.file_name}
                            className="h-full w-full object-cover"
                          />
                        ) : (
                          <div className="flex h-full w-full items-center justify-center">
                            <FileImage className="h-6 w-6 text-[#333333]/35" />
                          </div>
                        )}
                      </div>

                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="truncate text-base font-medium text-[#333333]">
                            {item.file_name}
                          </p>
                          {!item.file &&
                            item.status !== 'success' &&
                            item.status !== 'duplicated' && (
                              <span className="rounded-full bg-rose-50 px-2.5 py-1 text-xs font-medium text-rose-700">
                                File missing
                              </span>
                            )}
                        </div>
                        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-[#333333]/55">
                          <span>{formatFileSize(item.file_size)}</span>
                          <span>
                            {item.file_type.replace('image/', '').toUpperCase() || 'Image'}
                          </span>
                          <span>Updated {formatRelativeTime(item.updated_at)}</span>
                        </div>

                        {item.status === 'uploading' && (
                          <div className="mt-3 h-2 overflow-hidden rounded-full bg-[#E5E5E5]">
                            <motion.div
                              className="h-full rounded-full bg-[#333333]"
                              initial={{ width: 0 }}
                              animate={{ width: `${item.progress}%` }}
                              transition={{ duration: 0.25 }}
                            />
                          </div>
                        )}

                        {item.result?.error_message && item.status === 'failed' && (
                          <p className="mt-2 text-sm text-rose-600">{item.result.error_message}</p>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 lg:justify-end">
                      <div
                        className={cn(
                          'inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-medium',
                          statusStyles[item.status]
                        )}
                      >
                        <StatusIcon
                          className={cn('h-4 w-4', item.status === 'uploading' && 'animate-spin')}
                        />
                        <span>{statusLabels[item.status]}</span>
                        {item.status === 'uploading' && <span>{item.progress}%</span>}
                      </div>

                      {!selectionMode && (
                        <>
                          {canUploadThisItem && (
                            <button
                              onClick={() => void uploadItemsByIds([item.id])}
                              className={cn(buttonBaseClass, outlineButtonClass, 'px-3')}
                            >
                              Upload
                            </button>
                          )}
                          <button
                            onClick={() => removeItems([item.id])}
                            disabled={hasUploading}
                            className={cn(
                              'inline-flex cursor-pointer items-center justify-center rounded-xl p-2 text-[#333333]/45 transition-colors hover:bg-[#F2F2F2] hover:text-rose-500',
                              hasUploading && 'cursor-not-allowed opacity-35'
                            )}
                            aria-label={`Remove ${item.file_name}`}
                          >
                            <Trash2 className="h-4.5 w-4.5" />
                          </button>
                        </>
                      )}
                    </div>
                  </motion.div>
                )
              })}
            </AnimatePresence>
          </div>
        ) : (
          <div className="px-6 py-16 text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-3xl bg-[#EDEDED] text-[#333333]/35">
              <ImageIcon className="h-8 w-8" />
            </div>
            <h3 className="mt-5 text-lg font-semibold text-[#333333]">Nothing in this view</h3>
            <p className="mt-2 text-sm text-[#333333]/55">
              {items.length === 0
                ? 'Add images above to start building your persistent upload queue.'
                : 'Change the filter or add more files to populate this list.'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
