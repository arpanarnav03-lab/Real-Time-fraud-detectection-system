import { API_BASE } from "./constants.js";

export function describeFetchError(e, fallback) {
  // fetch() only throws TypeError for a network-level failure (backend down,
  // wrong port, CORS). Anything else here is a response we did get, just
  // with a non-2xx status — worth telling apart so the message is honest.
  // Name the actual API_BASE rather than hardcoding a URL: this message is
  // shown in production too, where "localhost:8000" was actively misleading.
  if (e instanceof TypeError) {
    return `Can't reach the backend at ${API_BASE}.`;
  }
  return `${fallback}: ${e.message}`;
}

// Extracts a readable message from a FastAPI error body: a plain string
// (HTTPException) or a list of Pydantic validation errors.
export function describeErrorBody(body, status) {
  if (!body || !body.detail) return `Server responded with ${status}`;
  return Array.isArray(body.detail) ? body.detail.map((d) => d.msg).join("; ") : body.detail;
}
