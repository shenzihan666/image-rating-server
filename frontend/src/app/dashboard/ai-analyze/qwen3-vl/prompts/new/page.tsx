"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowLeft, Loader2, Save } from "lucide-react";

import { aiPromptApi, type ApiError } from "@/lib/api";

export default function NewQwenPromptPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [userPrompt, setUserPrompt] = useState("");
  const [commitMessage, setCommitMessage] = useState("Initial prompt");
  const [isActive, setIsActive] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!name.trim() || !systemPrompt.trim() || !userPrompt.trim()) {
      setError("Name, system prompt, and user prompt are required.");
      return;
    }

    try {
      setSaving(true);
      const response = await aiPromptApi.createPrompt({
        model_name: "qwen3-vl",
        name: name.trim(),
        description: description.trim() || null,
        is_active: isActive,
        system_prompt: systemPrompt.trim(),
        user_prompt: userPrompt.trim(),
        commit_message: commitMessage.trim() || null,
        created_by: "dashboard",
      });
      router.push(
        `/dashboard/ai-analyze/qwen3-vl/prompts/${encodeURIComponent(response.data.id)}`
      );
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.detail || "Failed to create prompt");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <Link
          href="/dashboard/ai-analyze/qwen3-vl/prompts"
          className="inline-flex items-center gap-2 text-sm text-[#333333]/60 transition-colors hover:text-[#333333]"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Prompt Library
        </Link>

        <div>
          <h1 className="text-3xl font-bold text-[#333333]">Create Qwen3-VL Prompt</h1>
          <p className="mt-1 max-w-2xl text-[#333333]/60">
            Start a new prompt track with an initial system prompt, user prompt, and
            commit message. The first saved version becomes v1.
          </p>
        </div>
      </div>

      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.45fr]">
        <div className="glass-card rounded-2xl border border-[#E0E0E0] p-6">
          <h2 className="text-lg font-semibold text-[#333333]">Prompt Metadata</h2>
          <div className="mt-5 space-y-4">
            <div className="space-y-2">
              <label className="block text-sm font-medium text-[#333333]">Name</label>
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="e.g. Editorial Visual Scoring"
                className="w-full rounded-xl border border-[#D8D8D8] bg-white px-4 py-3 text-[#333333] outline-none transition focus:border-[#333333] focus:ring-2 focus:ring-[#333333]/10"
              />
            </div>
            <div className="space-y-2">
              <label className="block text-sm font-medium text-[#333333]">Description</label>
              <textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                rows={4}
                placeholder="What makes this prompt different from the others?"
                className="w-full rounded-xl border border-[#D8D8D8] bg-white px-4 py-3 text-[#333333] outline-none transition focus:border-[#333333] focus:ring-2 focus:ring-[#333333]/10"
              />
            </div>
            <div className="space-y-2">
              <label className="block text-sm font-medium text-[#333333]">Initial Commit Message</label>
              <input
                value={commitMessage}
                onChange={(event) => setCommitMessage(event.target.value)}
                placeholder="What changed in this version?"
                className="w-full rounded-xl border border-[#D8D8D8] bg-white px-4 py-3 text-[#333333] outline-none transition focus:border-[#333333] focus:ring-2 focus:ring-[#333333]/10"
              />
            </div>
            <label className="flex items-center gap-3 rounded-2xl border border-[#E0E0E0] bg-white/80 px-4 py-3 text-sm text-[#333333]">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(event) => setIsActive(event.target.checked)}
                className="h-4 w-4 rounded border-[#C8C8C8] text-[#333333] focus:ring-[#333333]/20"
              />
              Set this prompt active after creation
            </label>
          </div>
        </div>

        <div className="glass-card rounded-2xl border border-[#E0E0E0] p-6">
          <div className="grid gap-5">
            <div className="space-y-2">
              <label className="block text-sm font-medium text-[#333333]">System Prompt</label>
              <textarea
                value={systemPrompt}
                onChange={(event) => setSystemPrompt(event.target.value)}
                rows={10}
                placeholder="You are a professional image analysis assistant..."
                className="w-full rounded-2xl border border-[#D8D8D8] bg-[#121212] px-4 py-4 font-mono text-sm text-[#F5F5F5] outline-none transition focus:border-[#333333] focus:ring-2 focus:ring-[#333333]/10"
              />
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-medium text-[#333333]">User Prompt</label>
              <textarea
                value={userPrompt}
                onChange={(event) => setUserPrompt(event.target.value)}
                rows={14}
                placeholder="Analyze {{image_name}} ..."
                className="w-full rounded-2xl border border-[#D8D8D8] bg-[#121212] px-4 py-4 font-mono text-sm text-[#F5F5F5] outline-none transition focus:border-[#333333] focus:ring-2 focus:ring-[#333333]/10"
              />
              <p className="text-sm text-[#333333]/55">
                Supported placeholders: <code>{"{{image_name}}"}</code>, <code>{"{{mime_type}}"}</code>,{" "}
                <code>{"{{model_name}}"}</code>
              </p>
            </div>
          </div>

          <div className="mt-8 flex items-center justify-end">
            <button
              onClick={handleCreate}
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-xl bg-[#333333] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#222222] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              Create Prompt
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
