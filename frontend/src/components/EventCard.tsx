import { MapPin, ThumbsDown } from 'lucide-react';
import type { EventItem } from '../api/client';

const SOURCE_LABELS: Record<string, string> = {
  yandex_afisha: 'Яндекс Афиша',
  afisha_ru: 'Афиша.ru',
  vk_events: 'VK События',
  demo: 'тестовые данные',
  test_data: 'тестовые данные',
};

export function EventCard({ event, onAction }: { event: EventItem; onAction: (action: string) => void }) {
  const rawDate = event.next_session || event.start_at;
  const dateObject = rawDate ? new Date(rawDate) : null;
  const date = dateObject && !Number.isNaN(dateObject.getTime())
    ? dateObject.toLocaleString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
    : 'Время уточняется';
  const price = event.price_label || (event.is_free ? 'Бесплатно' : event.price_min != null ? 'от ' + event.price_min + ' ₽' : 'Цена уточняется');
  const sourceUrl = event.ticket_url || event.source_url;
  const sourceLabel = event.primary_source ? (SOURCE_LABELS[event.primary_source] || event.primary_source) : 'источник события';

  return (
    <article className="card" onClick={() => onAction('view')}>
      <div className="cover">
        {event.image_url ? <img src={event.image_url} alt="" /> : <div className="placeholder">MAX<br />Афиша</div>}
      </div>
      <div className="cardBody">
        <div className="meta">{event.category || 'Событие'} · {date}</div>
        <h3>{event.title}</h3>
        <div className="place"><MapPin size={14} />{event.venue_name || event.address || event.city || 'Городское событие'}{event.distance_km != null && <span> · {event.distance_km} км</span>}</div>
        <div className={event.primary_source === 'demo' || event.primary_source === 'test_data' ? 'sourceMeta testData' : 'sourceMeta'}>
          Источник: {sourceLabel}
          {sourceUrl && <a className="sourceLink" href={sourceUrl} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>Подробнее ↗</a>}
        </div>
        <div className="cardFoot">
          <b>{price}</b>
          <div className="actions">
            <button aria-label="Не показывать" onClick={(e) => { e.stopPropagation(); onAction('dislike'); }}><ThumbsDown size={17} /></button>
          </div>
        </div>
      </div>
    </article>
  );
}
