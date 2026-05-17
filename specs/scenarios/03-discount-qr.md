# Scenario: Discount QR

## Goal
Registered user gets QR code with embedded deeplink to share with seller for profile lookup.

## Actors
- User (registered)
- Bot

## Trigger
User clicks "Скидка" button.

## Preconditions
- Customer exists in DB

## Main flow

1. Bot loads Customer from DB by `max_user_id`
2. Bot generates QR PNG encoding Max Messenger deeplink containing customer identifier
3. Bot sends message with QR image: «Покажите этот QR-код продавцу»
4. User shows QR to seller; seller scans → scenario 06 triggers

## Alternative flows

### A1: QR generation raises exception
- Error logged
- Fallback: bot sends deeplink as text URL
- User can share link manually

### A2: User not registered
- Bot: «Вы ещё не зарегистрированы. Нажмите кнопку ниже.» + `unregistered_keyboard`

## Postconditions
- User has QR visible on screen
- No DB writes

## Open questions
- [ ] Button name/payload: user description says "Скидка"; existing code uses "Показать код на скидку" (`SHOW_DISCOUNT_BTN_TEXT`). Rename or add new button?
- [ ] Deeplink format: exact Max Messenger deeplink URL structure with customer identifier payload?
- [ ] Customer identifier in deeplink: `max_user_id`, internal `id`, or signed token?
- [ ] Previous QR data format was `SORVANCY:DISCOUNT:{max_user_id}:{discount_percent}%` (old scenario 03 + src/ code). Now replaced by deeplink. Code divergence — update needed.
- [ ] Message text: show customer's discount percent alongside QR, or instruction only?
