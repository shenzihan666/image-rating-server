"use client";

/**
 * Explicit route for /dashboard/ai-analyze/qwen3-vl so it does not collide with the
 * static segment folder `qwen3-vl/prompts/` (Next may not bind `modelName` correctly otherwise).
 */
import { AIModelConfigPageContent } from "../_components/AIModelConfigPageContent";

export default function Qwen3VlModelConfigPage() {
  return <AIModelConfigPageContent modelName="qwen3-vl" />;
}
