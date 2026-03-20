"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  Clock3,
  Loader2,
  PencilLine,
  Plus,
  Search,
  Trash2,
} from "lucide-react";

import { aiPromptApi, type AIPromptSummary, type ApiError } from "@/lib/api";

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}

export default function QwenPromptLibraryPage() {
  const [prompts, setPrompts] = useState<AIPromptSummary[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyPromptId, setBusyPromptId] = useState<string | null>(null);

  const fetchPrompts = useCallback(async () => {
    try {
      setLoading(true);
      const response = await aiPromptApi.listPrompts("qwen3-vl");
      setPrompts(response.data);
      setError(null);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.detail || "Failed to load prompts");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPrompts();
  }, [fetchPrompts]);

  const filteredPrompts = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    if (!keyword) return prompts;
    return prompts.filter((prompt) => {
      const haystack = [prompt.name, prompt.description ?? "", prompt.model_name]
        .join(" ")
        .toLowerCase();
      return haystack.includes(keyword);
    });
  }, [prompts, search]);

  const handleActivate = async (promptId: string) => {
    try {
      setBusyPromptId(promptId);
      await aiPromptApi.updatePrompt(promptId, { is_active: true });
      await fetchPrompts();
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.detail || "Failed to activate prompt");
    } finally {
      setBusyPromptId(null);
    }
  };

  const handleDelete = async (promptId: string) => {
    if (!confirm("Delete this prompt and all its versions? This cannot be undone.")) {
      return;
    }

    try {
      setBusyPromptId(promptId);
      await aiPromptApi.deletePrompt(promptId);
      await fetchPrompts();
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.detail || "Failed to delete prompt");
    } finally {
      setBusyPromptId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <Link
          href="/dashboard/ai-analyze/qwen3-vl"
          className="inline-flex items-center gap-2 text-sm text-[#333333]/60 transition-colors hover:text-[#333333]"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Qwen3-VL Configuration
        </Link>

        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-[#333333]">Qwen3-VL Prompts</h1>
            <p className="mt-1 max-w-2xl text-[#333333]/60">
              Manage the system and user prompts used by qwen3-vl, keep version history,
              and compare revisions before promoting them to production.
            </p>
          </div>

          <Link
            href="/dashboard/ai-analyze/qwen3-vl/prompts/new"
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#333333] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#222222]"
          >
            <Plus className="h-4 w-4" />
            New Prompt
          </Link>
        </div>
      </div>

      <div className="glass-card rounded-2xl border border-[#E0E0E0] p-4">
        <div className="relative">
          <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#333333]/45" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search prompts by name or description"
            className="w-full rounded-xl border border-[#D8D8D8] bg-white px-11 py-3 text-[#333333] outline-none transition focus:border-[#333333] focus:ring-2 focus:ring-[#333333]/10"
          />
        </div>
      </div>

      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex min-h-[320px] items-center justify-center">
          <div className="text-center">
            <Loader2 className="mx-auto h-10 w-10 animate-spin text-[#333333]" />
            <p className="mt-4 text-[#333333]/60">Loading prompts...</p>
          </div>
        </div>
      ) : filteredPrompts.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-[#D0D0D0] bg-white/70 p-10 text-center text-[#333333]/60">
          {prompts.length === 0
            ? "No prompts exist yet. Create the first qwen3-vl prompt to start versioning."
            : "No prompts match the current search."}
        </div>
      ) : (
        <div className="grid gap-4 xl:grid-cols-2">
          {filteredPrompts.map((prompt) => {
            const isBusy = busyPromptId === prompt.id;

            return (
              <div
                key={prompt.id}
                className="glass-card rounded-2xl border border-[#E0E0E0] p-5 shadow-sm"
              >
                <div className="flex flex-col gap-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <h2 className="text-xl font-semibold text-[#333333]">{prompt.name}</h2>
                        <span
                          className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${
                            prompt.is_active
                              ? "bg-green-100 text-green-700"
                              : "bg-slate-100 text-slate-600"
                          }`}
                        >
                          {prompt.is_active ? "Active" : "Inactive"}
                        </span>
                      </div>
                      <p className="text-sm text-[#333333]/60">
                        {prompt.description || "No description provided."}
                      </p>
                    </div>

                    <div className="rounded-2xl bg-[#333333]/6 px-3 py-2 text-right text-xs text-[#333333]/65">
                      <div className="font-medium uppercase tracking-wide">Current</div>
                      <div className="mt-1 text-base font-semibold text-[#333333]">
                        {prompt.current_version_number ? `v${prompt.current_version_number}` : "N/A"}
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-3 rounded-2xl bg-white/70 p-4 text-sm text-[#333333]/65 sm:grid-cols-2">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      Model: <span className="font-medium text-[#333333]">{prompt.model_name}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock3 className="h-4 w-4 text-[#333333]/45" />
                      Updated: <span className="font-medium text-[#333333]">{formatDate(prompt.updated_at)}</span>
                    </div>
                  </div>

                  <div className="flex flex-col gap-3 border-t border-[#E0E0E0] pt-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="text-sm text-[#333333]/55">
                      {prompt.is_active
                        ? "This prompt is currently injected into qwen3-vl requests."
                        : "Activate to make this prompt the runtime default."}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Link
                        prefetch={false}
                        href={`/dashboard/ai-analyze/qwen3-vl/prompts/${encodeURIComponent(prompt.id)}`}
                        className="inline-flex items-center gap-2 rounded-xl border border-[#E0E0E0] px-4 py-2 text-sm font-medium text-[#333333] transition-colors hover:bg-[#EAEAEA]"
                      >
                        <PencilLine className="h-4 w-4" />
                        Open
                      </Link>
                      {!prompt.is_active && (
                        <button
                          onClick={() => handleActivate(prompt.id)}
                          disabled={isBusy}
                          className="inline-flex items-center gap-2 rounded-xl bg-green-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {isBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                          Set Active
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(prompt.id)}
                        disabled={isBusy}
                        className="inline-flex items-center gap-2 rounded-xl border border-red-200 px-4 py-2 text-sm font-medium text-red-600 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {isBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
