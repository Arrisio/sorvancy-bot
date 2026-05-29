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

1. Bot sends: «Введите или выберите сумму купона (в руб., 100–5000):» + buttons [300] [500] [1000] [Отмена] in one row.
2. Operator types integer 100–5000 **or** taps quick-value button → `coupon_draft.value`.
3. Bot sends: «Срок действия купона (в днях, минимум 7):» + buttons [7] [14] [30] [60] [Отмена] in one row.
4. Operator types integer ≥ 7 **or** taps quick-value button → `coupon_draft.validity_days`.
5. Bot sends: «Выберите минимальную сумму покупки для применения купона (в руб.) или введите своё значение:» + buttons [1000] [2000] [Отмена] in one row.
6. Operator taps [1000] or [2000] **or** types integer ≥ 0 → `coupon_draft.min_purchase_amount`.
7. Bot computes suggested default display name: `"{value} ₽ до {ДД.ММ.ГГ}"` where date = today + `validity_days`.
   Bot sends: «Название купона в кнопке (видит покупатель, макс. 40 символов). Предложение: «{suggested}». Введите своё или примите предложенное.» + buttons [Принять] [Отмена]
8. Operator clicks [Принять] → `coupon_draft.display_name = suggested`; OR operator types text (≤ 40 chars) → `coupon_draft.display_name = typed_text`.
9. Sub-scenario returns `coupon_draft` to parent.

## Alternative flows

### A1: Operator clicks [Отмена] at any step
- Sub-scenario signals cancellation to parent. Parent handles state reset and response per its own alt flow.

## Negative scenarios

### N1: Non-integer input
- Bot: «Введите целое число.»
- Operator retries same step.

### N2: `value` out of range (<100 or >5000)
- Bot: «Введите сумму от 100 до 5000 рублей.»
- Operator retries step 2.

### N3: `validity_days` < 7
- Bot: «Срок должен быть не менее 7 дней.»
- Operator retries step 4.

### N4: `min_purchase_amount` is negative
- Bot: «Введите целое число от 0 и выше.»
- Operator retries step 6.

### N5: `display_name` exceeds 40 chars
- Bot: «Название не должно превышать 40 символов. Введите короче или нажмите [Принять] для использования предложенного.»
- Operator retries step 8.

## Postconditions
- `coupon_draft = {value, validity_days, min_purchase_amount, display_name}` returned to parent scenario.
- No DB writes performed by this sub-scenario.

## Open questions
- ~~Upper bound for `min_purchase_amount`: no limit. RESOLVED.~~
