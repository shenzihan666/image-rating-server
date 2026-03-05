"use client";

import { useCallback, useEffect, useState } from "react";

import { aiAnalyzeApi, AIModel } from "@/lib/api";

export default function AIAnalyzePage() {
  const [models, setModels] = useState<AIModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [switchingModel, setSwitchingModel] = useState<string | null>(null);

  const fetchModels = useCallback(async () => {
    try {
      setLoading(true);
      const response = await aiAnalyzeApi.getModels();
      setModels(response.data);
      setError(null);
    } catch (err) {
      setError("Failed to load AI models");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchModels();
  }, [fetchModels]);

  const handleToggle = async (model: AIModel) => {
    if (switchingModel) return;

    try {
      setSwitchingModel(model.name);
      if (model.is_active) {
        await aiAnalyzeApi.deactivateActiveModel();
      } else {
        await aiAnalyzeApi.setActiveModel(model.name);
      }
      await fetchModels();
    } catch (err) {
      setError("Failed to switch AI model");
      console.error(err);
    } finally {
      setSwitchingModel(null);
    }
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-lg text-muted-foreground">Loading AI models...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">AI Analyze Server</h1>
        <p className="text-muted-foreground">Manage your AI analysis models</p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          {error}
        </div>
      )}

      <div className="space-y-4">
        {models.map((model) => (
          <div
            key={model.name}
            className="rounded-lg border bg-card p-4 shadow-sm transition-shadow hover:shadow-md"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xl">
                    {model.is_active ? "\u{1F3AF}" : "\u{1F52E}"}
                  </span>
                  <h3 className="text-lg font-semibold">{model.name.toUpperCase()}</h3>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">
                  {model.description}
                </p>
                <div className="mt-2 flex items-center gap-2">
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
                      model.is_active
                        ? "bg-green-100 text-green-700"
                        : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    <span
                      className={`mr-1 h-2 w-2 rounded-full ${
                        model.is_active ? "bg-green-500" : "bg-gray-400"
                      }`}
                    />
                    {model.is_active ? "Active" : "Inactive"}
                  </span>
                  {model.is_loaded && (
                    <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700">
                      Loaded
                    </span>
                  )}
                </div>
              </div>

              <button
                onClick={() => handleToggle(model)}
                disabled={switchingModel !== null}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  model.is_active ? "bg-green-500" : "bg-gray-300"
                } ${switchingModel ? "cursor-not-allowed opacity-50" : "cursor-pointer"}`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    model.is_active ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>

            {switchingModel === model.name && (
              <div className="mt-3 text-sm text-muted-foreground">
                Updating model state...
              </div>
            )}
          </div>
        ))}

        {models.length === 0 && !loading && (
          <div className="rounded-lg border bg-card p-8 text-center text-muted-foreground">
            No AI models available
          </div>
        )}
      </div>
    </div>
  );
}
