import logging

from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types import CallbackButton
from maxapi.context import MemoryContext

from src.states import RegistrationState, ProfileState
from src.keyboards import (
    registered_keyboard,
    back_keyboard,
    back_and_skip_keyboard,
    gender_keyboard,
    profile_card_keyboard,
    children_list_keyboard,
    child_card_keyboard,
    confirm_delete_child_keyboard,
    adding_child_back_keyboard,
)
from src.handlers.profile import _profile_text, _child_text
from src.handlers.callbacks._common import _delete_step_mids, _append_step_mid
from src.db.connection import get_session_factory
from src.models import customer as customer_model
from src.models import child as child_model

logger = logging.getLogger(__name__)


async def _return_to_profile(bot, user_id: int, cust, context: MemoryContext) -> None:
    async with get_session_factory()() as session:
        children = await child_model.get_by_customer(session, cust.id)
    await context.set_state(RegistrationState.REGISTERED)
    await bot.send_message(
        user_id=user_id,
        text=_profile_text(cust, children),
        attachments=[profile_card_keyboard(cust.opt_out_marketing)],
    )


async def _send_children_list(bot, user_id: int, children: list) -> None:
    if children:
        await bot.send_message(
            user_id=user_id,
            text="👶 Ваши дети:",
            attachments=[children_list_keyboard(children)],
        )
    else:
        await bot.send_message(user_id=user_id, text="У вас пока нет детей в профиле.")


async def handle_profile_callback(
    bot, user_id: int, state: str, payload: str, context: MemoryContext, get_customer, event
) -> None:

    if payload == "profile:back":
        await context.set_state(RegistrationState.REGISTERED)
        await bot.send_message(user_id=user_id, text="Главное меню.", attachments=[registered_keyboard()])
        return

    if payload.startswith("profile:edit:"):
        field = payload[len("profile:edit:"):]
        cust = await get_customer()
        if cust is None:
            return
        await context.update_data(**{"edit.field": field})
        await context.set_state(ProfileState.EDITING_CUSTOMER_FIELD)
        labels = {
            "first_name": "Имя",
            "last_name": "Фамилия",
            "birthdate": "Дата рождения (ДД.ММ.ГГГГ)",
            "phone": "Телефон",
        }
        label = labels.get(field, field)
        current = getattr(cust, field, None) or "не указано"
        builder = InlineKeyboardBuilder()
        builder.row(CallbackButton(text="Оставить текущее", payload="profile:keep_field"))
        if field != "first_name":
            builder.row(CallbackButton(text="Очистить поле", payload=f"profile:clear:{field}"))
        builder.row(CallbackButton(text="← Назад", payload="profile:edit_back"))
        await bot.send_message(
            user_id=user_id,
            text=f"Введите новое значение — {label}:\nТекущее: {current}",
            attachments=[builder.as_markup()],
        )
        return

    if payload == "profile:keep_field":
        cust = await get_customer()
        if cust is None:
            return
        await _return_to_profile(bot, user_id, cust, context)
        return

    if payload.startswith("profile:clear:"):
        field = payload[len("profile:clear:"):]
        cust = await get_customer()
        if cust is None:
            return
        async with get_session_factory()() as session:
            async with session.begin():
                cust = await customer_model.update_field(session, cust.id, **{field: None})
                ch = await child_model.get_by_customer(session, cust.id)
        await context.set_state(RegistrationState.REGISTERED)
        await bot.send_message(
            user_id=user_id,
            text=_profile_text(cust, ch),
            attachments=[profile_card_keyboard(cust.opt_out_marketing)],
        )
        return

    if payload == "profile:edit_back":
        cust = await get_customer()
        if cust is None:
            return
        await _return_to_profile(bot, user_id, cust, context)
        return

    if payload in ("profile:opt_out", "profile:opt_in"):
        cust = await get_customer()
        if cust is None:
            return
        new_flag = payload == "profile:opt_out"
        async with get_session_factory()() as session:
            async with session.begin():
                cust = await customer_model.update_field(
                    session, cust.id, opt_out_marketing=new_flag
                )
                ch = await child_model.get_by_customer(session, cust.id)
        await bot.edit_message(
            message_id=event.message.body.mid,
            text=_profile_text(cust, ch),
            attachments=[profile_card_keyboard(cust.opt_out_marketing)],
        )
        return

    if payload == "profile:children":
        cust = await get_customer()
        if cust is None:
            return
        async with get_session_factory()() as session:
            children = await child_model.get_by_customer(session, cust.id)
        if children:
            await bot.send_message(
                user_id=user_id,
                text="👶 Ваши дети:",
                attachments=[children_list_keyboard(children)],
            )
        else:
            builder = InlineKeyboardBuilder()
            builder.row(CallbackButton(text="➕ Добавить ребёнка", payload="child:add"))
            builder.row(CallbackButton(text="← Назад к профилю", payload="children:back"))
            await bot.send_message(
                user_id=user_id,
                text="У вас пока нет детей в профиле.",
                attachments=[builder.as_markup()],
            )
        return

    if payload == "children:back":
        cust = await get_customer()
        if cust is None:
            return
        await _return_to_profile(bot, user_id, cust, context)
        return

    if payload.startswith("child:edit:") and "field" not in payload:
        child_id = int(payload.split(":")[-1])
        async with get_session_factory()() as session:
            ch = await child_model.get_by_id(session, child_id)
        if ch is None:
            await bot.send_message(user_id=user_id, text="Ребёнок не найден.")
            return
        await bot.send_message(
            user_id=user_id,
            text=_child_text(ch),
            attachments=[child_card_keyboard(child_id)],
        )
        return

    if payload.startswith("child:field:"):
        parts = payload.split(":")
        child_id = int(parts[2])
        child_field = parts[3]
        await context.update_data(**{"edit.child_id": child_id, "edit.child_field": child_field})
        await context.set_state(ProfileState.EDITING_CHILD_FIELD)
        if child_field == "gender":
            await bot.send_message(
                user_id=user_id, text="Выберите пол:", attachments=[gender_keyboard()]
            )
        else:
            labels = {"name": "Имя", "birthdate": "Дата рождения (ДД.ММ.ГГГГ)"}
            await bot.send_message(
                user_id=user_id,
                text=f"Введите новое значение — {labels.get(child_field, child_field)}:",
                attachments=[back_keyboard()],
            )
        return

    if payload.startswith("child:delete:"):
        child_id = int(payload.split(":")[-1])
        async with get_session_factory()() as session:
            ch = await child_model.get_by_id(session, child_id)
        name = ch.name if ch else str(child_id)
        await bot.send_message(
            user_id=user_id,
            text=f"Удалить {name} из профиля? Это действие нельзя отменить.",
            attachments=[confirm_delete_child_keyboard(child_id)],
        )
        return

    if payload.startswith("child:confirm_delete:"):
        child_id = int(payload.split(":")[-1])
        cust = await get_customer()
        try:
            async with get_session_factory()() as session:
                async with session.begin():
                    await child_model.delete(session, child_id)
                    children = await child_model.get_by_customer(session, cust.id)
        except Exception:
            logger.exception("Child delete failed")
            await bot.send_message(user_id=user_id, text="Не удалось удалить.")
            return
        await _send_children_list(bot, user_id, children)
        return

    if payload == "child:back_to_list":
        cust = await get_customer()
        if cust is None:
            return
        async with get_session_factory()() as session:
            children = await child_model.get_by_customer(session, cust.id)
        await _send_children_list(bot, user_id, children)
        return

    if payload == "child:add":
        await context.set_state(ProfileState.ADDING_CHILD_NAME)
        await context.update_data(step_mids=[])
        sent = await bot.send_message(
            user_id=user_id,
            text="Как зовут ребёнка?",
            attachments=[adding_child_back_keyboard()],
        )
        await _append_step_mid(context, sent.message.body.mid)
        return

    if payload == "child:add_cancel":
        cust = await get_customer()
        if cust is None:
            return
        await _delete_step_mids(bot, context)
        await context.set_state(RegistrationState.REGISTERED)
        async with get_session_factory()() as session:
            children = await child_model.get_by_customer(session, cust.id)
        await _send_children_list(bot, user_id, children)
        return

    if state == ProfileState.ADDING_CHILD_GENDER and payload.startswith("gender:"):
        gender = payload.split(":")[-1]
        await context.update_data(**{"new_child.gender": gender})
        await context.set_state(ProfileState.ADDING_CHILD_BIRTHDATE)
        sent = await bot.send_message(
            user_id=user_id,
            text="Когда день рождения у ребёнка? (ДД.ММ.ГГГГ)",
            attachments=[back_and_skip_keyboard("child:add_cancel")],
        )
        await _append_step_mid(context, sent.message.body.mid)
        return

    if state == ProfileState.ADDING_CHILD_BIRTHDATE and payload == "skip":
        cust = await get_customer()
        if cust is None:
            return
        data = await context.get_data()
        try:
            async with get_session_factory()() as session:
                async with session.begin():
                    await child_model.create(
                        session,
                        customer_id=cust.id,
                        name=data["new_child.name"],
                        gender=data["new_child.gender"],
                        birthdate=None,
                    )
                    children = await child_model.get_by_customer(session, cust.id)
        except Exception:
            logger.exception("Add child (no birthdate) failed")
            await bot.send_message(user_id=user_id, text="Ошибка. Попробуйте ещё раз.")
            return
        await _delete_step_mids(bot, context)
        await context.set_state(RegistrationState.REGISTERED)
        await bot.send_message(
            user_id=user_id,
            text="👶 Ваши дети:",
            attachments=[children_list_keyboard(children)],
        )
        return

    if state in (ProfileState.ADDING_CHILD_GENDER, ProfileState.ADDING_CHILD_BIRTHDATE) and payload == "back":
        if state == ProfileState.ADDING_CHILD_BIRTHDATE:
            await context.set_state(ProfileState.ADDING_CHILD_GENDER)
            sent = await bot.send_message(
                user_id=user_id,
                text="Ваш ребёнок — мальчик или девочка?",
                attachments=[gender_keyboard()],
            )
            await _append_step_mid(context, sent.message.body.mid)
        else:
            await context.set_state(ProfileState.ADDING_CHILD_NAME)
            sent = await bot.send_message(
                user_id=user_id,
                text="Как зовут ребёнка?",
                attachments=[adding_child_back_keyboard()],
            )
            await _append_step_mid(context, sent.message.body.mid)
        return

    if state == ProfileState.EDITING_CHILD_FIELD and payload.startswith("gender:"):
        data = await context.get_data()
        child_id = data.get("edit.child_id")
        gender = payload.split(":")[-1]
        try:
            async with get_session_factory()() as session:
                async with session.begin():
                    updated = await child_model.update_field(session, child_id, gender=gender)
        except Exception:
            logger.exception("Child gender update failed")
            return
        await context.set_state(RegistrationState.REGISTERED)
        await bot.send_message(
            user_id=user_id,
            text=_child_text(updated),
            attachments=[child_card_keyboard(child_id)],
        )
        return
