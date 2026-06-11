from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


CHECK_SUBSCRIPTION_CALLBACK = "check_subscription"
BTN_ENTER_CODE = "Ввести код"
BTN_HELP = "Помощь"
BTN_ADD_FILM = "Добавить фильм"
BTN_FILMS = "Список фильмов"


def main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text=BTN_ENTER_CODE), KeyboardButton(text=BTN_HELP)],
    ]

    if is_admin:
        keyboard.insert(
            1,
            [KeyboardButton(text=BTN_ADD_FILM), KeyboardButton(text=BTN_FILMS)],
        )

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Отправь код фильма",
    )


def subscription_keyboard(channel_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подписаться на канал", url=channel_url)],
            [
                InlineKeyboardButton(
                    text="Проверить подписку",
                    callback_data=CHECK_SUBSCRIPTION_CALLBACK,
                )
            ],
        ]
    )


def channel_keyboard(channel_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Перейти в канал", url=channel_url)],
        ]
    )
