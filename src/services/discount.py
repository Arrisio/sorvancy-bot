import io
import qrcode
import config


def registration_complete_message() -> str:
    pct = config.DISCOUNT_PERCENT
    return f"Вы зарегистрированы! Ваша скидка — {pct}%."


def survey_offer_message() -> str:
    return (
        "Заполните анкету и получите ещё +2% к скидке!\n\n"
        "Расскажите о себе и своих детях — займёт 2 минуты."
    )


def discount_card(first_name: str) -> str:
    pct = config.DISCOUNT_PERCENT
    return (
        f"┌─────────────────────────┐\n"
        f"│  🏷 СКИДКА {pct}%             │\n"
        f"│  Магазин СОРВАНЦЫ       │\n"
        f"└─────────────────────────┘\n\n"
        f"Покупатель: {first_name}\n\n"
        f"Покажите это сообщение кассиру."
    )


def profile_message(customer, children: list) -> str:
    lines = [
        "👤 Ваш профиль",
        f"Имя: {customer.first_name or '—'}",
        f"Скидка: {customer.discount_percent}%",
        f"Зарегистрирован: {customer.registered_at.strftime('%d.%m.%Y')}",
    ]
    if customer.birthdate:
        lines.append(f"Дата рождения: {customer.birthdate.strftime('%d.%m.%Y')}")
    if children:
        lines.append("\nДети:")
        for ch in children:
            gender_str = "Мальчик" if ch.gender == "male" else "Девочка"
            lines.append(f"  • {ch.name}, {gender_str}, {ch.birthdate.strftime('%d.%m.%Y')}")
    return "\n".join(lines)


def make_qr_png(user_id: int, discount_percent: int) -> bytes:
    data = f"SORVANCY:DISCOUNT:{user_id}:{discount_percent}%"
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
