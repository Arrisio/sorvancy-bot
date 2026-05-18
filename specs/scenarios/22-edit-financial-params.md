# Scenario: Edit Financial Parameters

## Goal
Owner views and edits all financial parameters (registration discount, coupon templates) without touching env vars or code.

## Actors
- Owner (Staff with `is_owner = true`, `customer_mode = false`)
- Bot
- Database (FinancialConfig)

## Trigger
Owner taps «Финансовые настройки» on `superuser_keyboard`.

## Preconditions
- Actor is Owner (`is_owner = true`)
- FinancialConfig row exists in DB (seeded at startup)

## Main flow

### Step 1 — Summary screen

Bot sends **financial summary message** (inline keyboard):

```
⚙️ Финансовые настройки

Скидка при регистрации: [X]%

🎁 Купон за анкету
Сумма: [X] ₽ · Срок: [X] дн · Макс. % от покупки: [X]%

🎂 Купон на день рождения
Сумма: [X] ₽ · Срок: [X] дн · Макс. % от покупки: [X]%
```

Inline buttons:
```
[✏️ Скидка при регистрации]
[✏️ Купон за анкету]
[✏️ Купон на день рождения]
```

### Step 2 — Coupon card (on [✏️ Купон за анкету] or [✏️ Купон на день рождения])

Bot **edits summary message** to coupon card for selected coupon type:

```
🎂 Купон на день рождения        (or 🎁 Купон за анкету)
Сумма: [X] ₽
Срок действия: [X] дней
Макс. % от покупки: [X]%
```

Inline buttons:
```
[✏️ Сумма]  [✏️ Срок]  [✏️ % от покупки]
[← Назад]
```

### Step 3 — Edit a field

Owner taps any [✏️ …] button (on summary screen or coupon card):

1. Bot sets `AWAITING_FINANCIAL_PARAM_VALUE` FSM state
2. Bot stores `editing_field` in MemoryContext (e.g. `birthday_coupon_value`)
3. Bot stores `mid` of the card message as `financial_card_mid`
4. Bot sends new prompt message for that field (see prompt table below) + [Отмена]

**Prompts:**

| Field | Prompt |
|-------|--------|
| `registration_discount_pct` | «Введите новое значение скидки при регистрации (1–100):\nСейчас: X%» (X — текущее значение из БД) |
| `survey_coupon_value` | «Введите сумму купона за анкету (целое число ₽, > 0):» |
| `survey_coupon_valid_days` | «Введите срок действия купона за анкету (целое число дней, > 0):» |
| `survey_coupon_max_pct` | «Введите макс. % от покупки для купона за анкету (1–100):» |
| `birthday_coupon_value` | «Введите сумму купона на день рождения (целое число ₽, > 0):» |
| `birthday_coupon_valid_days` | «Введите срок действия купона на день рождения (целое число дней, > 0):» |
| `birthday_coupon_max_pct` | «Введите макс. % от покупки для купона на день рождения (1–100):» |

5. Owner enters value → validated → FinancialConfig updated in DB
6. Bot deletes prompt message
7. Bot **edits `financial_card_mid`** with refreshed values (coupon card or summary, whichever was active)
8. FSM state cleared to base owner state

### Step 4 — Back navigation

Owner taps [← Назад] on coupon card → bot **edits message** back to summary (step 1 format with current DB values).

## Alternative flows

### A1: Owner taps [Отмена] on field prompt
- Prompt deleted; FSM state cleared; `financial_card_mid` message edited to show current values (no DB change).

## Negative scenarios

### N1: Non-integer input
- Bot: «Введите целое число.» Prompt message unchanged; state stays `AWAITING_FINANCIAL_PARAM_VALUE`; owner retries.

### N2: Value out of allowed range
- `registration_discount_pct` outside [1, 100]: «Введите число от 1 до 100.»
- `*_value` ≤ 0: «Сумма должна быть больше 0.»
- `*_valid_days` ≤ 0: «Срок должен быть больше 0.»
- `*_max_pct` outside [1, 100]: «Введите процент от 1 до 100.»
- State unchanged; owner retries.

### N3: DB write fails
- Bot: «Не удалось сохранить. Попробуйте ещё раз.»
- State unchanged; prompt still visible; owner retries.

## Postconditions
- FinancialConfig row updated in DB
- All future coupon issuances and new customer registrations use updated values

## NFR refs
None.

## Open questions
None.
