# Scenario: Edit Customer Discount

## Goal
Seller updates a customer's discount percentage and both parties are notified.

## Actors
- Seller (Staff)
- Customer
- Bot

## Trigger
Seller clicks "Изменить % скидки" button on customer profile message (scenario 06).

## Preconditions
- Seller received customer profile message (scenario 06 complete)
- Seller is registered in Staff table

## Main flow

1. Bot sends seller: «Введите новое значение скидки (0–30):»
2. Seller enters integer in range [0, 30]
3. Bot updates `Customer.discount_percent` in DB
4. Bot sends seller: «Скидка изменена: ~~[старое]%~~ → [новое]%»
5. Bot sends customer: «Скидка изменена: ~~[старое]%~~ → [новое]%»

## Negative scenarios

### N1: Value out of range
- Seller sends value < 0 or > 30 → bot: «Введите число от 0 до 30.» State unchanged; seller retries.

### N2: Non-numeric input
- Bot: «Введите число от 0 до 30.» State unchanged; seller retries.

## Postconditions
- `Customer.discount_percent` updated in DB
- Seller and customer both received notification with old and new values

## Open questions
- [ ] Is "Изменить % скидки" restricted to `is_owner = true`, or available to all Staff?
- [ ] Seller abandons input (no reply): timeout or cancel behavior?
- [ ] Strikethrough format: Max Messenger supports `~~text~~` markdown? Confirm rendering.
