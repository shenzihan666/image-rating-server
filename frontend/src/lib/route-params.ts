/**
 * Resolve App Router dynamic segments when useParams() is missing or delayed
 * (common difference between next dev and production builds behind proxies).
 */

export function safeDecodePathSegment(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment;
  }
}

export function segmentFromParam(
  param: string | string[] | undefined
): string {
  const raw =
    typeof param === "string"
      ? param
      : Array.isArray(param) && param[0]
        ? param[0]
        : "";
  return raw ? safeDecodePathSegment(raw) : "";
}

export function resolveRouteSegment(options: {
  param: string | string[] | undefined;
  pathname: string;
  /** First capture group must be the segment value. */
  pattern: RegExp;
  /** If the segment equals any of these, treat as unresolved. */
  reject?: readonly string[];
}): string {
  const fromParam = segmentFromParam(options.param);
  if (fromParam) {
    if (options.reject?.includes(fromParam)) {
      return "";
    }
    return fromParam;
  }
  const m = options.pathname.match(options.pattern);
  if (!m?.[1]) {
    return "";
  }
  const decoded = safeDecodePathSegment(m[1]);
  if (options.reject?.includes(decoded)) {
    return "";
  }
  return decoded;
}
