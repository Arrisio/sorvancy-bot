# Keyboards

Bot presents a persistent reply keyboard based on actor type. Actor detection runs in middleware on every incoming message — see nfr/middleware-routing.md.

---

## Customer keyboard (`registered_keyboard`)

**Shown to:** registered Customer; also shown to Staff with `customer_mode = true`

| Button | Scenario |
|--------|----------|
| «Мой профиль» | → 05 Profile Editing |
| «Скидка» | → 03 Discount QR |
| «Связаться с продавцом» | → TBD (not yet specced) |

---

## Staff keyboard (`staff_keyboard`)

**Shown to:** Staff with `is_owner = false` AND `customer_mode = false`

| Button | Scenario |
|--------|----------|
| «Найти профиль» | → 10 Find Customer Profile by ID |

Note: Staff also triggers scenario 06 (Show Customer Profile) by following a deeplink — no keyboard button needed.

---

## Superuser keyboard (`superuser_keyboard`)

**Shown to:** Staff with `is_owner = true` AND `customer_mode = false`

| Button | Scenario |
|--------|----------|
| «Найти профиль» | → 10 Find Customer Profile by ID |
| «Excel» | → 13 Excel Export |
| «Показать продавцов» | → 09 Staff List Management |
| «Запустить рассылку» | → 11 Create and Schedule Broadcast |
| «Запланированные рассылки» | → 12 Show Scheduled Broadcasts |

Note: Superuser registers sellers by forwarding a contact card — no keyboard button; intentional (out-of-band onboarding).

`/mode` command available to superuser at any time regardless of `customer_mode` state — see scenario 14.

---

## Transient keyboards (shown mid-flow, not persistent)

| Keyboard | Shown in | Buttons |
|----------|----------|---------|
| `unregistered_keyboard` | Scenario 01, step 1 | «Зарегистрироваться и получить скидку» |
| `registered_keyboard_with_contact` | Scenario 01, step 6 | Same as `registered_keyboard` (customer keyboard) |
| `survey_offer_keyboard` | Scenario 01, step 7 | «Пропустить», «Заполнить анкету» |

---

## Open questions

- [ ] «Связаться с продавцом»: scenario TBD — keep as placeholder or remove until specced?
- [ ] Staff keyboard shown on bot_started for known Staff, or only after explicit action?
- [ ] Superuser in `customer_mode = true`: which keyboard shown on bot_started — customer keyboard, or no automatic keyboard?
