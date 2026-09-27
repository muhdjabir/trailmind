// Mirrors agent/app/api/schemas.py's response models.

export type Trip = {
  id: number;
  user_id: string | null;
  name: string;
  destinations: string[];
  start_date: string | null;
  end_date: string | null;
  party_size: number | null;
  status: string;
  budget_planned: number | null;
  budget_total: number | null;
  created_at: string;
  updated_at: string;
};

export type ItineraryDay = {
  day_number: number;
  // YYYY-MM-DD, or null while the trip's dates are open.
  date: string | null;
  title: string;
  items: string[];
  updated_at: string;
};

export type TripStats = {
  trip_days: number | null;
  days_planned: number;
  open_days: number[];
  budget_planned: number | null;
  budget_total: number | null;
  weather: {
    destination: string;
    source: "forecast" | "historical_average";
    avg_high_c: number;
    avg_low_c: number;
    total_precipitation_mm: number;
  } | null;
  weather_error: string | null;
};

export type ChatMessage = {
  role: string;
  content: string;
  created_at: string;
};
