// Mirrors agent/app/api/schemas.py's TripResponse/ChatMessageResponse.

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

export type ChatMessage = {
  role: string;
  content: string;
  created_at: string;
};
