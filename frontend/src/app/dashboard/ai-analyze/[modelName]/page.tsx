"use client";

import { useParams, usePathname } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { resolveRouteSegment } from "@/lib/route-params";

import { AIModelConfigPageContent } from "../_components/AIModelConfigPageContent";

export default function AIModelConfigPage() {
  const params = useParams();
  const pathname = usePathname();

  const modelName = resolveRouteSegment({
    param: params.modelName,
    pathname,
    pattern: /\/dashboard\/ai-analyze\/([^/]+)\/?$/,
  });

  if (!modelName) {
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
          Invalid model route. Open this page from the AI Analyze Server list (Configure).
        </div>
      </div>
    );
  }

  return <AIModelConfigPageContent modelName={modelName} />;
}
