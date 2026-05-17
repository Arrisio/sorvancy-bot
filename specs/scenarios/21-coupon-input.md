# Scenario: Coupon Input (Sub-scenario)

## Goal
Collect coupon parameters from operator via sequential prompts; return draft to calling scenario for persistence.

## Actors
- Operator (Seller or Owner — determined by calling scenario)
- Bot

## Trigger
Called inline by parent scenario when operator opts to attach or issue a coupon. Not triggered directly by user action.

## Preconditions
- Parent scenario is active.
- Operator is authenticated Staff.

## Main flow

1. Bot sends: «Введите максимальную сумму купона (в рублях, 101–1000):» + button [Отмена]
2. Operator types integer 101–1000 → `coupon_draft.value`.
3. Bot sends: «Срок действия купона (в днях, минимум 7):» + button [Отмена]
4. Operator types integer ≥ 7 → `coupon_draft.validity_days`.
5. Bot sends: «Максимальный процент от покупки, который можно оплатить купоном (1–100):» + button [Отмена]
6. Operator types integer 1–100 → `coupon_draft.max_payment_pct`.
7. Sub-scenario returns `coupon_draft` to parent.

## Alternative flows

### A1: Operator clicks [Отмена] at any step
- Sub-scenario signals cancellation to parent. Parent handles state reset and response per its own alt flow.

## Negative scenarios

### N1: Non-integer input
- Bot: «Введите целое число.»
- Operator retries same step.

### N2: `value` out of range (≤100 or >1000)
- Bot: «Введите сумму от 101 до 1000 рублей.»
- Operator retries step 2.

### N3: `validity_days` < 7
- Bot: «Срок должен быть не менее 7 дней.»
- Operator retries step 4.

### N4: `max_payment_pct` out of range (<1 or >100)
- Bot: «Введите процент от 1 до 100.»
- Operator retries step 6.

## Postconditions
- `coupon_draft = {value, validity_days, max_payment_pct}` returned to parent scenario.
- No DB writes performed by this sub-scenario.

## Open questions
- [ ] N4 absent from current scenario 15 implementation — confirm `max_payment_pct` range validation should be added (entity invariant requires 1–100).
