import io
import logging
from datetime import datetime, timezone

from maxapi.types import MessageCreated
from maxapi.types.input_media import InputMediaBuffer
from maxapi.filters import F
from maxapi.context import MemoryContext

from src.keyboards import EXCEL_BTN_TEXT
from src.db.connection import get_session_factory
from src.models import customer as customer_model
from src.models import child as child_model
from src.models import coupon as coupon_model
from src.db.orm import Staff, Customer, Child

logger = logging.getLogger(__name__)


async def register_excel_handlers(dp):

    @dp.message_created(F.message.body.text == EXCEL_BTN_TEXT)
    async def on_excel(
        event: MessageCreated,
        context: MemoryContext,
        staff: Staff | None = None,
        route: str = "registration",
    ):
        if route != "staff" or staff is None or not staff.is_owner:
            return
        user_id = event.message.sender.user_id
        try:
            xlsx_bytes = await _generate_excel()
        except Exception:
            logger.exception("Excel generation failed")
            await event.message.answer("Ошибка при генерации файла.")
            return

        now_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        media = InputMediaBuffer(
            buffer=xlsx_bytes,
            filename=f"sorvancy_export_{now_str}.xlsx",
        )
        await event.bot.send_message(
            user_id=user_id,
            text="Выгрузка клиентов:",
            attachments=[media],
        )


async def _generate_excel() -> bytes:
    try:
        import openpyxl
    except ImportError:
        raise RuntimeError("openpyxl not installed; run: pip install openpyxl")

    from openpyxl import Workbook
    from openpyxl.styles import Font

    async with get_session_factory()() as session:
        customers = await customer_model.get_all(session)
        all_children: dict[int, list] = {}
        all_coupons: dict[int, list] = {}
        for c in customers:
            all_children[c.id] = await child_model.get_by_customer(session, c.id)
            all_coupons[c.id] = await coupon_model.get_active_by_customer(session, c.id)

    wb = Workbook()
    ws = wb.active
    ws.title = "Клиенты"

    headers = [
        "Номер клиента", "Имя", "Фамилия", "Телефон", "Дата рождения",
        "Скидка, %", "Дата регистрации", "Отказ от рассылок",
        "Последняя активность",
        "Имя ребёнка", "Пол", "Дата рождения ребёнка",
        "Активные купоны",
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for cust in customers:
        children = all_children.get(cust.id, [])
        coupons = all_coupons.get(cust.id, [])

        coupon_lines = []
        for cp in coupons:
            until = cp.valid_until.strftime("%d.%m.%Y %H:%M")
            coupon_lines.append(f"{cp.type} — {cp.value} ₽, до {until}")
        coupon_cell = "\n".join(coupon_lines) if coupon_lines else ""

        bd_str = cust.birthdate.strftime("%d.%m.%Y") if cust.birthdate else ""
        reg_str = cust.registered_at.strftime("%d.%m.%Y") if cust.registered_at else ""
        touch_str = cust.last_touch.strftime("%d.%m.%Y %H:%M") if cust.last_touch else ""

        base_row = [
            cust.id,
            cust.first_name or "",
            cust.last_name or "",
            cust.phone or "",
            bd_str,
            cust.discount_percent,
            reg_str,
            "Да" if cust.opt_out_marketing else "Нет",
            touch_str,
        ]

        if not children:
            ws.append(base_row + ["", "", "", coupon_cell])
        else:
            for i, ch in enumerate(children):
                ch_bd = ch.birthdate.strftime("%d.%m.%Y") if ch.birthdate else ""
                gender_str = "Мальчик" if ch.gender == "male" else "Девочка"
                row = base_row + [ch.name, gender_str, ch_bd, coupon_cell if i == 0 else ""]
                ws.append(row)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
