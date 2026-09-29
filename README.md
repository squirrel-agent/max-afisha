# MAX Афиша — MVP

## 1. Назначение решения
Цифровой сервис и мини-приложение в МАХ для персонального подбора городских событий (Москва, Санкт-Петербург) на основе 5 вопросов анкеты и гибридного ML-ранжирования с pgvector. При отсутствии точных совпадений система отображает no-match экран и общую городскую ленту.

## 2. Основной пользовательский сценарий
1. Пользователь открывает мини-приложение через бота в МАХ (или в браузере).
2. Выбирает город (Москва или Санкт-Петербург).
3. Проходит 5 вопросов: время, компания, настроение, длительность, бюджет.
4. Backend строит эмбеддинг, применяет hard-фильтры и отсекает события ниже порога сходства.
5. Пользователь получает персональные рекомендации с причинами подбора и ссылкой на источник.

## 3. Состав и архитектура решения
- postgres: PostgreSQL 16 + pgvector (хранение данных и векторный поиск).
- backend: FastAPI (бизнес-логика, ML-ранжирование, эмбеддинги, валидация сессий МАХ).
- parser: сервис сбора и нормализации событий.
- frontend: React/Vite SPA (MAX Bridge, раздача через Nginx).

## 4. Запуск всех компонентов через Docker одной командой
docker compose up --build -d

## 5. Порядок остановки и повторного запуска
- Остановка: docker compose down
- Повторный запуск: docker compose up -d
- Полная очистка БД: docker compose down -v

## 6. Необходимые параметры и переменные окружения
Шаблон задан в .env.example, значения по умолчанию — в compose.yaml:
- POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD — реквизиты БД.
- ADMIN_TOKEN — Bearer-токен для защищенных эндпоинтов.
- TEXT_ENCODER_MODEL — модель эмбеддингов (intfloat/multilingual-e5-small).
- RECOMMENDATION_MIN_SEMANTIC_SIMILARITY — порог сходства (0.78).
- RECOMMENDATION_MIN_FINAL_SCORE — итоговый порог (0.62).
- MAX_BOT_TOKEN, MAX_INIT_DATA_MAX_AGE_SECONDS — параметры сессии МАХ.

## 7. Используемые порты
- Frontend: порт 8080 (FRONTEND_PORT) — Mini App UI
- Backend: порт 8000 (BACKEND_PORT) — REST API, OpenAPI
- Parser: порт 8010 (PARSER_PORT) — API управления парсером
- PostgreSQL: порт 5432 (POSTGRES_PORT) — БД pgvector

## 8. Зависимости
- Backend: Python 3.11, FastAPI, SQLAlchemy, asyncpg, pgvector, sentence-transformers (backend/requirements.txt).
- Parser: Python 3.11, httpx, beautifulsoup4, lxml (parser-service/requirements.txt).
- Frontend: Node 20, React 18, TypeScript, Vite, Axios (frontend/package.json).
- Базовые образы: python:3.11-slim, node:20-alpine, nginx:alpine, pgvector/pgvector:pg16.

## 9. Внешние сервисы и интеграции
- Платформа МАХ: среда запуска бота и контейнер Mini App по HTTPS с верификацией initData.
- Источники событий: открытые витрины Яндекс.Афиша и Афиша.ру (сбои парсинга не влияют на сохраненную локальную базу).
- HuggingFace: кэширование модели векторизации в локальный docker-volume при первом запуске.

## 10. Описание работы с данными
- Каталог формируется только из фактов первоисточников (primary_source, площадка, даты, цены).
- Рекомендации рассчитываются отдельно на основе семантического векторного сходства (384-мерные векторы, индекс HNSW) и hard-фильтров.
- Модель не генерирует вымышленные события.

## 11. Порядок работы с тестовыми данными
В репозитории подготовлен эталонный файл синтетических данных test-data/events.sample.json (согласно п. 10 Ограничений).
Загрузка в БД:
curl -X POST http://localhost:8000/api/dev/seed -H "Authorization: Bearer <ADMIN_TOKEN>"
или
curl -X POST http://localhost:8000/api/admin/ingest -H "Authorization: Bearer <ADMIN_TOKEN>" -H "Content-Type: application/json" --data @test-data/events.sample.json
Все тестовые события имеют отметку demo и плашку «Тестовые данные» в UI.

## 12. Пошаговый сценарий проверки
1. Проверка контейнеров: curl http://localhost:8000/health (ответ: HTTP 200 {"status":"ok"}).
2. Проверка API каталога: curl http://localhost:8000/api/v1/cities.
3. Открыть http://localhost:8080, выбрать город, пройти 5 вопросов анкеты и нажать «Показать события».
4. Проверить результат: отображение карточек с обоснованием причин рекомендации.
5. Проверить No-match: при взаимоисключающих фильтрах интерфейс выдает «По вашему запросу нет вариантов» и общую городскую ленту.

## 13. Примеры ожидаемого поведения системы
- Успешный подбор (HTTP 200): POST /api/v1/recommendations возвращает JSON со списком recommendations (поля id, title, score, reasons).
- Состояние No-match (HTTP 200): POST /api/v1/recommendations возвращает recommendations: [] и fallback_feed с флагом is_fallback: true.

## 14. Известные ограничения
- Первый запуск требует интернета для загрузки весов модели (~120 МБ).
- События без точного времени окончания (end_at) отсекаются строгим фильтром длительности.
- При недоступности внешних сайтов обновление каталога приостанавливается, но локальная БД продолжает отдавать события.
