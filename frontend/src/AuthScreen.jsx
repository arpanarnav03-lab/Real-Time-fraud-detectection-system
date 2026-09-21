import { useState } from "react";
import { API_BASE } from "./constants.js";
import { describeFetchError, describeErrorBody } from "./utils.js";

function AuthScreen({ onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const body = await res.json().catch(() => null);
      if (!res.ok) throw new Error(describeErrorBody(body, res.status));
      onAuthenticated(body.access_token);
    } catch (e) {
      setError(describeFetchError(e, mode === "login" ? "Login failed" : "Sign up failed"));
    }
    setSubmitting(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-sm bg-slate-900 border border-slate-800 rounded-xl p-6">
        <h1 className="text-xl font-bold mb-1">Real-Time Fraud Detection</h1>
        <p className="text-slate-500 text-sm mb-6">{mode === "login" ? "Log in to continue" : "Create an account"}</p>

        {error && (
          <div className="mb-4 px-3 py-2 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3">
          <label className="block">
            <span className="block text-xs text-slate-500 mb-1">Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
            />
          </label>
          <label className="block">
            <span className="block text-xs text-slate-500 mb-1">Password{mode === "signup" ? " (min 8 characters)" : ""}</span>
            <input
              type="password"
              required
              minLength={mode === "signup" ? 8 : undefined}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
            />
          </label>
          <button
            type="submit"
            disabled={submitting}
            className="w-full px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-500 transition disabled:opacity-50"
          >
            {submitting ? "…" : mode === "login" ? "Log in" : "Sign up"}
          </button>
        </form>

        <button
          type="button"
          onClick={() => { setMode(mode === "login" ? "signup" : "login"); setError(null); }}
          className="mt-4 text-xs text-slate-500 hover:text-slate-300 transition"
        >
          {mode === "login" ? "Need an account? Sign up" : "Already have an account? Log in"}
        </button>
      </div>
    </div>
  );
}

export default AuthScreen;
