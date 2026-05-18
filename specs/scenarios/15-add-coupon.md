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
2. Bot creates Coupon: `type=anket`, `value=FinancialConfig.survey_coupon_value`, `max_payment_pct=FinancialConfig.survey_coupon_max_pct`, `valid_until=now()+FinancialConfig.survey_coupon_valid_days days`, `display_name="Бонус {value} ₽ до {ДД.ММ.ГГ}"`.
3. Bot sends customer notification (see Notification section).

### Flow B — Seller-initiated

1. Seller clicks «Выдать купон» on customer profile.
2. Bot sends: «Выдаёте купон клиенту [first_name] [last_name].» + button [Отмена]
3. Bot runs sub-scenario 21 (Coupon Input) → collects `coupon_draft = {value, validity_days, max_payment_pct, display_name}`.
   - On cancellation → A1.
4. Bot saves Coupon: `type=seller`; `valid_until = now() + coupon_draft.validity_days days`; `display_name = coupon_draft.display_name`.
5. Bot sends customer notification (see Notification section).
6. Bot sends seller updated customer profile (scenario 06 format).

## Notification

Bot sends customer:

«Вам выдан купон на [value] ₽. Успейте потратить до [valid_until formatted as ДД.ММ.ГГГГ].»

## Alternative flows

### A1: Cancellation during Flow B
- Seller clicks [Отмена] at step 2, or sub-scenario 21 signals cancellation → no DB write; scenario ends; profile message unchanged.

## Negative scenarios

Validation errors during coupon data entry handled by sub-scenario 21.

## Postconditions
- Coupon record created in DB linked to customer.
- Customer received notification with value and expiry date.
- Seller (Flow B) received updated customer profile.

## Open questions
- ~~Seller-initiated coupon `type` value: `seller`. RESOLVED.~~
