# Scenario: Excel Export

## Goal
Superuser receives Excel file with all customers, their children, and active coupons.

## Actors
- Superuser (Staff with `is_owner = true`)
- Bot

## Trigger
Superuser clicks «Excel» button.

## Preconditions
- Acting user has `is_owner = true` in Staff table

## Main flow

1. Superuser clicks «Excel»
2. Bot queries all Customers with their Children and active Coupons
3. Bot generates `.xlsx` file
4. Bot sends file as attachment in reply message; bot sends `superuser_keyboard`

## File structure

One base row per Customer. If Customer has multiple children, expands into one sub-row per child. Customer-level columns **merged** across all child sub-rows (vertical merge). If Customer has no children: single row, child columns empty.

### Column order

| # | Column | Source field | Scope |
|---|--------|-------------|-------|
| 1 | Номер клиента | Customer.id | Customer (merged) |
| 2 | Имя | Customer.first_name | Customer (merged) |
| 3 | Фамилия | Customer.last_name | Customer (merged) |
| 4 | Телефон | Customer.phone | Customer (merged) |
| 5 | Дата рождения | Customer.birthdate | Customer (merged) |
| 6 | Скидка, % | Customer.discount_percent | Customer (merged) |
| 7 | Дата регистрации | Customer.registered_at | Customer (merged) |
| 8 | Отказ от рассылок | Customer.opt_out_marketing | Customer (merged) |
| 9 | Последняя активность | Customer.last_touch | Customer (merged) |
| 10 | Имя ребёнка | Child.name | Child (per row) |
| 11 | Пол | Child.gender | Child (per row) |
| 12 | Дата рождения ребёнка | Child.birthdate | Child (per row) |
| 13 | Активные купоны | active Coupons | Customer (merged) |
| 14 | Заполнена анкета | Customer.survey_completed | Customer (merged) |

### Formatting rules

1. **Merged cells** — customers with 2+ children: columns 1–9, 13, 14 merged vertically across child sub-rows. Merged cells: vertical align = center.
2. **Wrap text** — column 13 «Активные купоны» always has `wrap_text = True`; multiple coupons render on separate lines within cell.
3. **Column auto-width** — all columns sized to fit widest content (header or data). No manual resizing required after opening.

### Field formats

| Field | Format |
|-------|--------|
| Customer.birthdate | `DD.MM.YYYY` |
| Customer.registered_at | `DD.MM.YYYY` |
| Customer.last_touch | `DD.MM.YYYY HH:MM` |
| Child.birthdate | `DD.MM.YYYY` |
| Customer.opt_out_marketing | «Да» / «Нет» |
| Customer.survey_completed | «Да» / «Нет» |
| Coupon valid_until | `DD.MM.YYYY HH:MM` |
| Coupon line format | `[type] — [value] ₽, до [valid_until]` (`, от [min_purchase_amount] ₽` appended when `min_purchase_amount > 0`) |

Active coupon filter: `status = active` AND `valid_until > now()`.
Zero coupons: cell empty.

## Postconditions
- Superuser receives `.xlsx` file named `sorvancy_export_YYYY-MM-DD.xlsx`
- No DB writes

## NFR refs
- pii.md

## Open questions
- [ ] Пол ребёнка: только «Мальчик»/«Девочка» или возможны другие значения?
