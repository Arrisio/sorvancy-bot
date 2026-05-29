# Scenario: Discount QR

## Goal
Registered user gets QR code with embedded deeplink to share with seller for profile lookup.

## Actors
- User (registered)
- Bot

## Trigger
User clicks «🎁 Скидка и купоны» button.

## Preconditions
- Customer exists in DB

## Main flow

1. Bot loads Customer and active Coupons (`status = active`) from DB by `max_user_id`
2. Bot generates QR PNG encoding Max Messenger deeplink containing customer identifier
3. Bot sends message with QR image, customer number, discount percent, coupon list, deeplink URL, and link label (+ `registered_keyboard`):
   ```
   Покажите этот QR-код продавцу
   Номер клиента: {customer.id}
   Скидка: {customer.discount_percent}%

   Ваши купоны:
   🎁 {coupon.display_name} (от {coupon.min_purchase_amount} ₽)
   🎁 {coupon.display_name}
   …

   Если QR не считывается — отправьте ссылку:
   {deeplink_url}
   ```
   `(от {N} ₽)` shown only when `coupon.min_purchase_amount > 0`; omitted when 0.
   Coupon section omitted if no active coupons. If >20 coupons, show first 20, append «…и ещё N» (style guide §8).
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
_All resolved._
