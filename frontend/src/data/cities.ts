import { api } from '../api/client';

export type CityId = 'moscow' | 'saint-petersburg';

export type City = {
  id: CityId;
  name: string;
  region: string;
  aliases: string[];
};

export const fallbackCities: City[] = [
  { id: 'moscow', name: 'Москва', region: 'Москва', aliases: ['москва', 'мск', 'moscow'] },
  { id: 'saint-petersburg', name: 'Санкт-Петербург', region: 'Санкт-Петербург', aliases: ['санкт-петербург', 'санкт петербург', 'спб', 'питер', 'saint-petersburg', 'st petersburg'] },
];

export async function loadCities(): Promise<City[]> {
  try {
    const result = await api.cities();
    return result.length ? result : fallbackCities;
  } catch {
    return fallbackCities;
  }
}

export function getCity(id: CityId) {
  return fallbackCities.find((city) => city.id === id) ?? fallbackCities[0];
}

export function suggestCities(catalog: City[], query: string) {
  const normalized = query.trim().toLocaleLowerCase('ru');
  if (!normalized) return catalog;

  return catalog
    .map((city) => {
      const candidates = [city.name, city.id.replaceAll('-', ' '), ...city.aliases]
        .map((value) => value.toLocaleLowerCase('ru'));
      const score = Math.min(...candidates.map((value) => {
        if (value === normalized) return 0;
        if (value.startsWith(normalized)) return 1;
        if (value.includes(normalized)) return 2;
        return Number.POSITIVE_INFINITY;
      }));
      return { city, score };
    })
    .filter(({ score }) => Number.isFinite(score))
    .sort((a, b) => a.score - b.score)
    .map(({ city }) => city);
}
