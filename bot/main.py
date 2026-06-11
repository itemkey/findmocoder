import asyncio
from contextlib import suppress
import html
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.filters.command import CommandObject
from aiogram.types import CallbackQuery, Message

from bot.config import Config, load_config
from bot.database import Database, Film, normalize_code
from bot.keyboards import (
    BTN_ADD_FILM,
    BTN_ENTER_CODE,
    BTN_FILMS,
    BTN_HELP,
    CHECK_SUBSCRIPTION_CALLBACK,
    channel_keyboard,
    main_menu_keyboard,
    subscription_keyboard,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

router = Router()

SUBSCRIBED_STATUSES = {"member", "administrator", "creator"}


class SubscriptionCheckError(Exception):
    pass


def is_admin(config: Config, user_id: int | None) -> bool:
    return user_id is not None and user_id in config.admin_ids


def user_is_admin(message: Message, config: Config) -> bool:
    return is_admin(config, message.from_user.id if message.from_user else None)


def menu_for_message(message: Message, config: Config):
    return main_menu_keyboard(user_is_admin(message, config))


def status_value(status: object) -> str:
    return str(getattr(status, "value", status))


async def is_user_subscribed(bot: Bot, config: Config, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(
            chat_id=config.required_channel_username,
            user_id=user_id,
        )
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.exception("Could not check subscription")
        raise SubscriptionCheckError(str(exc)) from exc

    return status_value(member.status) in SUBSCRIBED_STATUSES


async def send_movie(message: Message, config: Config, film: Film) -> None:
    text = (
        f"Название фильма: <b>{html.escape(film.title)}</b>\n\n"
        f"{html.escape(config.promo_text)}"
    )
    await message.answer(text, reply_markup=channel_keyboard(config.required_channel_url))


async def ask_to_subscribe(message: Message, config: Config) -> None:
    await message.answer(
        "Чтобы получить название фильма, подпишись на канал и нажми кнопку проверки.",
        reply_markup=subscription_keyboard(config.required_channel_url),
    )


async def handle_subscription_error(message: Message) -> None:
    await message.answer(
        "Не получилось проверить подписку. Проверь, что бот добавлен администратором "
        "в обязательный канал, и попробуй еще раз."
    )


@router.message(CommandStart())
async def start_handler(message: Message, config: Config) -> None:
    await message.answer(
        "Привет! Отправь мне код фильма, который ты увидел в YouTube, и я покажу название.",
        reply_markup=menu_for_message(message, config),
    )


async def send_help(message: Message, config: Config) -> None:
    is_admin_user = user_is_admin(message, config)
    text = (
        "Как пользоваться ботом:\n"
        "1. Отправь код фильма из YouTube.\n"
        "2. Подпишись на канал, если бот попросит.\n"
        "3. Нажми кнопку проверки подписки и получи название."
    )

    if is_admin_user:
        text += (
            "\n\nАдмин-команды:\n"
            "/add CODE Название фильма\n"
            "/delete CODE\n"
            "/films\n"
            "/help_admin\n\n"
            "Пример: /add A123 Интерстеллар"
        )

    await message.answer(text, reply_markup=main_menu_keyboard(is_admin_user))


@router.message(Command("help"))
async def help_handler(message: Message, config: Config) -> None:
    await send_help(message, config)


@router.message(Command("id"))
async def id_handler(message: Message, config: Config) -> None:
    if message.from_user is None:
        return

    await message.answer(
        f"Твой Telegram ID: <code>{message.from_user.id}</code>",
        reply_markup=menu_for_message(message, config),
    )


@router.message(F.text == BTN_ENTER_CODE)
async def enter_code_button_handler(message: Message, config: Config) -> None:
    await message.answer(
        "Отправь код фильма одним сообщением.",
        reply_markup=menu_for_message(message, config),
    )


@router.message(F.text == BTN_HELP)
async def help_button_handler(message: Message, config: Config) -> None:
    await send_help(message, config)


@router.message(F.text == BTN_ADD_FILM)
async def add_film_button_handler(message: Message, config: Config) -> None:
    if not user_is_admin(message, config):
        await message.answer(
            "Эта кнопка доступна только администратору.",
            reply_markup=menu_for_message(message, config),
        )
        return

    await message.answer(
        "Чтобы добавить фильм, отправь:\n/add CODE Название фильма\n\n"
        "Например:\n/add A123 Интерстеллар",
        reply_markup=menu_for_message(message, config),
    )


@router.message(Command("help_admin"))
async def admin_help_handler(message: Message, config: Config) -> None:
    if not is_admin(config, message.from_user.id if message.from_user else None):
        await message.answer(
            "Эта команда доступна только администратору.",
            reply_markup=menu_for_message(message, config),
        )
        return

    await message.answer(
        "Админ-команды:\n"
        "/add CODE Название фильма - добавить или обновить фильм\n"
        "/delete CODE - удалить фильм\n"
        "/films - показать список фильмов\n"
        "/help_admin - показать эту подсказку",
        reply_markup=menu_for_message(message, config),
    )


@router.message(Command("add"))
async def add_film_handler(
    message: Message,
    command: CommandObject,
    config: Config,
    db: Database,
) -> None:
    if not is_admin(config, message.from_user.id if message.from_user else None):
        await message.answer(
            "Эта команда доступна только администратору.",
            reply_markup=menu_for_message(message, config),
        )
        return

    args = command.args or ""
    parts = args.split(maxsplit=1)

    if len(parts) != 2:
        await message.answer(
            "Использование: /add CODE Название фильма",
            reply_markup=menu_for_message(message, config),
        )
        return

    code, title = parts

    try:
        film = await db.add_film(code, title)
    except ValueError as exc:
        await message.answer(str(exc), reply_markup=menu_for_message(message, config))
        return

    await message.answer(
        f"Фильм сохранен: {html.escape(film.code)} - {html.escape(film.title)}",
        reply_markup=menu_for_message(message, config),
    )


@router.message(Command("delete"))
async def delete_film_handler(
    message: Message,
    command: CommandObject,
    config: Config,
    db: Database,
) -> None:
    if not is_admin(config, message.from_user.id if message.from_user else None):
        await message.answer(
            "Эта команда доступна только администратору.",
            reply_markup=menu_for_message(message, config),
        )
        return

    code = normalize_code(command.args or "")
    if not code:
        await message.answer(
            "Использование: /delete CODE",
            reply_markup=menu_for_message(message, config),
        )
        return

    deleted = await db.delete_film(code)
    if deleted:
        await message.answer(
            f"Фильм с кодом {html.escape(code)} удален.",
            reply_markup=menu_for_message(message, config),
        )
    else:
        await message.answer(
            f"Фильм с кодом {html.escape(code)} не найден.",
            reply_markup=menu_for_message(message, config),
        )


@router.message(Command("films"))
async def list_films_handler(message: Message, config: Config, db: Database) -> None:
    if not is_admin(config, message.from_user.id if message.from_user else None):
        await message.answer(
            "Эта команда доступна только администратору.",
            reply_markup=menu_for_message(message, config),
        )
        return

    films = await db.list_films()
    if not films:
        await message.answer(
            "Список фильмов пуст. Добавь первый фильм командой /add.",
            reply_markup=menu_for_message(message, config),
        )
        return

    lines = ["Список фильмов:"]
    lines.extend(
        f"{html.escape(film.code)} - {html.escape(film.title)}" for film in films
    )
    text = "\n".join(lines)

    for start in range(0, len(text), 3500):
        await message.answer(
            text[start : start + 3500],
            reply_markup=menu_for_message(message, config),
        )


@router.message(F.text == BTN_FILMS)
async def films_button_handler(message: Message, config: Config, db: Database) -> None:
    await list_films_handler(message, config, db)


@router.message(F.text)
async def movie_code_handler(
    message: Message,
    bot: Bot,
    config: Config,
    db: Database,
) -> None:
    if not message.from_user or not message.text:
        return

    code = normalize_code(message.text)
    if not code:
        await message.answer(
            "Отправь код фильма текстом.",
            reply_markup=menu_for_message(message, config),
        )
        return

    if code.startswith("/"):
        await message.answer(
            "Неизвестная команда. Отправь код фильма или нажми /start.",
            reply_markup=menu_for_message(message, config),
        )
        return

    film = await db.get_film(code)
    if film is None:
        await message.answer(
            "Такого кода нет. Проверь код и отправь его еще раз.",
            reply_markup=menu_for_message(message, config),
        )
        return

    try:
        subscribed = await is_user_subscribed(bot, config, message.from_user.id)
    except SubscriptionCheckError:
        await handle_subscription_error(message)
        return

    if not subscribed:
        await db.set_pending_code(message.from_user.id, film.code)
        await ask_to_subscribe(message, config)
        return

    await db.clear_pending_code(message.from_user.id)
    await send_movie(message, config, film)


@router.callback_query(F.data == CHECK_SUBSCRIPTION_CALLBACK)
async def check_subscription_handler(
    callback: CallbackQuery,
    bot: Bot,
    config: Config,
    db: Database,
) -> None:
    if not callback.from_user or not callback.message:
        await callback.answer()
        return

    pending_code = await db.get_pending_code(callback.from_user.id)
    if pending_code is None:
        await callback.answer("Сначала отправь код фильма.", show_alert=True)
        return

    try:
        subscribed = await is_user_subscribed(bot, config, callback.from_user.id)
    except SubscriptionCheckError:
        await callback.answer()
        await handle_subscription_error(callback.message)
        return

    if not subscribed:
        await callback.answer("Подписка пока не найдена.", show_alert=True)
        return

    film = await db.get_film(pending_code)
    if film is None:
        await db.clear_pending_code(callback.from_user.id)
        await callback.answer()
        await callback.message.answer(
            "Этот код больше не доступен. Отправь новый код фильма."
        )
        return

    await db.clear_pending_code(callback.from_user.id)

    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(reply_markup=None)

    await callback.answer("Подписка подтверждена.")
    await send_movie(callback.message, config, film)


async def main() -> None:
    config = load_config()
    db = Database(config.database_path)
    await db.init()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(config=config, db=db)
    dp.include_router(router)

    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
