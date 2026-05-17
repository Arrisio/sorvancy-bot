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
3. Bot sends message with QR image, customer number, discount percent, deeplink URL, and link label:
   ```
   Покажите этот QR-код продавцу
   Номер клиента: {customer.id}
   Скидка: {customer.discount_percent}%
   
   Ссылка для продавца:
   {deeplink_url}
   ```
4. User shows QR (or shares link) to seller; seller scans/opens → scenario 06 triggers

## Alternative flows

### A1: QR generation raises exception
- Error logged
- Bot sends same text without QR image (link already present as text — user can share manually)

### A2: User not registered
- Bot: «Вы ещё не зарегистрированы. Нажмите кнопку ниже.» + `unregistered_keyboard`

## Postconditions
- User has QR and deeplink URL visible on screen
- `Customer.last_touch` set to current datetime

## Open questions
- [ ] Link label text: «Ссылка для продавца:» confirmed? Or different wording?
- [ ] Button name/payload: user description says "Скидка"; existing code uses `DISCOUNT_BTN_TEXT`. Verify they match.
