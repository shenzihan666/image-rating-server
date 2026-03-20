import type { UploadListItem, UploadResult } from "@/types";

const META_KEY = "uploadInboxMeta";
const DB_NAME = "image-rating-upload-db";
const STORE_NAME = "upload-files";
const DB_VERSION = 1;

interface StoredUploadMeta {
  id: string;
  file_name: string;
  file_size: number;
  file_type: string;
  status: UploadListItem["status"];
  progress: number;
  result?: UploadResult;
  created_at: string;
  updated_at: string;
}

interface StoredFileRecord {
  id: string;
  blob: Blob;
  name: string;
  type: string;
  lastModified: number;
}

function promisifyRequest<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("IndexedDB request failed"));
  });
}

function promisifyTransaction(transaction: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error ?? new Error("IndexedDB transaction failed"));
    transaction.onabort = () => reject(transaction.error ?? new Error("IndexedDB transaction aborted"));
  });
}

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "id" });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("Failed to open upload database"));
  });
}

function parseStoredMeta(): StoredUploadMeta[] {
  if (typeof window === "undefined") {
    return [];
  }

  const raw = localStorage.getItem(META_KEY);
  if (!raw) {
    return [];
  }

  try {
    return JSON.parse(raw) as StoredUploadMeta[];
  } catch {
    localStorage.removeItem(META_KEY);
    return [];
  }
}

function toFile(record?: StoredFileRecord): File | undefined {
  if (!record) {
    return undefined;
  }

  return new File([record.blob], record.name, {
    type: record.type,
    lastModified: record.lastModified,
  });
}

export async function loadUploadInbox(): Promise<UploadListItem[]> {
  if (typeof window === "undefined" || typeof indexedDB === "undefined") {
    return [];
  }

  const metaItems = parseStoredMeta();
  if (metaItems.length === 0) {
    return [];
  }

  const db = await openDatabase();
  try {
    const transaction = db.transaction(STORE_NAME, "readonly");
    const store = transaction.objectStore(STORE_NAME);
    const records = await promisifyRequest(store.getAll() as IDBRequest<StoredFileRecord[]>);
    await promisifyTransaction(transaction);

    const fileMap = new Map(records.map((record) => [record.id, record]));

    return metaItems.map((item) => {
      const file = toFile(fileMap.get(item.id));
      const restoredStatus = item.status === "uploading" ? "pending" : item.status;
      const missingPendingFile = !file && (restoredStatus === "pending" || restoredStatus === "failed");

      return {
        ...item,
        status: missingPendingFile ? "failed" : restoredStatus,
        progress: restoredStatus === "pending" ? 0 : item.progress,
        result: missingPendingFile
          ? {
              status: "failed",
              original_filename: item.file_name,
              error_message: "File data is unavailable after refresh. Please add it again.",
              is_duplicate: false,
            }
          : item.result,
        file,
      };
    });
  } finally {
    db.close();
  }
}

export async function saveUploadInbox(items: UploadListItem[]): Promise<void> {
  if (typeof window === "undefined" || typeof indexedDB === "undefined") {
    return;
  }

  const metaItems: StoredUploadMeta[] = items.map(
    ({ file: _file, preview: _preview, ...item }) => item
  );
  localStorage.setItem(META_KEY, JSON.stringify(metaItems));

  const db = await openDatabase();
  try {
    const existingTransaction = db.transaction(STORE_NAME, "readonly");
    const existingStore = existingTransaction.objectStore(STORE_NAME);
    const existingKeys = await promisifyRequest(existingStore.getAllKeys() as IDBRequest<IDBValidKey[]>);
    await promisifyTransaction(existingTransaction);

    const activeIds = new Set(items.map((item) => item.id));
    const existingIdSet = new Set(existingKeys.map((key) => String(key)));
    const writeTransaction = db.transaction(STORE_NAME, "readwrite");
    const writeStore = writeTransaction.objectStore(STORE_NAME);

    items.forEach((item) => {
      if (!item.file || existingIdSet.has(item.id)) {
        return;
      }

      writeStore.put({
        id: item.id,
        blob: item.file,
        name: item.file_name,
        type: item.file_type,
        lastModified: item.file.lastModified,
      } satisfies StoredFileRecord);
    });

    existingKeys.forEach((key) => {
      const id = String(key);
      if (!activeIds.has(id)) {
        writeStore.delete(id);
      }
    });

    await promisifyTransaction(writeTransaction);
  } finally {
    db.close();
  }
}

export async function clearUploadInboxStorage(): Promise<void> {
  if (typeof window === "undefined") {
    return;
  }

  localStorage.removeItem(META_KEY);

  if (typeof indexedDB === "undefined") {
    return;
  }

  const db = await openDatabase();
  try {
    const transaction = db.transaction(STORE_NAME, "readwrite");
    transaction.objectStore(STORE_NAME).clear();
    await promisifyTransaction(transaction);
  } finally {
    db.close();
  }
}

