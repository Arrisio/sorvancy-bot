import io
import qrcode
import config


def registration_complete_message(pct: int) -> str:
    return f"Вы зарегистрированы! Ваша скидка — {pct}%."


def survey_offer_message() -> str:
    return (
        "Заполните анкету — и получите купон на 300 ₽!\n\n"
        "Расскажите о себе и своих детях — займёт 2 минуты."
    )


def discount_card(first_name: str, pct: int) -> str:
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
        f"Имя: {customer.first_name or 'не указано'}",
        f"Фамилия: {customer.last_name or 'не указано'}",
        f"Дата рождения: {customer.birthdate.strftime('%d.%m.%Y') if customer.birthdate else 'не указано'}",
        f"Телефон: {customer.phone or 'не указано'}",
    ]
    if children:
        lines.append("\n👧 Дети:")
        for i, ch in enumerate(children, 1):
            gender_str = "Мальчик" if ch.gender == "male" else "Девочка"
            bdate = ch.birthdate.strftime("%d.%m.%Y") if ch.birthdate else "—"
            lines.append(f"  {i}. {ch.name} · {gender_str} · {bdate}")
    return "\n".join(lines)


def staff_customer_profile_message(customer, coupons: list) -> str:
    name = " ".join(filter(None, [customer.first_name, customer.last_name])) or "—"
    lines = [
        f"👤 {name}",
        f"Номер клиента: {customer.id}",
        f"Скидка: {customer.discount_percent}%",
    ]
    if coupons:
        lines.append("\n🎟 Купоны:")
        for i, c in enumerate(coupons, 1):
            until = c.valid_until.strftime("%d.%m.%Y")
            lines.append(f"  {i}. {c.display_name} — {c.value} ₽, действует до {until}")
    else:
        lines.append("\nНет активных купонов.")
    return "\n".join(lines)


def coupon_issued_notification(coupon) -> str:
    until = coupon.valid_until.strftime("%d.%m.%Y")
    return f"Вам выдан купон на {coupon.value} ₽. Успейте потратить до {until}."


def customer_qr_deeplink(customer_id: int) -> str:
    return f"{config.DEEPLINK_BASE}?start=show_profile_{customer_id}"


def make_qr_png(customer_id: int) -> bytes:
    data = customer_qr_deeplink(customer_id)
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
