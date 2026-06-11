# Telegram-Бот Для Кодов Фильмов

Бот принимает код фильма из YouTube, проверяет подписку пользователя на обязательный Telegram-канал и после подтверждения отправляет название фильма с рекламным текстом и ссылкой на канал.

## Что нужно заранее

1. Создать бота через [@BotFather](https://t.me/BotFather) и получить `BOT_TOKEN`.
2. Создать публичный канал, например `@my_channel`.
3. Добавить бота администратором в этот канал. Без этого Telegram может не дать проверить подписку.
4. Узнать свой Telegram user ID через бота вроде [@userinfobot](https://t.me/userinfobot).

## Быстрый запуск локально

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Заполни `.env` своими значениями:

```env
BOT_TOKEN=токен_от_BotFather
ADMIN_IDS=твой_telegram_id,id_второго_админа
REQUIRED_CHANNEL_USERNAME=@имя_канала
REQUIRED_CHANNEL_URL=https://t.me/имя_канала
PROMO_TEXT=Больше подборок фильмов и новых кодов ищи в нашем канале.
DATABASE_PATH=data/bot.sqlite3
TELEGRAM_REQUEST_TIMEOUT=90
POLLING_RETRY_DELAY=15
TELEGRAM_FORCE_IPV4=false
TELEGRAM_PROXY_URL=
```

Запуск:

```bash
python -m bot.main
```

## Запуск 24/7 на VPS через Docker

На сервере установи Docker и Docker Compose, скопируй проект, создай `.env` из примера и запусти:

```bash
docker compose up -d --build
```

Посмотреть логи:

```bash
docker compose logs -f
```

Если в логах есть `TelegramNetworkError: Request timeout error`, контейнер не может
достучаться до Telegram Bot API. Проверь доступ к `https://api.telegram.org` именно
с VPS или из контейнера:

```bash
docker compose exec movie-code-bot python -c "import urllib.request; print(urllib.request.urlopen('https://api.telegram.org', timeout=10).status)"
```

При временных сетевых сбоях бот будет ждать `POLLING_RETRY_DELAY` секунд и
запускать polling повторно.

Если VPS открывает Telegram только по IPv4, поставь в `.env`:

```env
TELEGRAM_FORCE_IPV4=true
```

Если у провайдера VPS заблокирован или не маршрутизируется Telegram Bot API,
укажи прокси:

```env
TELEGRAM_PROXY_URL=socks5://user:password@host:port
```

Подойдут `socks4://`, `socks5://`, `http://` и `https://` прокси.

Остановить:

```bash
docker compose down
```

База SQLite хранится в папке `data`, которая подключена в контейнер как volume. После перезапуска данные сохраняются.

## Админ-команды

Команды доступны только пользователям из `ADMIN_IDS`. Если админов несколько, укажи ID через запятую:

```env
ADMIN_IDS=123456789,987654321
```

```text
/add CODE Название фильма
/delete CODE
/films
/help_admin
/help
/id
```

Примеры:

```text
/add A123 Интерстеллар
/add 777 Бойцовский клуб
/delete A123
```

Коды сохраняются без учета регистра: `a123`, `A123` и `A123 ` считаются одним кодом.

Команда `/id` показывает твой Telegram ID, чтобы его можно было добавить в `ADMIN_IDS`.

## Пользовательский сценарий

1. Пользователь открывает бота и отправляет код фильма.
2. Если код есть в базе, бот проверяет подписку на канал.
3. Если подписки нет, бот показывает кнопки `Подписаться на канал` и `Проверить подписку`.
4. После подписки пользователь нажимает `Проверить подписку`.
5. Бот отправляет название фильма, рекламный текст и кнопку перехода в канал.

## Нижние кнопки бота

Бот показывает обычную Telegram-клавиатуру под полем ввода.

Для всех пользователей:

```text
Ввести код
Помощь
```

Для админов дополнительно:

```text
Добавить фильм
Список фильмов
```
