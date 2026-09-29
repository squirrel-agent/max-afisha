# ML Pipeline

## Event embeddings

```text
title + category + genres + tags + venue + city + description
                    ↓
        multilingual-e5-small
                    ↓
          384-dim embedding
                    ↓
              pgvector
```

## User profile

Анкета содержит ровно 5 ответов: время, компания, настроение, доступная длительность и бюджет. Backend переводит нормализованные коды в текст, добавляет пользовательские free-form ответы и строит E5 query embedding. Вопроса о категориях в текущем onboarding нет.

## Hard constraints

До ML-выдачи применяются ограничения, которые можно проверить по данным события:

- город;
- актуальность (явно прошедшие события не предлагаются);
- выбранный период (`сегодня вечером`, `завтра`, ближайшие выходные);
- бюджет;
- максимальная длительность;
- радиус, если пользователь дал геопозицию.

Для строгого запроса по времени/длительности неизвестные поля не интерпретируются как совпадение.

## Relevance gate

Главное правило текущей версии: **nearest neighbour не означает relevant result**. Если все кандидаты слабые, backend возвращает ноль персональных событий вместо «лучшего из плохих».

Для анкеты без выбора категории итоговый score:

- 50% semantic similarity;
- 20% поведенческий сигнал по истории;
- 15% близость даты;
- 10% расстояние, когда доступна геопозиция;
- 5% novelty.

Персональное событие проходит только при выполнении обоих порогов:

- `semantic_similarity >= RECOMMENDATION_MIN_SEMANTIC_SIMILARITY` (default `0.78`);
- `final_score >= RECOMMENDATION_MIN_FINAL_SCORE` (default `0.62`).

Свободный neural search использует отдельный `NEURAL_SEARCH_MIN_SIMILARITY` (default `0.78`). Пороги конфигурируются через environment и должны калиброваться на собственной размеченной выборке.

## Empty personalized result

`GET /api/recommendations/{user_id}` возвращает:

- `has_relevant: false`;
- пустые `podium/items`;
- `fallback_reason` (`no_relevant_events`, `no_events_after_constraints`, `event_embeddings_unavailable` или `profile_embedding_unavailable`);
- диагностические counters в `relevance`.

Frontend в этом случае показывает сообщение «По вашему запросу нет вариантов. Попробуйте также:» и отдельно загружает `/api/events` как `fallback_feed`. Общая лента не смешивается с персональным score и не выдаётся за результат ML.
