"use client";

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  FileDiff,
  History,
  Loader2,
  Save,
  Settings2,
  Sparkles,
  X,
} from "lucide-react";

import {
  aiPromptApi,
  type AIPromptDetail,
  type AIPromptVersionDetail,
  type AIPromptVersionSummary,
  type ApiError,
} from "@/lib/api";
import { resolveRouteSegment } from "@/lib/route-params";

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}

export default function QwenPromptDetailPage() {
  const params = useParams();
  const pathname = usePathname();

  const promptId = resolveRouteSegment({
    param: params.promptId,
    pathname,
    pattern: /\/prompts\/([^/]+)\/?$/,
    reject: ["new"],
  });
  const [prompt, setPrompt] = useState<AIPromptDetail | null>(null);
  const [versions, setVersions] = useState<AIPromptVersionSummary[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isActive, setIsActive] = useState(false);
  const [systemPrompt, setSystemPrompt] = useState("");
  const [userPrompt, setUserPrompt] = useState("");
  const [commitMessage, setCommitMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [savingMeta, setSavingMeta] = useState(false);
  const [savingVersion, setSavingVersion] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showDiff, setShowDiff] = useState(false);
  const [showMetadata, setShowMetadata] = useState(false);
  const [leftVersionId, setLeftVersionId] = useState("");
  const [rightVersionId, setRightVersionId] = useState("");
  const [diffLeft, setDiffLeft] = useState<AIPromptVersionDetail | null>(null);
  const [diffRight, setDiffRight] = useState<AIPromptVersionDetail | null>(null);

  const syncPromptForm = useCallback((detail: AIPromptDetail) => {
    setPrompt(detail);
    setName(detail.name);
    setDescription(detail.description || "");
    setIsActive(detail.is_active);
    setSystemPrompt(detail.current_version?.system_prompt || "");
    setUserPrompt(detail.current_version?.user_prompt || "");
  }, []);

  const fetchPrompt = useCallback(async () => {
    if (!promptId.trim()) {
      setLoading(false);
      setPrompt(null);
      setError("Invalid or missing prompt id.");
      return;
    }
    try {
      setLoading(true);
      const [promptResponse, versionsResponse] = await Promise.all([
        aiPromptApi.getPrompt(promptId),
        aiPromptApi.listPromptVersions(promptId),
      ]);

      syncPromptForm(promptResponse.data);
      setVersions(versionsResponse.data);
      if (versionsResponse.data.length > 0) {
        setRightVersionId((current) => current || versionsResponse.data[0].id);
        setLeftVersionId((current) =>
          current || versionsResponse.data[Math.min(1, versionsResponse.data.length - 1)].id
        );
      }
      setError(null);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.detail || "Failed to load prompt");
    } finally {
      setLoading(false);
    }
  }, [promptId, syncPromptForm]);

  useEffect(() => {
    fetchPrompt();
  }, [fetchPrompt]);

  const versionsById = useMemo(
    () => Object.fromEntries(versions.map((version) => [version.id, version] as const)),
    [versions]
  );

  useEffect(() => {
    let cancelled = false;

    async function loadDiffVersions() {
      if (!showDiff || !leftVersionId || !rightVersionId) {
        return;
      }

      try {
        const [leftResponse, rightResponse] = await Promise.all([
          aiPromptApi.getPromptVersion(promptId, leftVersionId),
          aiPromptApi.getPromptVersion(promptId, rightVersionId),
        ]);
        if (!cancelled) {
          setDiffLeft(leftResponse.data);
          setDiffRight(rightResponse.data);
        }
      } catch {
        if (!cancelled) {
          setDiffLeft(null);
          setDiffRight(null);
        }
      }
    }

    loadDiffVersions();

    return () => {
      cancelled = true;
    };
  }, [leftVersionId, promptId, rightVersionId, showDiff]);

  const handleSaveMeta = async (): Promise<boolean> => {
    if (!prompt) return false;

    try {
      setSavingMeta(true);
      const response = await aiPromptApi.updatePrompt(prompt.id, {
        name: name.trim(),
        description: description.trim() || null,
        is_active: isActive,
      });
      setPrompt(response.data);
      setName(response.data.name);
      setDescription(response.data.description || "");
      setIsActive(response.data.is_active);
      setSuccess("Prompt metadata saved.");
      setError(null);
      return true;
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.detail || "Failed to save prompt metadata");
      setSuccess(null);
      return false;
    } finally {
      setSavingMeta(false);
    }
  };

  const handleSaveVersion = async () => {
    if (!prompt) return;
    if (!commitMessage.trim()) {
      setError("Commit message is required when saving a new version.");
      return;
    }
    if (!systemPrompt.trim() || !userPrompt.trim()) {
      setError("System prompt and user prompt cannot be empty.");
      return;
    }

    try {
      setSavingVersion(true);
      await aiPromptApi.createPromptVersion(prompt.id, {
        system_prompt: systemPrompt.trim(),
        user_prompt: userPrompt.trim(),
        commit_message: commitMessage.trim(),
        created_by: "dashboard",
      });
      setCommitMessage("");
      setSuccess("New prompt version saved.");
      await fetchPrompt();
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.detail || "Failed to save prompt version");
      setSuccess(null);
    } finally {
      setSavingVersion(false);
    }
  };

  const handleLoadVersionIntoEditor = async (versionId: string) => {
    try {
      const response = await aiPromptApi.getPromptVersion(promptId, versionId);
      setSystemPrompt(response.data.system_prompt);
      setUserPrompt(response.data.user_prompt);
      setSuccess(`Loaded v${response.data.version_number} into the editor.`);
      setError(null);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.detail || "Failed to load prompt version");
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[320px] items-center justify-center">
        <div className="text-center">
          <Loader2 className="mx-auto h-10 w-10 animate-spin text-[#333333]" />
          <p className="mt-4 text-[#333333]/60">Loading prompt...</p>
        </div>
      </div>
    );
  }

  if (!prompt) {
    return (
      <div className="space-y-4">
        <Link
          href="/dashboard/ai-analyze/qwen3-vl/prompts"
          className="inline-flex items-center gap-2 text-sm text-[#333333]/60 transition-colors hover:text-[#333333]"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Prompt Library
        </Link>
        <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-red-700">
          {error || "Prompt not found"}
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-6">
        <div className="space-y-3">
          <Link
            href="/dashboard/ai-analyze/qwen3-vl/prompts"
            className="inline-flex items-center gap-2 text-sm text-[#333333]/60 transition-colors hover:text-[#333333]"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Prompt Library
          </Link>

          <section className="overflow-hidden rounded-[28px] border border-[#E3DDD4] bg-[radial-gradient(circle_at_top_left,_rgba(255,255,255,0.96),_rgba(248,242,233,0.92)_42%,_rgba(243,237,229,0.9)_100%)] shadow-[0_20px_60px_rgba(57,45,31,0.08)]">
            <div className="flex flex-col gap-6 px-6 py-6 lg:flex-row lg:items-end lg:justify-between lg:px-8">
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-3">
                  <h1 className="text-3xl font-bold tracking-tight text-[#2D2A26] sm:text-4xl">
                    {prompt.name}
                  </h1>
                  <span
                    className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
                      prompt.is_active
                        ? "bg-green-100 text-green-700"
                        : "bg-[#E9E2D7] text-[#6A5F52]"
                    }`}
                  >
                    {prompt.is_active ? "Active" : "Inactive"}
                  </span>
                  <span className="inline-flex items-center rounded-full bg-[#2D2A26]/7 px-3 py-1 text-xs font-semibold text-[#4B4339]">
                    {prompt.current_version_number
                      ? `v${prompt.current_version_number}`
                      : "No version"}
                  </span>
                </div>
                <p className="max-w-3xl text-sm leading-6 text-[#5D574D] sm:text-base">
                  The editor is optimized for prompt writing first. Metadata is separated into
                  a floating panel so the system and user prompts can occupy the page.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <button
                  onClick={() => setShowMetadata(true)}
                  className="inline-flex items-center justify-center gap-2 rounded-2xl border border-[#D8D1C6] bg-white/80 px-4 py-2.5 text-sm font-medium text-[#2D2A26] transition hover:border-[#B7ADA0] hover:bg-white"
                >
                  <Settings2 className="h-4 w-4" />
                  Metadata
                </button>
                <button
                  onClick={() => setShowDiff(true)}
                  disabled={versions.length === 0}
                  className="inline-flex items-center justify-center gap-2 rounded-2xl border border-[#D8D1C6] bg-white/80 px-4 py-2.5 text-sm font-medium text-[#2D2A26] transition hover:border-[#B7ADA0] hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <FileDiff className="h-4 w-4" />
                  Compare Versions
                </button>
                <button
                  onClick={handleSaveVersion}
                  disabled={savingVersion}
                  className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[#2D2A26] px-5 py-2.5 text-sm font-medium text-white transition hover:bg-[#1F1C18] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {savingVersion ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4" />
                  )}
                  Save New Version
                </button>
              </div>
            </div>
          </section>
        </div>

        {error && (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {success && (
          <div className="rounded-2xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
            {success}
          </div>
        )}

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.75fr)_340px]">
          <section className="glass-card rounded-[28px] border border-[#E3DDD4] bg-white/88 p-6 shadow-[0_18px_50px_rgba(57,45,31,0.06)] lg:p-8">
            <div className="space-y-6">
              <div className="rounded-3xl border border-[#ECE6DC] bg-[#FCFAF6] p-5">
                <div className="mb-3 flex items-center justify-between gap-4">
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[#8C7B66]">
                      Commit Message
                    </div>
                    <p className="mt-1 text-sm text-[#6B6257]">
                      Every save creates a new immutable version in the history rail.
                    </p>
                  </div>
                  <div className="rounded-full bg-[#EFE8DE] px-3 py-1 text-xs font-semibold text-[#6B6257]">
                    {versions.length} version{versions.length === 1 ? "" : "s"}
                  </div>
                </div>
                <input
                  value={commitMessage}
                  onChange={(event) => setCommitMessage(event.target.value)}
                  placeholder="What changed in this revision?"
                  className="w-full rounded-2xl border border-[#D8D1C6] bg-white px-4 py-3 text-[#2D2A26] outline-none transition focus:border-[#7A6C59] focus:ring-2 focus:ring-[#7A6C59]/10"
                />
              </div>

              <PromptEditorBlock
                label="System Prompt"
                helper="Keeps the model aligned to response format, safety, and scoring behavior."
                value={systemPrompt}
                onChange={setSystemPrompt}
                rows={13}
              />

              <PromptEditorBlock
                label="User Prompt"
                helper="Primary instruction body. Supported placeholders: {{image_name}}, {{mime_type}}, {{model_name}}."
                value={userPrompt}
                onChange={setUserPrompt}
                rows={20}
              />
            </div>
          </section>

          <aside className="xl:sticky xl:top-8 xl:self-start">
            <div className="glass-card rounded-[28px] border border-[#E3DDD4] bg-white/88 p-5 shadow-[0_18px_50px_rgba(57,45,31,0.06)]">
              <div className="flex items-start gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#2D2A26]/7">
                  <History className="h-5 w-5 text-[#5A5146]" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-[#2D2A26]">Version History</h2>
                  <p className="mt-1 text-sm leading-6 text-[#6B6257]">
                    Vertical revision rail. Click any version to load it into the editor.
                  </p>
                </div>
              </div>

              <div className="mt-5 space-y-3">
                {versions.map((version) => {
                  const isCurrent = version.id === prompt.current_version_id;
                  return (
                    <button
                      key={version.id}
                      onClick={() => handleLoadVersionIntoEditor(version.id)}
                      className={`w-full rounded-2xl border px-4 py-4 text-left transition ${
                        isCurrent
                          ? "border-[#BFAE96] bg-[linear-gradient(145deg,#fffaf1,#f4ecdd)] shadow-[0_12px_30px_rgba(76,59,35,0.08)]"
                          : "border-[#E5DED2] bg-white/80 hover:border-[#B7ADA0] hover:bg-white"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <div className="text-sm font-semibold text-[#2D2A26]">
                              v{version.version_number}
                            </div>
                            {isCurrent && (
                              <span className="rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-green-700">
                                Live
                              </span>
                            )}
                          </div>
                          <div className="text-sm leading-6 text-[#61584D]">
                            {version.commit_message || "No commit message"}
                          </div>
                        </div>
                        <div className="text-right text-[11px] leading-5 text-[#8A8174]">
                          <div>{formatDate(version.created_at)}</div>
                          <div>{version.created_by || "Unknown author"}</div>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </aside>
        </div>
      </div>

      {showMetadata && (
        <div className="fixed inset-0 z-50 bg-[#0F0D0B]/45 p-4 backdrop-blur-sm">
          <div className="mx-auto flex h-full max-w-2xl items-center justify-center">
            <div className="w-full rounded-[30px] border border-[#DED5C8] bg-[linear-gradient(145deg,#fffdfa,#f6f1e8)] shadow-[0_30px_90px_rgba(26,18,9,0.18)]">
              <div className="flex items-start justify-between gap-4 border-b border-[#E6DED3] px-6 py-5">
                <div>
                  <h2 className="text-2xl font-bold text-[#2D2A26]">Prompt Metadata</h2>
                  <p className="mt-1 text-sm leading-6 text-[#655D52]">
                    Edit the prompt name, description, and active status without taking editor
                    space away from the prompt text.
                  </p>
                </div>
                <button
                  onClick={() => setShowMetadata(false)}
                  className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-[#DDD3C4] bg-white/75 text-[#4F473D] transition hover:bg-white"
                  aria-label="Close metadata dialog"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="space-y-5 px-6 py-6">
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-[#2D2A26]">Name</label>
                  <input
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    className="w-full rounded-2xl border border-[#D8D1C6] bg-white px-4 py-3 text-[#2D2A26] outline-none transition focus:border-[#7A6C59] focus:ring-2 focus:ring-[#7A6C59]/10"
                  />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-[#2D2A26]">Description</label>
                  <textarea
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                    rows={5}
                    className="w-full rounded-2xl border border-[#D8D1C6] bg-white px-4 py-3 text-[#2D2A26] outline-none transition focus:border-[#7A6C59] focus:ring-2 focus:ring-[#7A6C59]/10"
                  />
                </div>
                <label className="flex items-center gap-3 rounded-2xl border border-[#E3DDD4] bg-white/80 px-4 py-4 text-sm text-[#2D2A26]">
                  <input
                    type="checkbox"
                    checked={isActive}
                    onChange={(event) => setIsActive(event.target.checked)}
                    className="h-4 w-4 rounded border-[#C8C0B4] text-[#2D2A26] focus:ring-[#2D2A26]/20"
                  />
                  Use this prompt as the active qwen3-vl runtime prompt
                </label>
              </div>

              <div className="flex flex-col gap-3 border-t border-[#E6DED3] px-6 py-5 sm:flex-row sm:items-center sm:justify-end">
                <button
                  onClick={() => setShowMetadata(false)}
                  className="rounded-2xl border border-[#D8D1C6] bg-white/80 px-4 py-2.5 text-sm font-medium text-[#2D2A26] transition hover:bg-white"
                >
                  Cancel
                </button>
                <button
                  onClick={async () => {
                    const saved = await handleSaveMeta();
                    if (saved) {
                      setShowMetadata(false);
                    }
                  }}
                  disabled={savingMeta}
                  className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[#2D2A26] px-5 py-2.5 text-sm font-medium text-white transition hover:bg-[#1F1C18] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {savingMeta ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="h-4 w-4" />
                  )}
                  Save Metadata
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showDiff && (
        <div className="fixed inset-0 z-50 bg-[#111111]/55 p-4 backdrop-blur-sm">
          <div className="mx-auto flex h-full max-w-7xl flex-col rounded-[28px] bg-[#F6F4EF] shadow-2xl">
            <div className="flex flex-col gap-4 border-b border-[#E0E0E0] px-6 py-5 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <h2 className="text-2xl font-bold text-[#333333]">Compare Versions</h2>
                <p className="mt-1 text-sm text-[#333333]/60">
                  Choose any two saved versions and compare their prompt text side by side.
                </p>
              </div>
              <button
                onClick={() => setShowDiff(false)}
                className="rounded-xl border border-[#E0E0E0] px-4 py-2 text-sm font-medium text-[#333333] transition hover:bg-white"
              >
                Close
              </button>
            </div>

            <div className="grid gap-4 px-6 py-5 lg:grid-cols-2">
              <div className="space-y-2">
                <label className="block text-sm font-medium text-[#333333]">Original</label>
                <select
                  value={leftVersionId}
                  onChange={(event) => setLeftVersionId(event.target.value)}
                  className="w-full rounded-xl border border-[#D8D8D8] bg-white px-4 py-3 text-[#333333] outline-none transition focus:border-[#333333] focus:ring-2 focus:ring-[#333333]/10"
                >
                  {versions.map((version) => (
                    <option key={version.id} value={version.id}>
                      v{version.version_number} · {version.commit_message || "No message"}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <label className="block text-sm font-medium text-[#333333]">Modified</label>
                <select
                  value={rightVersionId}
                  onChange={(event) => setRightVersionId(event.target.value)}
                  className="w-full rounded-xl border border-[#D8D8D8] bg-white px-4 py-3 text-[#333333] outline-none transition focus:border-[#333333] focus:ring-2 focus:ring-[#333333]/10"
                >
                  {versions.map((version) => (
                    <option key={version.id} value={version.id}>
                      v{version.version_number} · {version.commit_message || "No message"}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid flex-1 gap-6 overflow-hidden px-6 pb-6 lg:grid-cols-2">
              <DiffColumn
                label={
                  diffLeft
                    ? `Original · v${diffLeft.version_number}`
                    : `Original · ${versionsById[leftVersionId]?.version_number ?? ""}`
                }
                subtitle={diffLeft?.commit_message || "Select a version"}
                systemPrompt={diffLeft?.system_prompt || ""}
                userPrompt={diffLeft?.user_prompt || ""}
              />
              <DiffColumn
                label={
                  diffRight
                    ? `Modified · v${diffRight.version_number}`
                    : `Modified · ${versionsById[rightVersionId]?.version_number ?? ""}`
                }
                subtitle={diffRight?.commit_message || "Select a version"}
                systemPrompt={diffRight?.system_prompt || ""}
                userPrompt={diffRight?.user_prompt || ""}
              />
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function PromptEditorBlock({
  label,
  helper,
  value,
  onChange,
  rows,
}: {
  label: string;
  helper: string;
  value: string;
  onChange: (_value: string) => void;
  rows: number;
}) {
  return (
    <section className="rounded-[28px] border border-[#ECE6DC] bg-[linear-gradient(180deg,#fdfbf7,#f7f1e8)] p-5">
      <div className="mb-4 flex flex-col gap-1">
        <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[#8C7B66]">
          {label}
        </div>
        <p className="text-sm leading-6 text-[#655D52]">{helper}</p>
      </div>

      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        rows={rows}
        className="w-full rounded-[24px] border border-[#D6CCBE] bg-[#0E0E10] px-5 py-5 font-mono text-sm leading-6 text-[#F6F6F6] outline-none transition focus:border-[#A6937A] focus:ring-2 focus:ring-[#A6937A]/15"
      />
    </section>
  );
}

function DiffColumn({
  label,
  subtitle,
  systemPrompt,
  userPrompt,
}: {
  label: string;
  subtitle: string;
  systemPrompt: string;
  userPrompt: string;
}) {
  return (
    <div className="flex min-h-0 flex-col rounded-[24px] border border-[#D8D8D8] bg-white">
      <div className="border-b border-[#EAE7E0] px-5 py-4">
        <div className="text-sm font-semibold text-[#333333]">{label}</div>
        <div className="mt-1 text-xs text-[#333333]/50">{subtitle}</div>
      </div>
      <div className="grid min-h-0 flex-1 gap-4 overflow-auto p-5">
        <div>
          <div className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-[#333333]/45">
            System Prompt
          </div>
          <textarea
            readOnly
            value={systemPrompt}
            className="h-[240px] w-full rounded-2xl border border-[#E0E0E0] bg-[#121212] px-4 py-4 font-mono text-sm text-[#F5F5F5] outline-none"
          />
        </div>
        <div>
          <div className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-[#333333]/45">
            User Prompt
          </div>
          <textarea
            readOnly
            value={userPrompt}
            className="h-[320px] w-full rounded-2xl border border-[#E0E0E0] bg-[#121212] px-4 py-4 font-mono text-sm text-[#F5F5F5] outline-none"
          />
        </div>
      </div>
    </div>
  );
}
