import { useState, useEffect } from "react";
import { API_BASE } from "./constants.js";
import { describeFetchError, describeErrorBody } from "./utils.js";
import StatCard from "./StatCard.jsx";
import NewTransactionPanel from "./NewTransactionPanel.jsx";
import TransactionRow from "./TransactionRow.jsx";

function Dashboard({ token, onLogout }) {
  const [transactions, setTransactions] = useState([]);
  const [expandedId, setExpandedId] = useState(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [highlightId, setHighlightId] = useState(null);
  const [error, setError] = useState(null);

  const busy = refreshing || seeding;

  // Attaches the bearer token to every API call, and signs the user out if
  // it's been rejected (missing/expired/invalid) rather than surfacing a
  // raw 401 as a generic error.
  const apiFetch = async (path, options = {}) => {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: { ...(options.headers || {}), Authorization: `Bearer ${token}` },
    });
    if (res.status === 401) {
      onLogout();
    }
    return res;
  };

  const fetchTransactions = async () => {
    try {
      const res = await apiFetch("/transactions");
      if (res.status === 401) return;
      if (!res.ok) throw new Error(`Server responded with ${res.status}`);
      setTransactions(await res.json());
      setError(null);
    } catch (e) {
      setError(describeFetchError(e, "Couldn't load transactions"));
    }
  };

  useEffect(() => {
    fetchTransactions().finally(() => setInitialLoading(false));
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchTransactions();
    setRefreshing(false);
  };

  const seedDemoData = async () => {
    setSeeding(true);
    try {
      const res = await apiFetch("/seed-demo-data", { method: "POST" });
      if (res.status === 401) { setSeeding(false); return; }
      if (!res.ok) throw new Error(`Server responded with ${res.status}`);
      await fetchTransactions();
    } catch (e) {
      setError(describeFetchError(e, "Seed failed"));
    }
    setSeeding(false);
  };

  const createTransaction = async (payload) => {
    setSubmitting(true);
    try {
      const res = await apiFetch("/transactions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (res.status === 401) { setSubmitting(false); return false; }
      const body = await res.json().catch(() => null);
      if (!res.ok) throw new Error(describeErrorBody(body, res.status));
      await fetchTransactions();
      setHighlightId(body.id);
      setTimeout(() => setHighlightId(null), 2500);
      setSubmitting(false);
      return true;
    } catch (e) {
      setError(describeFetchError(e, "Couldn't create transaction"));
      setSubmitting(false);
      return false;
    }
  };

  const updateStatus = async (id, status) => {
    try {
      const res = await apiFetch(`/transactions/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (res.status === 401) return;
      if (!res.ok) throw new Error(`Server responded with ${res.status}`);
      await fetchTransactions();
    } catch (e) {
      setError(describeFetchError(e, "Couldn't update status"));
    }
  };

  // While a just-created transaction is highlighted, pin it to the top
  // regardless of its natural risk-sort rank; once the highlight clears it
  // settles back into normal order on the next render.
  const orderedTransactions = highlightId
    ? [
        ...transactions.filter((t) => t.id === highlightId),
        ...transactions.filter((t) => t.id !== highlightId),
      ]
    : transactions;

  const highRisk = transactions.filter(t => t.risk_level === "high").length;
  const pending = transactions.filter(t => t.status === "pending").length;
  const avgProb = transactions.length
    ? (transactions.reduce((s, t) => s + t.fraud_probability, 0) / transactions.length * 100).toFixed(1)
    : "0";

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <div className="flex items-center justify-between mb-10">
        <div>
          <h1 className="text-2xl font-bold">Real-Time Fraud Detection</h1>
          <p className="text-slate-500 text-sm mt-1">Digital lending transaction monitor — ML scoring + LLM explanation</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={handleRefresh} disabled={busy} className="px-4 py-2 text-sm rounded-lg bg-slate-800 hover:bg-slate-700 transition disabled:opacity-50">
            {refreshing ? "Refreshing…" : "Refresh"}
          </button>
          <button onClick={seedDemoData} disabled={busy} className="px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-500 transition disabled:opacity-50">
            {seeding ? "Loading…" : "Load Demo Transactions"}
          </button>
          <div className="w-px h-6 bg-slate-800 mx-1"></div>
          <button onClick={onLogout} className="px-4 py-2 text-sm rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition">
            Log out
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-6 px-4 py-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm">{error}</div>
      )}

      <div className="grid grid-cols-4 gap-4 mb-10">
        <StatCard label="Total Transactions" value={transactions.length} />
        <StatCard label="High Risk" value={highRisk} accent="text-rose-400" />
        <StatCard label="Pending Review" value={pending} accent="text-amber-400" />
        <StatCard label="Avg Fraud Score" value={`${avgProb}%`} />
      </div>

      <NewTransactionPanel onSubmit={createTransaction} submitting={submitting} />

      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
              <th className="py-3 px-4">ID</th>
              <th className="py-3 px-4">Risk</th>
              <th className="py-3 px-4">Score</th>
              <th className="py-3 px-4">Amount</th>
              <th className="py-3 px-4">Distance</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4">Action</th>
            </tr>
          </thead>
          <tbody>
            {orderedTransactions.map(txn => (
              <TransactionRow
                key={txn.id}
                txn={txn}
                expanded={expandedId === txn.id}
                highlight={txn.id === highlightId}
                onExpand={(id) => setExpandedId(expandedId === id ? null : id)}
                onStatusChange={updateStatus}
              />
            ))}
          </tbody>
        </table>
        {initialLoading && (
          <div className="py-20 flex items-center justify-center gap-2 text-slate-500 text-sm">
            <span className="w-4 h-4 border-2 border-slate-600 border-t-slate-300 rounded-full animate-spin"></span>
            Loading transactions…
          </div>
        )}
        {!initialLoading && transactions.length === 0 && !error && (
          <div className="py-20 flex flex-col items-center gap-3 text-center px-6">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-10 h-10 text-slate-700">
              <rect x="5" y="3" width="14" height="18" rx="2" />
              <line x1="8" y1="8" x2="16" y2="8" />
              <line x1="8" y1="12" x2="16" y2="12" />
              <line x1="8" y1="16" x2="13" y2="16" />
            </svg>
            <div className="text-slate-400 text-sm">No transactions yet</div>
            <div className="text-slate-600 text-xs max-w-xs">
              Click "Load Demo Transactions" above to seed the dashboard, or add one yourself with "+ New Transaction".
            </div>
          </div>
        )}
      </div>

      <p className="text-xs text-slate-600 mt-6">
        Click a row to see the LLM explanation and take action. Prototype scope: Postgres+pgvector (Neon), single-service
        backend. Production target: AWS Bedrock, Render/Vercel deploy — see docs/ARCHITECTURE.md.
      </p>
    </div>
  );
}

export default Dashboard;
