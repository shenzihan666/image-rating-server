"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Loader2, Save, ShieldCheck } from "lucide-react";

import {
  aiAnalyzeApi,
  type AIModelConfigField,
  type AIModelDetail,
  type ApiError,
} from "@/lib/api";

function formatModelLabel(name: string): string {
  return name
    .split("-")
    .map((part) => (part ? part.toUpperCase() : part))
    .join(" ");
}

export function AIModelConfigPageContent({ modelName }: { modelName: string }) {
  const [model, setModel] = useState<AIModelDetail | null>(null);
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const secretFieldSet = useMemo(
    () => new Set(model?.configured_secret_fields ?? []),
    [model?.configured_secret_fields]
  );

  const syncFormValues = useCallback((detail: AIModelDetail) => {
    const nextValues: Record<string, string> = {};
    detail.config_fields.forEach((field) => {
      nextValues[field.key] = detail.config[field.key] ?? "";
    });
    setFormValues(nextValues);
  }, []);

  const fetchModel = useCallback(async () => {
    if (!modelName.trim()) {
      setLoading(false);
      setError("Missing model name in route.");
      return;
    }
    try {
      setLoading(true);
      const response = await aiAnalyzeApi.getModel(modelName);
      setModel(response.data);
      syncFormValues(response.data);
      setError(null);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.detail || "Failed to load model configuration");
    } finally {
      setLoading(false);
    }
  }, [modelName, syncFormValues]);

  useEffect(() => {
    fetchModel();
  }, [fetchModel]);

  const handleChange = (field: string, value: string) => {
    setFormValues((current) => ({
      ...current,
      [field]: value,
    }));
    if (success) {
      setSuccess(null);
    }
  };

  const handleSave = async () => {
    if (!model) return;

    try {
      setSaving(true);
      const response = await aiAnalyzeApi.updateModelConfig(model.name, formValues);
      setModel(response.data);
      syncFormValues(response.data);
      setSuccess("Configuration saved");
      setError(null);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.detail || "Failed to save model configuration");
      setSuccess(null);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[320px] items-center justify-center">
        <div className="text-center">
          <Loader2 className="mx-auto h-10 w-10 animate-spin text-[#333333]" />
          <p className="mt-4 text-[#333333]/60">Loading configuration...</p>
        </div>
      </div>
    );
  }

  if (error && !model) {
    return (
      <div className="space-y-4">
        <Link
          href="/dashboard/ai-analyze"
          className="inline-flex items-center gap-2 text-sm text-[#333333]/60 transition-colors hover:text-[#333333]"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to AI Analyze Server
        </Link>
        <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-red-700">
          {error}
        </div>
      </div>
    );
  }

  if (!model) {
    return (
      <div className="space-y-4">
        <Link
          href="/dashboard/ai-analyze"
          className="inline-flex items-center gap-2 text-sm text-[#333333]/60 transition-colors hover:text-[#333333]"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to AI Analyze Server
        </Link>
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-amber-900">
          No configuration was returned for this model. Try again or go back to the model list.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <Link
          href="/dashboard/ai-analyze"
          className="inline-flex items-center gap-2 text-sm text-[#333333]/60 transition-colors hover:text-[#333333]"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to AI Analyze Server
        </Link>

        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-[#333333]">
              {formatModelLabel(model.name)}
            </h1>
            <p className="mt-1 text-[#333333]/60">{model.description}</p>
          </div>

          <div className="flex flex-wrap gap-2">
            <span
              className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${
                model.configured
                  ? "bg-blue-100 text-blue-700"
                  : "bg-amber-100 text-amber-700"
              }`}
            >
              {model.configured ? "Configured" : "Needs Config"}
            </span>
            <span
              className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${
                model.is_active
                  ? "bg-green-100 text-green-700"
                  : "bg-slate-100 text-slate-600"
              }`}
            >
              {model.is_active ? "Active" : "Inactive"}
            </span>
          </div>
        </div>
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

      <div className="glass-card rounded-2xl border border-[#E0E0E0] p-6">
        <div className="mb-6 flex items-start gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#333333]/8">
            <ShieldCheck className="h-5 w-5 text-[#333333]" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-[#333333]">
              Runtime Configuration
            </h2>
            <p className="mt-1 text-sm text-[#333333]/60">
              Manage provider credentials, endpoint defaults, and keep prompt content
              versioned separately from runtime secrets.
            </p>
          </div>
        </div>

        <div className="space-y-5">
          {model.config_fields.map((field: AIModelConfigField) => {
            const isSecretConfigured = field.secret && secretFieldSet.has(field.key);
            const placeholder = isSecretConfigured
              ? "Already saved. Leave blank to keep current value."
              : field.placeholder || "";

            return (
              <div key={field.key} className="space-y-2">
                <label
                  htmlFor={field.key}
                  className="block text-sm font-medium text-[#333333]"
                >
                  {field.label}
                  {field.required && <span className="ml-1 text-red-500">*</span>}
                </label>
                <input
                  id={field.key}
                  type={field.field_type}
                  value={formValues[field.key] ?? ""}
                  onChange={(event) => handleChange(field.key, event.target.value)}
                  placeholder={placeholder}
                  autoComplete="off"
                  className="w-full rounded-xl border border-[#D8D8D8] bg-white px-4 py-3 text-[#333333] outline-none transition focus:border-[#333333] focus:ring-2 focus:ring-[#333333]/10"
                />
                {field.help_text && (
                  <p className="text-sm text-[#333333]/55">{field.help_text}</p>
                )}
              </div>
            );
          })}

          {model.config_fields.length === 0 && (
            <div className="rounded-2xl border border-dashed border-[#D0D0D0] bg-white/60 p-5 text-sm text-[#333333]/60">
              This model does not expose any editable runtime configuration.
            </div>
          )}
        </div>

        <div className="mt-8 flex flex-col gap-3 border-t border-[#E0E0E0] pt-5 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-[#333333]/55">
            Secret fields are not sent back to the browser after they are saved.
          </p>
          <div className="flex flex-col gap-3 sm:flex-row">
            <button
              onClick={handleSave}
              disabled={saving}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#333333] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#222222] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  Save Configuration
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
