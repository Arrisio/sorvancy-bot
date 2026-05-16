# Scenario: Discount Display

## Goal
Registered user shows discount code to cashier on phone screen.

## Triggers (any of three)
- User clicks "Показать код на скидку" message button (`SHOW_DISCOUNT_BTN_TEXT` text match)
- User sends `/discount` command
- User clicks "🏷 Показать скидку кассиру" inline callback (payload `show_discount`)

## Preconditions
- Customer exists in DB (may or may not have completed survey)

## Main flow

1. Bot loads Customer from DB by max_user_id

2. Bot generates QR PNG:
   - Data: `SORVANCY:DISCOUNT:{max_user_id}:{discount_percent}%`
   - Library: `qrcode` (box_size=10, border=4)
   - Sent as image via `InputMediaBuffer`

3. Bot sends message: "Ваш код на скидку {N}%\nПокажите кассиру:" + QR image

4. User shows phone screen to cashier

## Alternative flows

### A1: QR generation raises exception
- Error logged
- Fallback: bot sends ASCII text card (customer first_name + discount_percent)
- User still has something to show cashier

### A2: User not registered
- Bot: "Вы ещё не зарегистрированы. Нажмите кнопку ниже." + `unregistered_keyboard`

## Postconditions
- User has discount visible on screen
- No DB writes

## Open questions
- [ ] Cashier validation: eye-check or QR scanner? If scanner — what action does POS take on scan?
- [ ] QR data format: add customer first_name for cashier readability?
- [ ] "Мой профиль" button shows profile text + `registered_keyboard` (no QR). Intentional separation?
