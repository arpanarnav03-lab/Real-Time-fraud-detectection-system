import { useState } from "react";
import { PRESETS, EMPTY_FORM } from "./constants.js";
import NumberField from "./NumberField.jsx";
import ToggleField from "./ToggleField.jsx";

function NewTransactionPanel({ onSubmit, submitting }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);

  const setField = (name) => (value) => setForm((f) => ({ ...f, [name]: value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    const ok = await onSubmit({
      loan_amount: Number(form.loan_amount),
      distance_from_home: Number(form.distance_from_home),
      distance_from_last_transaction: Number(form.distance_from_last_transaction),
      ratio_to_median_purchase: Number(form.ratio_to_median_purchase),
      hour_of_day: Number(form.hour_of_day),
      repeat_borrower: form.repeat_borrower ? 1 : 0,
      used_chip_or_biometric: form.used_chip_or_biometric ? 1 : 0,
      used_pin_or_otp: form.used_pin_or_otp ? 1 : 0,
      is_online_channel: form.is_online_channel ? 1 : 0,
    });
    if (ok) {
      setForm(EMPTY_FORM);
      setOpen(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl mb-6 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-4 text-sm font-medium hover:bg-slate-800/50 transition"
      >
        <span>+ New Transaction</span>
        <span className="text-slate-500 text-xs">{open ? "Hide ▲" : "Show ▼"}</span>
      </button>
      {open && (
        <form onSubmit={handleSubmit} className="px-5 pb-5 pt-1 border-t border-slate-800">
          <div className="flex gap-2 mb-4 mt-4">
            <button
              type="button"
              onClick={() => setForm(PRESETS.suspicious)}
              className="px-3 py-1.5 text-xs rounded-md bg-rose-600/20 text-rose-300 border border-rose-600/40 hover:bg-rose-600/30 transition"
            >Try a suspicious pattern</button>
            <button
              type="button"
              onClick={() => setForm(PRESETS.normal)}
              className="px-3 py-1.5 text-xs rounded-md bg-emerald-600/20 text-emerald-300 border border-emerald-600/40 hover:bg-emerald-600/30 transition"
            >Try a normal pattern</button>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
            <NumberField label="Loan amount" suffix="₹" value={form.loan_amount} onChange={setField("loan_amount")} min="1" />
            <NumberField label="Distance from home" suffix="km" value={form.distance_from_home} onChange={setField("distance_from_home")} min="0" />
            <NumberField label="Distance from last txn" suffix="km" value={form.distance_from_last_transaction} onChange={setField("distance_from_last_transaction")} min="0" />
            <NumberField label="Ratio to median purchase" value={form.ratio_to_median_purchase} onChange={setField("ratio_to_median_purchase")} min="0" />
            <NumberField label="Hour of day" suffix="0-23" value={form.hour_of_day} onChange={setField("hour_of_day")} min="0" max="23" />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <ToggleField label="Repeat borrower" checked={form.repeat_borrower} onChange={setField("repeat_borrower")} />
            <ToggleField label="Chip / biometric" checked={form.used_chip_or_biometric} onChange={setField("used_chip_or_biometric")} />
            <ToggleField label="PIN / OTP" checked={form.used_pin_or_otp} onChange={setField("used_pin_or_otp")} />
            <ToggleField label="Online channel" checked={form.is_online_channel} onChange={setField("is_online_channel")} />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-500 transition disabled:opacity-50"
          >
            {submitting ? "Scoring…" : "Score transaction"}
          </button>
        </form>
      )}
    </div>
  );
}

export default NewTransactionPanel;
