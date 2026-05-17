from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types import (
    CallbackButton,
    ButtonsPayload,
    MessageButton,
    RequestContactButton,
)

# --- Reply keyboard button labels ---
REGISTER_BTN_TEXT = "Зарегистрироваться и получить скидку"
DISCOUNT_BTN_TEXT = "Скидка"
MY_PROFILE_BTN_TEXT = "Мой профиль"
CONTACT_STAFF_BTN_TEXT = "Связаться с продавцом"

STAFF_FIND_BTN_TEXT = "Найти профиль"
EXCEL_BTN_TEXT = "Excel"
STAFF_LIST_BTN_TEXT = "Показать продавцов"
ADD_SELLER_BTN_TEXT = "Добавить продавца"
BROADCAST_CREATE_BTN_TEXT = "Запустить рассылку"
BROADCAST_LIST_BTN_TEXT = "Запланированные рассылки"


# --- Persistent reply keyboards ---

def unregistered_keyboard():
    return ButtonsPayload(buttons=[[MessageButton(text=REGISTER_BTN_TEXT)]]).pack()


def registered_keyboard():
    return ButtonsPayload(buttons=[
        [MessageButton(text=MY_PROFILE_BTN_TEXT)],
        [MessageButton(text=DISCOUNT_BTN_TEXT)],
        [MessageButton(text=CONTACT_STAFF_BTN_TEXT)],
    ]).pack()


def registered_keyboard_with_contact():
    return ButtonsPayload(buttons=[
        [MessageButton(text=MY_PROFILE_BTN_TEXT)],
        [MessageButton(text=DISCOUNT_BTN_TEXT)],
        [MessageButton(text=CONTACT_STAFF_BTN_TEXT)],
    ]).pack()


def staff_keyboard():
    return ButtonsPayload(buttons=[
        [MessageButton(text=STAFF_FIND_BTN_TEXT)],
    ]).pack()


def superuser_keyboard():
    return ButtonsPayload(buttons=[
        [MessageButton(text=STAFF_FIND_BTN_TEXT)],
        [MessageButton(text=EXCEL_BTN_TEXT)],
        [MessageButton(text=STAFF_LIST_BTN_TEXT), MessageButton(text=ADD_SELLER_BTN_TEXT)],
        [MessageButton(text=BROADCAST_CREATE_BTN_TEXT)],
        [MessageButton(text=BROADCAST_LIST_BTN_TEXT)],
    ]).pack()


# --- Transient / inline keyboards ---

def survey_offer_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="Пропустить", payload="survey:skip"),
        CallbackButton(text="Заполнить анкету", payload="survey:start"),
    )
    return builder.as_markup()


def resume_survey_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="▶️ Продолжить", payload="survey:resume"),
        CallbackButton(text="🔄 Начать заново", payload="survey:restart"),
    )
    return builder.as_markup()


def back_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="← Назад", payload="back"))
    return builder.as_markup()


def back_and_skip_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="Пропустить", payload="skip"),
        CallbackButton(text="← Назад", payload="back"),
    )
    return builder.as_markup()


def gender_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="Мальчик", payload="gender:male"),
        CallbackButton(text="Девочка", payload="gender:female"),
    )
    builder.row(CallbackButton(text="← Назад", payload="back"))
    return builder.as_markup()


def buy_for_self_keyboard():
    """Step 4 — child name — with optional 'buy for self' when 0 children."""
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="Купить для себя", payload="buy_for_self"))
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


def confirmation_card_keyboard(has_children: bool):
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="✏️ Имя", payload="edit:first_name"),
        CallbackButton(text="✏️ Фамилия", payload="edit:last_name"),
    )
    builder.row(
        CallbackButton(text="✏️ Дата рождения", payload="edit:birthdate"),
    )
    if has_children:
        builder.row(CallbackButton(text="👶 Дети", payload="edit:children"))
    builder.row(CallbackButton(text="✅ Сохранить", payload="confirm:save"))
    return builder.as_markup()


def contact_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(RequestContactButton(text="📞 Запрос контактов"))
    builder.row(
        CallbackButton(text="Завершить заполнение анкеты", payload="contact:skip"),
    )
    builder.row(CallbackButton(text="← Назад", payload="back"))
    return builder.as_markup()


def profile_card_keyboard(opt_out: bool):
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="✏️ Имя", payload="profile:edit:first_name"),
        CallbackButton(text="✏️ Фамилия", payload="profile:edit:last_name"),
    )
    builder.row(
        CallbackButton(text="✏️ Дата рождения", payload="profile:edit:birthdate"),
        CallbackButton(text="✏️ Телефон", payload="profile:edit:phone"),
    )
    builder.row(CallbackButton(text="👶 Управление детьми", payload="profile:children"))
    if opt_out:
        builder.row(CallbackButton(text="Получать рассылки", payload="profile:opt_in"))
    else:
        builder.row(CallbackButton(text="Отказаться от рассылок", payload="profile:opt_out"))
    builder.row(CallbackButton(text="← Главное меню", payload="profile:back"))
    return builder.as_markup()


def children_list_keyboard(children):
    builder = InlineKeyboardBuilder()
    for ch in children:
        builder.row(
            CallbackButton(text=f"✏️ {ch.name}", payload=f"child:edit:{ch.id}")
        )
    builder.row(CallbackButton(text="➕ Добавить ребёнка", payload="child:add"))
    builder.row(CallbackButton(text="← Назад к профилю", payload="children:back"))
    return builder.as_markup()


def child_card_keyboard(child_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="✏️ Имя", payload=f"child:field:{child_id}:name"),
        CallbackButton(text="✏️ Пол", payload=f"child:field:{child_id}:gender"),
        CallbackButton(text="✏️ Дата р.", payload=f"child:field:{child_id}:birthdate"),
    )
    builder.row(CallbackButton(text="🗑 Удалить", payload=f"child:delete:{child_id}"))
    builder.row(CallbackButton(text="← Назад к списку", payload="child:back_to_list"))
    return builder.as_markup()


def confirm_delete_child_keyboard(child_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="✅ Да, удалить", payload=f"child:confirm_delete:{child_id}"),
        CallbackButton(text="← Отмена", payload=f"child:edit:{child_id}"),
    )
    return builder.as_markup()


def adding_child_back_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="← Отмена", payload="child:add_cancel"))
    return builder.as_markup()


def staff_profile_keyboard(customer_id: int, coupons):
    builder = InlineKeyboardBuilder()
    for c in coupons:
        builder.row(
            CallbackButton(
                text=f"Купон «{c.type}» — {c.value} ₽",
                payload=f"coupon:redeem:{c.id}",
            )
        )
    builder.row(
        CallbackButton(
            text="Изменить % скидки",
            payload=f"discount:edit:{customer_id}",
        )
    )
    builder.row(
        CallbackButton(
            text="Выдать купон",
            payload=f"coupon:issue:{customer_id}",
        )
    )
    return builder.as_markup()


def confirm_coupon_keyboard(coupon_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="Да", payload=f"coupon:confirm:{coupon_id}"),
        CallbackButton(text="Нет", payload="coupon:cancel"),
    )
    return builder.as_markup()


def delete_seller_keyboard(staff_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="Удалить", payload=f"seller:delete:{staff_id}")
    )
    return builder.as_markup()


def confirm_delete_seller_keyboard(staff_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="✅ Да, удалить", payload=f"seller:confirm_delete:{staff_id}"),
        CallbackButton(text="← Отмена", payload="seller:cancel_delete"),
    )
    return builder.as_markup()


def empty_profile_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="Заполнить анкету", payload="survey:start"))
    builder.row(CallbackButton(text="← Главное меню", payload="profile:back"))
    return builder.as_markup()


def cancel_keyboard(cancel_payload: str = "cancel"):
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="Отмена", payload=cancel_payload))
    return builder.as_markup()


def broadcast_start_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="Начать в ближайшее время", payload="broadcast:soonest"),
        CallbackButton(text="Отмена", payload="broadcast:cancel"),
    )
    return builder.as_markup()


def cancel_broadcast_keyboard(broadcast_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="Отменить", payload=f"broadcast:cancel:{broadcast_id}")
    )
    return builder.as_markup()
