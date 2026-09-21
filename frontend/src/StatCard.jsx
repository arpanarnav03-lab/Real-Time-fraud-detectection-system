function StatCard({ label, value, accent }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl px-5 py-5">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`text-2xl font-semibold mt-1.5 ${accent || "text-slate-100"}`}>{value}</div>
    </div>
  );
}

export default StatCard;
