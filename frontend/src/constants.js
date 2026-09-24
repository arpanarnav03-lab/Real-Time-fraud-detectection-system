export const API_BASE = "https://your-actual-render-url.onrender.com";

export const RISK_STYLES = {
  high:   { dot: "bg-rose-500",   text: "text-rose-400",   bg: "bg-rose-500/10 border-rose-500/30" },
  medium: { dot: "bg-amber-500",  text: "text-amber-400",  bg: "bg-amber-500/10 border-amber-500/30" },
  low:    { dot: "bg-emerald-500",text: "text-emerald-400",bg: "bg-emerald-500/10 border-emerald-500/30" },
};

// Realistic pre-fills so a demo doesn't require typing all 9 fields by hand.
export const PRESETS = {
  suspicious: {
    loan_amount: "75000",
    distance_from_home: "250",
    distance_from_last_transaction: "180",
    ratio_to_median_purchase: "6.5",
    hour_of_day: "3",
    repeat_borrower: false,
    used_chip_or_biometric: false,
    used_pin_or_otp: false,
    is_online_channel: true,
  },
  normal: {
    loan_amount: "5000",
    distance_from_home: "8",
    distance_from_last_transaction: "3",
    ratio_to_median_purchase: "1.0",
    hour_of_day: "14",
    repeat_borrower: true,
    used_chip_or_biometric: true,
    used_pin_or_otp: true,
    is_online_channel: false,
  },
};

export const EMPTY_FORM = {
  loan_amount: "",
  distance_from_home: "",
  distance_from_last_transaction: "",
  ratio_to_median_purchase: "",
  hour_of_day: "",
  repeat_borrower: false,
  used_chip_or_biometric: false,
  used_pin_or_otp: false,
  is_online_channel: false,
};
