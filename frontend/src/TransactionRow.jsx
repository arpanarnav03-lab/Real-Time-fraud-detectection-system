import { RISK_STYLES } from "./constants.js";

function TransactionRow({ txn, onExpand, expanded, onStatusChange, highlight }) {
  const risk = RISK_STYLES[txn.risk_level] || RISK_STYLES.low;
  return (
    <>
      <tr
        onClick={() => onExpand(txn.id)}
        className={`border-b border-slate-800 cursor-pointer transition ${
          highlight ? "bg-indigo-500/15 ring-1 ring-inset ring-indigo-400 animate-pulse" : "hover:bg-slate-900/60"
        }`}
      >
        <td className="py-3.5 px-4 text-slate-400 text-sm">#{txn.id}</td>
        <td className="py-3.5 px-4">
          <span className={`inline-flex items-center gap-2 text-sm font-medium ${risk.text}`}>
            <span className={`w-2 h-2 rounded-full ${risk.dot}`}></span>
            {txn.risk_level.toUpperCase()}
          </span>
        </td>
        <td className="py-3.5 px-4 text-sm">{(txn.fraud_probability * 100).toFixed(1)}%</td>
        <td className="py-3.5 px-4 text-sm">₹{Number(txn.loan_amount).toLocaleString(undefined, {maximumFractionDigits:0})}</td>
        <td className="py-3.5 px-4 text-sm text-slate-400">{txn.distance_from_home.toFixed(0)} km</td>
        <td className="py-3.5 px-4">
          <span className="text-xs px-2 py-1 rounded-full bg-slate-800 text-slate-300 capitalize">{txn.status}</span>
        </td>
        <td className="py-3.5 px-4 text-sm text-slate-500">{txn.recommended_action.replace("_", " ")}</td>
      </tr>
      {expanded && (
        <tr className="border-b border-slate-800 bg-slate-900/40">
          <td colSpan="7" className="px-4 py-4">
            <div className={`rounded-lg border p-5 ${risk.bg}`}>
              <div className="text-sm text-slate-200 mb-3 leading-relaxed">{txn.explanation}</div>
              <div className="text-xs text-slate-500 mb-3">
                Explanation source: {txn.source === "groq" ? "Groq (LLM)" : "rule-based fallback"}
              </div>
              {txn.similar_cases && txn.similar_cases.length > 0 && (
                <div className="mb-3">
                  <div className="text-xs uppercase tracking-wide text-slate-500 mb-1">Similar past cases</div>
                  <ul className="text-xs text-slate-400 space-y-0.5">
                    {txn.similar_cases.map((c) => (
                      <li key={c.transaction_id}>
                        #{c.transaction_id} — {c.risk_level} risk ({(c.fraud_probability * 100).toFixed(1)}%),
                        {" "}₹{Number(c.loan_amount).toLocaleString(undefined, {maximumFractionDigits: 0})}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="flex gap-2">
                <button
                  onClick={(e) => { e.stopPropagation(); onStatusChange(txn.id, "cleared"); }}
                  className="px-3 py-1.5 text-xs rounded-md bg-emerald-600 hover:bg-emerald-500 transition"
                >Clear</button>
                <button
                  onClick={(e) => { e.stopPropagation(); onStatusChange(txn.id, "flagged"); }}
                  className="px-3 py-1.5 text-xs rounded-md bg-rose-600 hover:bg-rose-500 transition"
                >Flag</button>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default TransactionRow;
