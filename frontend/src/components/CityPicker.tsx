import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { Check, MapPin, Search, X } from 'lucide-react';
import { fallbackCities, getCity, loadCities, suggestCities, type CityId } from '../data/cities';

type CitySearchProps = {
  city: CityId;
  onSelect: (city: CityId) => void;
  autoFocus?: boolean;
  disabled?: boolean;
};

export function CitySearch({ city, onSelect, autoFocus, disabled }: CitySearchProps) {
  const currentCity = getCity(city);
  const [catalog, setCatalog] = useState(fallbackCities);
  const [query, setQuery] = useState(currentCity.name);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const results = suggestCities(catalog, query);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => setQuery(currentCity.name), [currentCity.name]);

  useEffect(() => {
    let active = true;
    loadCities().then((items) => { if (active) setCatalog(items); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    function closeOnOutsideClick(event: MouseEvent) {
      if (event.target instanceof Node && !wrapperRef.current?.contains(event.target)) setOpen(false);
    }
    document.addEventListener('mousedown', closeOnOutsideClick);
    return () => document.removeEventListener('mousedown', closeOnOutsideClick);
  }, []);

  function choose(id: CityId) {
    onSelect(id);
    setQuery(getCity(id).name);
    setOpen(false);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Escape') {
      setQuery(currentCity.name);
      setOpen(false);
      if (open) event.stopPropagation();
      return;
    }
    if (event.key === 'ArrowDown' && results.length) {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((index) => index < 0 ? 0 : (index + 1) % results.length);
    }
    if (event.key === 'ArrowUp' && results.length) {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((index) => index < 0 ? results.length - 1 : (index - 1 + results.length) % results.length);
    }
    if (event.key === 'Enter' && open && results.length) {
      event.preventDefault();
      const match = results.find((result) => result.id === city);
      const selected = activeIndex >= 0 ? results[activeIndex] : match ?? results[0];
      choose(selected.id);
    }
  }

  return (
    <div className="citySearch" ref={wrapperRef}>
      <label className="citySearchInput">
        <Search size={18} aria-hidden="true" />
        <input
          role="combobox"
          autoFocus={autoFocus}
          disabled={disabled}
          aria-expanded={open}
          aria-controls="city-suggestions"
          aria-activedescendant={activeIndex >= 0 && results[activeIndex] ? 'city-option-' + results[activeIndex].id : undefined}
          aria-autocomplete="list"
          aria-label="Найти город"
          value={query}
          placeholder="Введите название города"
          onFocus={() => { if (query === currentCity.name) setQuery(''); setOpen(true); setActiveIndex(-1); }}
          onChange={(event) => { setQuery(event.target.value); setOpen(true); setActiveIndex(-1); }}
          onKeyDown={handleKeyDown}
        />
        {query && <button type="button" className="cityClear" aria-label="Очистить поиск" disabled={disabled} onClick={() => { setQuery(''); setOpen(true); setActiveIndex(-1); }}><X size={16} /></button>}
      </label>
      {open && (
        <div className="citySuggestions" id="city-suggestions" role="listbox" aria-label="Города">
          {results.length ? results.map((item, index) => (
            <button
              type="button"
              role="option"
              id={'city-option-' + item.id}
              aria-selected={item.id === city}
              className={'citySuggestion' + (index === activeIndex ? ' active' : '')}
              key={item.id}
              onMouseEnter={() => setActiveIndex(index)}
              onClick={() => { if (!disabled) choose(item.id); }}
            >
              <span className="citySuggestionIcon"><MapPin size={17} /></span>
              <span className="citySuggestionText"><strong>{item.name}</strong><small>{item.region}</small></span>
              {item.id === city && <Check className="cityCheck" size={17} aria-label="Выбран" />}
            </button>
          )) : <p className="cityNoResults">Город не найден</p>}
        </div>
      )}
    </div>
  );
}

