from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types import (
    CallbackButton,
    ButtonsPayload,
    MessageButton,
    RequestContactButton,
)

REGISTER_BTN_TEXT = "Зарегистрироваться и получить скидку"
SHOW_DISCOUNT_BTN_TEXT = "Показать код на скидку"
MY_PROFILE_BTN_TEXT = "Мой профиль"


def unregistered_keyboard():
    return ButtonsPayload(buttons=[[MessageButton(text=REGISTER_BTN_TEXT)]]).pack()


def registered_keyboard():
    return ButtonsPayload(buttons=[
        [MessageButton(text=SHOW_DISCOUNT_BTN_TEXT)],
        [MessageButton(text=MY_PROFILE_BTN_TEXT)],
    ]).pack()


def registered_keyboard_with_contact():
    return ButtonsPayload(buttons=[
        [MessageButton(text=SHOW_DISCOUNT_BTN_TEXT)],
        [MessageButton(text=MY_PROFILE_BTN_TEXT)],
        [RequestContactButton(text="📱 Поделиться контактом [ТЕСТ]")],
    ]).pack()


def survey_offer_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="Пропустить", payload="survey:skip"),
        CallbackButton(text="Заполнить анкету", payload="survey:start"),
    )
    return builder.as_markup()


def back_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="← Назад", payload="back"))
    return builder.as_markup()


def gender_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="Мальчик", payload="gender:male"),
        CallbackButton(text="Девочка", payload="gender:female"),
    )
    builder.row(CallbackButton(text="← Назад", payload="back"))
    return builder.as_markup()


def yes_no_keyboard(yes_payload: str, no_payload: str):
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="Да", payload=yes_payload),
        CallbackButton(text="Нет", payload=no_payload),
    )
    builder.row(CallbackButton(text="← Назад", payload="back"))
    return builder.as_markup()


def discount_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="🏷 Показать скидку кассиру", payload="show_discount"))
    return builder.as_markup()
