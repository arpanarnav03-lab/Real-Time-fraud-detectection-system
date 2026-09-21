function ToggleField({ label, checked, onChange }) {
  return (
    <label className="flex items-center justify-between gap-3 bg-slate-800 border border-slate-700 rounded-md px-3 py-2 cursor-pointer select-none">
      <span className="text-sm text-slate-300">{label}</span>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="sr-only" />
      <span className={`w-9 h-5 rounded-full transition relative shrink-0 ${checked ? "bg-indigo-600" : "bg-slate-600"}`}>
        <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${checked ? "translate-x-4" : ""}`}></span>
      </span>
    </label>
  );
}

export default ToggleField;
