import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { api, type PodiumItem } from '../api/client';
import { useApp } from '../store/app';
import { EventCard } from '../components/EventCard';

export function Home() {
  const { userId, city, resetQuestionnaire } = useApp();
  const qc = useQueryClient();
  const [geo, setGeo] = useState<{ lat: number; lon: number }>();
  const [locationPrompt, setLocationPrompt] = useState(typeof navigator !== 'undefined' && 'geolocation' in navigator);
  const [locationError, setLocationError] = useState('');
  const [rating, setRating] = useState(0);
  const [rated, setRated] = useState(false);
  const [celebrating, setCelebrating] = useState(false);

  const rec = useQuery({
    queryKey: ['rec', userId, city, geo],
    queryFn: () => api.recommend(userId!, geo),
    enabled: !!userId,
  });

  const hasPersonal = Boolean(
    rec.isSuccess &&
    (rec.data.has_relevant ?? rec.data.items.length > 0) &&
    rec.data.items.length > 0,
  );
  const shouldShowFallback = !userId || rec.isError || (rec.isSuccess && !hasPersonal);
  const feed = useQuery({
    queryKey: ['events', city],
    queryFn: () => api.events(city),
    enabled: shouldShowFallback,
  });

  useEffect(() => {
    if (!hasPersonal) {
      setCelebrating(false);
      return;
    }
    setCelebrating(true);
    const timer = window.setTimeout(() => setCelebrating(false), 1800);
    return () => window.clearTimeout(timer);
  }, [hasPersonal, rec.data?.run_id]);

  async function act(
    eventId: string,
    action: string,
    surface: 'questionnaire_podium' | 'fallback_feed',
    directionPosition?: number,
    eventPosition?: number,
  ) {
    if (userId) {
      await api.action(
        userId,
        eventId,
        action,
        {
          ...(surface === 'questionnaire_podium' && rec.data?.run_id ? { run_id: rec.data.run_id } : {}),
          position: eventPosition || directionPosition,
          surface,
          algorithm_version: surface === 'questionnaire_podium' ? rec.data?.model_version : 'baseline-feed',
        },
      );
    }
    if (action === 'dislike' && surface === 'questionnaire_podium') {
      qc.invalidateQueries({ queryKey: ['rec', userId, city] });
    }
  }

  function enableNearby() {
    setLocationError('');
    if (!navigator.geolocation) {
      setLocationPrompt(false);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setGeo({ lat: position.coords.latitude, lon: position.coords.longitude });
        setLocationPrompt(false);
      },
      () => {
        setLocationError('Не удалось определить местоположение. Показываем события по выбранному городу.');
        setLocationPrompt(false);
      },
      { maximumAge: 300000, timeout: 8000 },
    );
  }

  async function sendRating(value: number) {
    setRating(value);
    setRated(true);
    if (userId && hasPersonal) {
      try { await api.rate(userId, value, rec.data?.run_id); } catch { /* rating is non-blocking */ }
    }
  }

  const podium: PodiumItem[] = hasPersonal ? (rec.data?.podium || []) : [];
  const personalItems = useMemo(
    () => podium.length ? podium.flatMap((direction) => direction.items) : (hasPersonal ? rec.data?.items || [] : []),
    [podium, hasPersonal, rec.data?.items],
  );
  const fallbackItems = feed.data ?? [];
  const fewerDirections = podium.length > 0 && podium.length < 3;
  const noRelevant = rec.isSuccess && !hasPersonal;
  const personalizationUnavailable = noRelevant && ['profile_embedding_unavailable', 'event_embeddings_unavailable'].includes(rec.data?.fallback_reason || '');

  return (
    <>
      <main className="home">
        <section className="hero">
          <span>{hasPersonal ? 'Персонально для тебя' : 'MAX Афиша'}</span>
          <h1>Куда пойдём?</h1>
          <p>{geo ? 'Ищем события рядом с тобой' : 'Показываем события в выбранном городе'}</p>
          {locationPrompt && (
            <button type="button" className="locationAction" onClick={enableNearby}>Искать рядом со мной</button>
          )}
          {locationError && <p className="locationNotice" role="status">{locationError}</p>}
        </section>

        {rec.isLoading && userId && <div className="empty" role="status">Подбираем события…</div>}

        {podium.length > 0 && (
          <section className="podium">
            <div className="sectionTitle">
              <h2>Твои направления</h2>
              <span>
                {rec.data?.location_source === 'browser' ? 'рядом с тобой' : 'по городу'}
                {rec.data?.location_source === 'browser' && rec.data?.radius_used_km ? ' · ' + rec.data.radius_used_km + ' км' : ''}
              </span>
            </div>
            {fewerDirections && <p className="podiumNote">Найдено {podium.length} направлений — показываем только действительно подходящие варианты.</p>}
            <div className="podiumGrid">
              {podium.map((direction) => (
                <article className={'podiumCard rank' + direction.rank} key={direction.type}>
                  <b>{direction.rank}</b><strong>{direction.label}</strong>
                </article>
              ))}
            </div>
          </section>
        )}

        {podium.length > 0 && podium.map((direction) => (
          <section className="recommendationGroup" key={direction.type}>
            <div className="sectionTitle"><h2>{direction.label}</h2></div>
            <div className="grid">
              {direction.items.map((event, index) => (
                <EventCard
                  key={String(event.id)}
                  event={event}
                  onAction={(action) => act(String(event.id), action, 'questionnaire_podium', direction.rank, index + 1)}
                />
              ))}
            </div>
          </section>
        ))}

        {hasPersonal && podium.length === 0 && (
          <section className="recommendationGroup">
            <div className="sectionTitle"><h2>События для тебя</h2></div>
            <div className="grid">
              {personalItems.map((event, index) => (
                <EventCard key={String(event.id)} event={event} onAction={(action) => act(String(event.id), action, 'questionnaire_podium', undefined, index + 1)} />
              ))}
            </div>
          </section>
        )}

        {noRelevant && (
          <section className="noMatch" role="status" aria-live="polite">
            <h2>{personalizationUnavailable ? 'Не удалось найти событие по запросу.' : 'По вашему запросу нет вариантов.'}</h2>
            <p>Вот наиболее подходящие:</p>
          </section>
        )}
        {rec.isError && (
          <section className="noMatch error" role="alert">
            <h2>Не удалось получить персональную подборку.</h2>
            <p>Попробуйте также:</p>
          </section>
        )}
        {!userId && (
          <section className="noMatch">
            <h2>Афиша города</h2>
            <p>Пройдите короткий опрос, чтобы получить персональную подборку.</p>
          </section>
        )}

        {shouldShowFallback && !feed.isLoading && fallbackItems.length > 0 && (
          <section className="fallbackFeed" aria-label="Общая лента событий">
            <div className="grid">
              {fallbackItems.map((event, index) => (
                <EventCard key={String(event.id)} event={event} onAction={(action) => act(String(event.id), action, 'fallback_feed', undefined, index + 1)} />
              ))}
            </div>
          </section>
        )}
        {shouldShowFallback && feed.isLoading && <div className="empty">Загружаем афишу…</div>}
        {shouldShowFallback && feed.isError && <div className="empty error">Не удалось загрузить общую афишу. Попробуйте обновить страницу.</div>}
        {shouldShowFallback && feed.isSuccess && fallbackItems.length === 0 && (
          <div className="empty">В афише выбранного города пока нет актуальных событий.</div>
        )}

        {hasPersonal && (
          <section className="rating">
            <h3>Насколько полезна подборка?</h3>
            <div>
              {[1, 2, 3, 4, 5].map((value) => (
                <button key={value} aria-label={value + ' звёзд'} className={value <= rating ? 'star active' : 'star'} aria-pressed={value <= rating} onClick={() => sendRating(value)}>★</button>
              ))}
            </div>
            {rated && <small>Спасибо за оценку</small>}
          </section>
        )}
        <button className="restart" onClick={() => { resetQuestionnaire(); window.scrollTo({ top: 0 }); }}>Пройти опрос заново</button>
      </main>
      {celebrating && hasPersonal && (
        <div className="celebration" aria-hidden="true"><span>🎉</span><span>🎊</span><span>✨</span><b>Подборка готова!</b></div>
      )}
    </>
  );
}
