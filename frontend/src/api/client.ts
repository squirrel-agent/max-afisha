import type { CityId } from '../data/cities';

export type CityItem = { id: CityId; name: string; region: string; aliases: string[] };
export type QuestionnairePayload = {
  categories: string[];
  genres?: string[];
  budget?: string;
  budget_text?: string;
  budget_max?: number | null;
  preferred_period?: string;
  company?: string;
  company_size?: string;
  company_text?: string;
  when?: string;
  when_text?: string;
  vibe?: string;
  vibe_text?: string;
  duration?: string;
  duration_text?: string;
  duration_min?: number | null;
  duration_max?: number | null;
  questionnaire_version?: string;
  novelty_preference?: number;
};
export type EventItem = {
  id: string;
  title: string;
  description?: string;
  category?: string;
  venue_name?: string;
  address?: string;
  city?: string;
  start_at?: string;
  end_at?: string;
  price_min?: number;
  price_max?: number;
  is_free?: boolean;
  age_min?: number;
  image_url?: string;
  primary_source?: string;
  source_url?: string;
  ticket_url?: string;
  score?: number;
  similarity?: number;
  semantic_similarity?: number;
  distance_km?: number;
  next_session?: string;
  price_label?: string;
};
export type PodiumItem = { rank: number; type: string; label: string; parent?: string | null; items: EventItem[] };
export type RecommendationResponse = {
  model_version?: string;
  run_id?: string;
  has_relevant?: boolean;
  fallback_reason?: string | null;
  relevance?: {
    min_semantic_similarity: number;
    min_final_score: number;
    hard_filter_candidates: number;
    semantic_scored_candidates: number;
    rejected_low_relevance: number;
  };
  podium?: PodiumItem[];
  items_by_type?: Record<string, EventItem[]>;
  radius_used_km?: number;
  location_source?: string;
  items: EventItem[];
};

const BASE = import.meta.env.VITE_API_URL || '';

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(BASE + path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  });
  if (!response.ok) throw new Error(String(response.status) + ': ' + (await response.text()));
  return response.json();
}

export const api = {
  cities: () => req<CityItem[]>('/api/cities'),
  events: (city: CityId) => req<EventItem[]>('/api/events?city=' + encodeURIComponent(city) + '&limit=100'),
  createUser: (city: CityId) => req<{ id: string }>('/api/users', { method: 'POST', body: JSON.stringify({ city }) }),
  maxSession: (initData: string, city: CityId) =>
    req<{ id: string; city: CityId; max_user_id: number; authenticated_via: string }>('/api/max/session', {
      method: 'POST',
      body: JSON.stringify({ init_data: initData, city }),
    }),
  setCity: (id: string, city: CityId) => req<{ ok: boolean; city: CityId }>('/api/users/' + id + '/city', { method: 'PUT', body: JSON.stringify({ city }) }),
  prefs: (id: string, payload: QuestionnairePayload) => req('/api/users/' + id + '/preferences', { method: 'PUT', body: JSON.stringify(payload) }),
  action: (id: string, event_id: string, action: string, context?: { run_id?: string; position?: number; surface?: string; algorithm_version?: string }) =>
    req('/api/users/' + id + '/interactions', { method: 'POST', body: JSON.stringify({ event_id, action, ...context }) }),
  recommend: (id: string, opts?: { lat?: number; lon?: number; radius_km?: number }) => {
    const query = new URLSearchParams({ limit: '40' });
    if (opts?.lat != null) query.set('lat', String(opts.lat));
    if (opts?.lon != null) query.set('lon', String(opts.lon));
    if (opts?.radius_km != null) query.set('radius_km', String(opts.radius_km));
    return req<RecommendationResponse>('/api/recommendations/' + id + '?' + query.toString());
  },
  rate: (id: string, rating: number, run_id?: string) =>
    req('/api/recommendations/' + id + '/rating', { method: 'POST', body: JSON.stringify({ rating, run_id }) }),
  search: (query: string, city: CityId) =>
    req<{ has_relevant: boolean; fallback_reason?: string | null; items: EventItem[] }>('/api/search/neural', {
      method: 'POST',
      body: JSON.stringify({ query, city, period: 'any', categories: [], exclude_categories: [], limit: 20 }),
    }),
};
