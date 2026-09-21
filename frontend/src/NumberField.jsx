function NumberField({ label, suffix, value, onChange, min, max, step = "any" }) {
  return (
    <label className="block">
      <span className="block text-xs text-slate-500 mb-1">{label}{suffix ? ` (${suffix})` : ""}</span>
      <input
        type="number"
        required
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
      />
    </label>
  );
}

export default NumberField;
