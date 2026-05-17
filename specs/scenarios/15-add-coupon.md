# Scenario: Add Coupon

## Goal
Customer receives new coupon and notification of issuance.

## Actors
- Bot
- Customer
- Seller (Staff) — Flow B only

## Trigger
1. **Survey completion** — Customer.survey_completed transitions False → True (end of scenario 02).
2. **Seller action** — Seller presses «Выдать купон» on customer profile keyboard (scenario 06).

## Preconditions
- Trigger 1: Customer exists; survey_completed was False.
- Trigger 2: Seller is registered Staff; customer profile is open.

## Main flow

### Flow A — Automated (survey completion)

1. Scenario 02 completes with survey_completed False → True; sends «Анкета заполнена! Спасибо 🎉».
2. Bot creates Coupon: `type=anket`, `value=300`, `max_payment_pct=30`, `valid_until=now()+1 month`.
3. Bot sends customer notification (see Notification section).

### Flow B — Seller-initiated

1. Seller clicks «Выдать купон» on customer profile.
2. Bot sends seller:

   «Выдаёте купон клиенту [first_name] [last_name]. Введите максимальную сумму купона (в рублях, 101–1000):»

   Buttons: [Отмена]

3. Seller types integer 101–1000 → stored as `coupon_draft.value`.
4. Bot asks: «Срок действия купона (в днях, минимум 7):»
5. Seller types integer ≥ 7 → `coupon_draft.validity_days`; `valid_until = now() + validity_days days`.
6. Bot asks: «Максимальный процент от покупки, который можно оплатить купоном (1–100):»
7. Seller types integer 1–100 → `coupon_draft.max_payment_pct`.
8. Bot saves Coupon to DB: `type=seller`, plus drafted value/valid_until/max_payment_pct.
9. Bot sends customer notification (see Notification section).

## Notification

Bot sends customer:

«Вам выдан купон на [value] ₽. Успейте потратить до [valid_until formatted as ДД.ММ.ГГГГ].»

## Alternative flows

### A1: Seller clicks [Отмена] at step 2
- No DB write; scenario ends; profile message unchanged.

## Negative scenarios

### N1: Non-integer input in Flow B
- Bot: «Введите целое число.»
- State unchanged; seller retries same step.

### N2: `value` out of range (≤100 or >1000) in Flow B
- Bot: «Введите сумму от 101 до 1000 рублей.»
- State unchanged; seller retries step 3.

### N3: `validity_days` < 7 in Flow B
- Bot: «Срок должен быть не менее 7 дней.»
- State unchanged; seller retries step 5.

## Postconditions
- Coupon record created in DB linked to customer.
- Customer received notification with value and expiry date.

## Open questions
- ~~Seller-initiated coupon `type` value: `seller`. RESOLVED.~~
