import logging

from datetime import datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def str_to_date(value: str) -> datetime.date:
    if isinstance(value, str):
        date_formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
        ]
        for date_format in date_formats:
            try:
                return datetime.strptime(value, date_format)
            except ValueError:
                continue
        logging.error(f"Failed to convert '{value}' to date")
    return None


def split_message(message, max_length=4096):
    """
    Разбивка сообщений на куски, разрешенного для отправки размера по умолчанию
    это 4096 символов
    """
    if len(message) <= max_length:
        return [message]

    title_break = message.find("\n\n")
    if title_break != -1:
        title = message[: title_break + 2]
        message_body = message[title_break + 2 :]
    else:
        title = ""
        message_body = message

    lines = message_body.split("\n")
    chunks = []
    current_chunk = title

    for line in lines:
        if len(current_chunk) + len(line) + 1 > max_length:
            chunks.append(current_chunk)
            current_chunk = line
        else:
            if current_chunk != title:
                current_chunk += "\n"
            current_chunk += line
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def create_inline_kb(
    width: int, *args: str, **kwargs: str
) -> InlineKeyboardMarkup:
    kb_builder: InlineKeyboardBuilder = InlineKeyboardBuilder()
    buttons: list[InlineKeyboardButton] = []
    if args:
        for button in args:
            buttons.append(
                InlineKeyboardButton(
                    text=button,
                    callback_data=button,
                )
            )
    if kwargs:
        for button, text in kwargs.items():
            buttons.append(
                InlineKeyboardButton(text=text, callback_data=button)
            )

    kb_builder.row(*buttons, width=width)
    return kb_builder.as_markup()
