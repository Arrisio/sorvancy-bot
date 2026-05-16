import re
import logging
from datetime import date

from maxapi.types import MessageCreated, MessageCallback
from maxapi.filters import F
from maxapi.context import MemoryContext

from src.states import RegistrationState
from src.keyboards import (
    gender_keyboard,
    yes_no_keyboard,
    registered_keyboard,
    registered_keyboard_with_contact,
    unregistered_keyboard,
    survey_offer_keyboard,
    back_keyboard,
    REGISTER_BTN_TEXT,
)
from src.db.connection import get_session_factory
from src.models import customer as customer_model
from src.models import child as child_model
from src.services.discount import registration_complete_message, survey_offer_message
import config

logger = logging.getLogger(__name__)


def _parse_date(text: str) -> date | None:
    parts = [p for p in re.split(r"\D+", text.strip()) if p]
    if len(parts) != 3:
        return None
    d, m, y = parts
    try:
        return date(int(y), int(m), int(d))
    except ValueError:
        return None


async def register_registration_handlers(dp):

    @dp.message_created(F.message.body.text == REGISTER_BTN_TEXT)
    async def on_register_button(event: MessageCreated, context: MemoryContext):
        user_id = event.message.sender.user_id
        username = getattr(event.message.sender, "name", None)

        async with get_session_factory()() as session:
            existing = await customer_model.get_by_max_id(session, user_id)
        if existing:
            await event.message.answer(
                "Вы уже зарегистрированы!",
                attachments=[registered_keyboard()],
            )
            return

        try:
            async with get_session_factory()() as session:
                async with session.begin():
                    await customer_model.create(
                        session,
                        max_user_id=user_id,
                        max_username=username,
                        discount_percent=config.DISCOUNT_PERCENT,
                    )
            logger.info("Registered max_user_id=%s (minimal)", user_id)
        except Exception:
            logger.exception("Registration failed for max_user_id=%s", user_id)
            await event.message.answer(
                "Ошибка при регистрации. Попробуйте позже.",
                attachments=[unregistered_keyboard()],
            )
            return

        await context.clear()
        await context.update_data(max_user_id=user_id, max_username=username, children=[])
        await context.set_state(RegistrationState.REGISTERED)

        await event.bot.send_message(
            user_id=user_id,
            text=registration_complete_message(),
            attachments=[registered_keyboard_with_contact()],
        )

        sended = await event.bot.send_message(
            user_id=user_id,
            text=survey_offer_message(),
            attachments=[survey_offer_keyboard()],
        )
        try:
            await context.update_data(survey_offer_mid=sended.message.mid)
        except Exception:
            logger.debug("Could not store survey offer message id")

    @dp.message_created(F.message.body.text)
    async def handle_text(event: MessageCreated, context: MemoryContext):
        state = await context.get_state()
        text = event.message.body.text.strip()

        if state == RegistrationState.AWAITING_FIRST_NAME:
            await context.update_data(first_name=text)
            await context.set_state(RegistrationState.AWAITING_CUSTOMER_BIRTHDATE)
            await event.message.answer(
                "Ваша дата рождения? (ДД.ММ.ГГГГ)",
                attachments=[back_keyboard()],
            )

        elif state == RegistrationState.AWAITING_CUSTOMER_BIRTHDATE:
            bd = _parse_date(text)
            if bd is None:
                await event.message.answer(
                    "Не понял дату. Введите в формате ДД.ММ.ГГГГ (разделитель любой):",
                    attachments=[back_keyboard()],
                )
                return
            await context.update_data(customer_birthdate=str(bd))
            await context.set_state(RegistrationState.AWAITING_CHILD_NAME)
            await event.message.answer(
                "Расскажите о ребёнке, для которого покупаете одежду.\n\nКак зовут ребёнка?",
                attachments=[back_keyboard()],
            )

        elif state == RegistrationState.AWAITING_CHILD_NAME:
            await context.update_data(current_child_name=text)
            await context.set_state(RegistrationState.AWAITING_CHILD_GENDER)
            await event.message.answer("Пол ребёнка?", attachments=[gender_keyboard()])

        elif state == RegistrationState.AWAITING_CHILD_BIRTHDATE:
            bd = _parse_date(text)
            if bd is None:
                await event.message.answer(
                    "Не понял дату. Введите в формате ДД.ММ.ГГГГ (разделитель любой):",
                    attachments=[back_keyboard()],
                )
                return
            await context.update_data(current_child_birthdate=str(bd))
            await context.set_state(RegistrationState.AWAITING_MORE_CHILDREN)
            await event.message.answer(
                "Добавить ещё одного ребёнка?",
                attachments=[yes_no_keyboard("more_children:yes", "more_children:no")],
            )

    @dp.message_callback()
    async def handle_callback(event: MessageCallback, context: MemoryContext):
        payload = event.callback.payload
        state = await context.get_state()
        user_id = event.callback.user.user_id
        await event.bot.send_callback(callback_id=event.callback.callback_id, notification="Принято")

        if payload == "survey:start":
            if state != RegistrationState.REGISTERED:
                async with get_session_factory()() as session:
                    customer = await customer_model.get_by_max_id(session, user_id)
                if not customer:
                    logger.warning("survey:start but user %s not registered, state=%s", user_id, state)
                    return
                await context.update_data(max_user_id=user_id, max_username=None, children=[])
                await context.set_state(RegistrationState.REGISTERED)
            await _delete_survey_offer(event.bot, context)
            await context.set_state(RegistrationState.AWAITING_FIRST_NAME)
            await event.bot.send_message(
                user_id=user_id,
                text="Как вас зовут? (Введите имя)",
                attachments=[back_keyboard()],
            )

        elif payload == "survey:skip":
            await _delete_survey_offer(event.bot, context)

        elif payload == "back":
            await _handle_back(event.bot, user_id, state, context)

        elif state == RegistrationState.AWAITING_CHILD_GENDER and payload.startswith("gender:"):
            gender = payload.split(":")[1]
            await context.update_data(current_child_gender=gender)
            await context.set_state(RegistrationState.AWAITING_CHILD_BIRTHDATE)
            await event.bot.send_message(
                user_id=user_id,
                text="Дата рождения ребёнка (ДД.ММ.ГГГГ, разделитель любой):",
                attachments=[back_keyboard()],
            )

        elif state == RegistrationState.AWAITING_MORE_CHILDREN and payload.startswith("more_children:"):
            await _commit_current_child(context)
            if payload.endswith("yes"):
                await context.update_data(
                    current_child_name=None,
                    current_child_gender=None,
                    current_child_birthdate=None,
                )
                await context.set_state(RegistrationState.AWAITING_CHILD_NAME)
                await event.bot.send_message(
                    user_id=user_id,
                    text="Имя следующего ребёнка?",
                    attachments=[back_keyboard()],
                )
            else:
                await _complete_survey(event.bot, user_id, context)

    async def _delete_survey_offer(bot, context: MemoryContext):
        data = await context.get_data()
        mid = data.get("survey_offer_mid")
        if mid:
            try:
                await bot.delete_message(message_id=mid)
            except Exception:
                logger.debug("Could not delete survey offer message %s", mid)

    async def _handle_back(bot, user_id: int, state: str, context: MemoryContext):
        data = await context.get_data()

        if state == RegistrationState.AWAITING_FIRST_NAME:
            await context.set_state(RegistrationState.REGISTERED)
            await bot.send_message(
                user_id=user_id,
                text="Анкета отменена. Вы можете заполнить её позже.",
                attachments=[registered_keyboard()],
            )

        elif state == RegistrationState.AWAITING_CUSTOMER_BIRTHDATE:
            await context.set_state(RegistrationState.AWAITING_FIRST_NAME)
            await bot.send_message(
                user_id=user_id,
                text="Как вас зовут? (Введите имя)",
                attachments=[back_keyboard()],
            )

        elif state == RegistrationState.AWAITING_CHILD_NAME:
            children = data.get("children", [])
            if children:
                # re-ask "add more children?" for the last committed child
                await context.set_state(RegistrationState.AWAITING_MORE_CHILDREN)
                await bot.send_message(
                    user_id=user_id,
                    text="Добавить ещё одного ребёнка?",
                    attachments=[yes_no_keyboard("more_children:yes", "more_children:no")],
                )
            else:
                await context.set_state(RegistrationState.AWAITING_CUSTOMER_BIRTHDATE)
                await bot.send_message(
                    user_id=user_id,
                    text="Ваша дата рождения? (ДД.ММ.ГГГГ)",
                    attachments=[back_keyboard()],
                )

        elif state == RegistrationState.AWAITING_CHILD_GENDER:
            await context.set_state(RegistrationState.AWAITING_CHILD_NAME)
            await bot.send_message(
                user_id=user_id,
                text="Как зовут ребёнка?",
                attachments=[back_keyboard()],
            )

        elif state == RegistrationState.AWAITING_CHILD_BIRTHDATE:
            await context.set_state(RegistrationState.AWAITING_CHILD_GENDER)
            await bot.send_message(
                user_id=user_id,
                text="Пол ребёнка?",
                attachments=[gender_keyboard()],
            )

        elif state == RegistrationState.AWAITING_MORE_CHILDREN:
            await context.set_state(RegistrationState.AWAITING_CHILD_BIRTHDATE)
            await bot.send_message(
                user_id=user_id,
                text="Дата рождения ребёнка (ДД.ММ.ГГГГ, разделитель любой):",
                attachments=[back_keyboard()],
            )

    async def _commit_current_child(context: MemoryContext):
        data = await context.get_data()
        child = {
            "name": data["current_child_name"],
            "gender": data["current_child_gender"],
            "birthdate": data["current_child_birthdate"],
        }
        children = data.get("children", [])
        children.append(child)
        await context.update_data(children=children)

    async def _complete_survey(bot, user_id: int, context: MemoryContext):
        data = await context.get_data()
        try:
            async with get_session_factory()() as session:
                async with session.begin():
                    customer = await customer_model.update_survey_data(
                        session,
                        max_user_id=data["max_user_id"],
                        first_name=data["first_name"],
                        birthdate=(
                            date.fromisoformat(data["customer_birthdate"])
                            if data.get("customer_birthdate")
                            else None
                        ),
                    )
                    for child_data in data.get("children", []):
                        await child_model.create(
                            session,
                            customer_id=customer.id,
                            name=child_data["name"],
                            gender=child_data["gender"],
                            birthdate=date.fromisoformat(child_data["birthdate"]),
                        )
            logger.info(
                "Survey completed for max_user_id=%s, children=%d",
                user_id,
                len(data.get("children", [])),
            )
        except Exception:
            logger.exception("Survey save failed for max_user_id=%s", user_id)
            await bot.send_message(
                user_id=user_id,
                text="Ошибка при сохранении. Попробуйте /start снова.",
                attachments=[registered_keyboard()],
            )
            return

        await context.set_state(RegistrationState.REGISTERED)
        await bot.send_message(
            user_id=user_id,
            text="Анкета заполнена! Спасибо 🎉\nТеперь ваша скидка увеличена.",
            attachments=[registered_keyboard()],
        )
