'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { ArrowRight, Bot, Loader2, Settings2 } from 'lucide-react'

import {
  aiAnalyzeApi,
  type AIModel,
  type AIModelConnectionTestResponse,
  type ApiError,
} from '@/lib/api'
import { cn } from '@/lib/utils'

function formatModelLabel(modelName: string): string {
  return modelName
    .split('-')
    .map((part) => (part ? part.toUpperCase() : part))
    .join(' ')
}

export default function AIAnalyzePage() {
  const [models, setModels] = useState<AIModel[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [switchingModel, setSwitchingModel] = useState<string | null>(null)
  const [testingModel, setTestingModel] = useState<string | null>(null)
  const [connectionResults, setConnectionResults] = useState<
    Record<string, AIModelConnectionTestResponse>
  >({})

  const fetchModels = useCallback(async () => {
    try {
      setLoading(true)
      const response = await aiAnalyzeApi.getModels()
      setModels(response.data)
      setError(null)
    } catch (err) {
      const apiError = err as ApiError
      setError(apiError.detail || 'Failed to load AI models')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchModels()
  }, [fetchModels])

  const handleToggle = async (model: AIModel) => {
    if (switchingModel) return

    try {
      setSwitchingModel(model.name)
      if (model.is_active) {
        await aiAnalyzeApi.deactivateActiveModel()
      } else {
        await aiAnalyzeApi.setActiveModel(model.name)
      }
      await fetchModels()
    } catch (err) {
      const apiError = err as ApiError
      setError(apiError.detail || 'Failed to switch AI model')
    } finally {
      setSwitchingModel(null)
    }
  }

  const handleTestConnection = async (model: AIModel) => {
    if (testingModel) return

    try {
      setTestingModel(model.name)
      const response = await aiAnalyzeApi.testConnection(model.name)
      setConnectionResults((current) => ({
        ...current,
        [model.name]: response.data,
      }))
    } catch (err) {
      const apiError = err as ApiError
      setConnectionResults((current) => ({
        ...current,
        [model.name]: {
          ok: false,
          status: 'request_failed',
          message: apiError.detail || 'Connection test failed',
          details: {},
        },
      }))
    } finally {
      setTestingModel(null)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[320px] items-center justify-center">
        <div className="text-center">
          <Loader2 className="mx-auto h-10 w-10 animate-spin text-[#333333]" />
          <p className="mt-4 text-[#333333]/60">Loading AI models...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-[#333333]">AI Analyze Server</h1>
          <p className="mt-1 text-[#333333]/60">
            Switch between local and remote analyzers, and configure pluggable providers like
            Qwen3-VL.
          </p>
        </div>
        <div className="inline-flex items-center gap-2 rounded-full border border-[#E0E0E0] bg-white/70 px-4 py-2 text-sm text-[#333333]/70">
          <Bot className="h-4 w-4" />
          {models.length} model{models.length === 1 ? '' : 's'}
        </div>
      </div>

      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-2">
        {models.map((model) => {
          const isBusy = switchingModel === model.name
          const isTesting = testingModel === model.name
          const connectionResult = connectionResults[model.name]

          return (
            <div
              key={model.name}
              className="glass-card rounded-2xl border border-[#E0E0E0] p-5 shadow-sm"
            >
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="bg-[#333333]/8 flex h-12 w-12 items-center justify-center rounded-2xl">
                      <Bot className="h-6 w-6 text-[#333333]" />
                    </div>
                    <div>
                      <h2 className="text-xl font-semibold text-[#333333]">
                        {formatModelLabel(model.name)}
                      </h2>
                      <p className="text-sm text-[#333333]/60">{model.description}</p>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <span
                      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${
                        model.is_active
                          ? 'bg-green-100 text-green-700'
                          : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      <span
                        className={`mr-2 h-2 w-2 rounded-full ${
                          model.is_active ? 'bg-green-500' : 'bg-slate-400'
                        }`}
                      />
                      {model.is_active ? 'Active' : 'Inactive'}
                    </span>

                    <span
                      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${
                        model.configured
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-amber-100 text-amber-700'
                      }`}
                    >
                      {model.configured ? 'Configured' : 'Needs Config'}
                    </span>

                    {model.is_loaded && (
                      <span className="bg-[#333333]/8 inline-flex items-center rounded-full px-3 py-1 text-xs font-medium text-[#333333]/70">
                        Loaded
                      </span>
                    )}
                  </div>
                </div>

                <button
                  onClick={() => handleToggle(model)}
                  disabled={switchingModel !== null}
                  className={`relative inline-flex h-7 w-12 flex-shrink-0 items-center rounded-full transition-colors ${
                    model.is_active ? 'bg-green-500' : 'bg-slate-300'
                  } ${switchingModel ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}`}
                  aria-label={`${model.is_active ? 'Deactivate' : 'Activate'} ${model.name}`}
                >
                  <span
                    className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
                      model.is_active ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>

              <div className="mt-5 flex flex-col gap-3 border-t border-[#E0E0E0] pt-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="text-sm text-[#333333]/55">
                  {isBusy
                    ? 'Updating model state...'
                    : model.configurable
                      ? 'Runtime credentials and endpoint can be edited.'
                      : 'Built-in model with no runtime configuration.'}
                </div>

                {model.configurable && (
                  <div className="flex flex-wrap gap-2">
                    {model.name === 'qwen3-vl' && (
                      <button
                        onClick={() => handleTestConnection(model)}
                        disabled={isTesting || switchingModel !== null || !model.configured}
                        className="inline-flex items-center gap-2 rounded-xl border border-[#E0E0E0] px-4 py-2 text-sm font-medium text-[#333333] transition-colors hover:bg-[#EAEAEA] disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {isTesting ? (
                          <>
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Testing...
                          </>
                        ) : (
                          'Test Connection'
                        )}
                      </button>
                    )}
                    <Link
                      href={`/dashboard/ai-analyze/${encodeURIComponent(model.name)}`}
                      className="inline-flex items-center gap-2 rounded-xl border border-[#E0E0E0] px-4 py-2 text-sm font-medium text-[#333333] transition-colors hover:bg-[#EAEAEA]"
                    >
                      <Settings2 className="h-4 w-4" />
                      Configure
                      <ArrowRight className="h-4 w-4" />
                    </Link>
                  </div>
                )}
              </div>

              {connectionResult && model.name === 'qwen3-vl' && (
                <div
                  className={cn(
                    'mt-4 rounded-xl border px-4 py-3 text-sm',
                    connectionResult.ok
                      ? 'border-green-200 bg-green-50 text-green-700'
                      : 'border-red-200 bg-red-50 text-red-700'
                  )}
                >
                  {connectionResult.message}
                </div>
              )}
            </div>
          )
        })}

        {models.length === 0 && (
          <div className="rounded-2xl border border-dashed border-[#D0D0D0] bg-white/60 p-10 text-center text-[#333333]/60">
            No AI models available
          </div>
        )}
      </div>
    </div>
  )
}
