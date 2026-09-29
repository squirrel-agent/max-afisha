# MAX Integration

## Что реализовано в коде

- Frontend загружает MAX Bridge: `https://st.max.ru/js/max-web-app.js`.
- При старте внутри MAX frontend использует только строку `window.WebApp.initData` как подтверждение сессии; `initDataUnsafe` не используется для доверенной идентификации.
- `POST /api/max/session` проверяет подпись initData на backend с `MAX_BOT_TOKEN`, проверяет `auth_date`, затем привязывает MAX user id к локальному `users.max_user_id`.
- Реальный `MAX_BOT_TOKEN` не хранится в репозитории и передаётся только через environment.
- В обычном браузере остаётся локальный flow через `POST /api/users`, чтобы MVP можно было воспроизвести в Docker без эмуляции MAX.

## Настройка на стороне MAX

1. Развернуть mini-app по HTTPS.
2. Задать `MAX_BOT_TOKEN` в environment backend.
3. В настройках выданного бота подключить URL mini-app. Мини-приложение используется через бот, а не как отдельный изолированный сервис.
4. Открыть приложение из MAX и пройти основной сценарий.

Эта платформенная привязка является конфигурацией аккаунта/бота, поэтому не создаётся автоматически из исходного архива.

## Security

- Никогда не передавайте bot token во frontend.
- Не доверяйте полям `initDataUnsafe` без серверной проверки.
- По умолчанию initData старше 3600 секунд отклоняется (`MAX_INIT_DATA_MAX_AGE_SECONDS`).
- Для внешнего deployment используйте HTTPS и ограниченный `CORS_ORIGINS`.
- Рабочий токен храните в secret/environment storage платформы деплоя.

## Production bot transport

Если помимо кнопки открытия mini-app реализуется полноценный чат-сценарий, production transport бота следует настраивать по актуальной документации MAX (обычно webhook). Этот архив не имитирует несуществующую платформенную интеграцию: без фактической настройки бота в MAX локальный browser-flow остаётся dev-only способом проверки UI/API.
