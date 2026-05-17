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
4. Bot sends file as attachment in reply message

## File structure

One base row per Customer. If Customer has multiple children, that row expands into sub-rows — one sub-row per child. Customer-level columns span all child sub-rows (merged cells or repeated values — see Open questions). If Customer has no children: single row with child columns empty.

### Columns

**Customer columns** (one value per customer, spans child sub-rows):

| Column | Source field |
|--------|-------------|
| Номер клиента | Customer.id |
| Имя | Customer.first_name |
| Фамилия | Customer.last_name |
| Телефон | Customer.phone |
| Дата рождения | Customer.birthdate |
| Скидка, % | Customer.discount_percent |
| Дата регистрации | Customer.registered_at |
| Отказ от рассылок | Customer.opt_out_marketing |
| Последняя активность | Customer.last_touch |

**Child columns** (one value per child sub-row):

| Column | Source field |
|--------|-------------|
| Имя ребёнка | Child.name |
| Пол | Child.gender |
| Дата рождения ребёнка | Child.birthdate |

**Coupon column** (all active coupons in one cell, one per line):

| Column | Content |
|--------|---------|
| Активные купоны | Each active coupon on separate line: «[type] — [value] ₽, до [valid_until]» |

Active coupon filter: `status = active` AND `valid_until > now()`.

## Postconditions
- Superuser receives `.xlsx` file
- No DB writes

## NFR refs
- pii.md

## Open questions
- [ ] Multi-child row layout: merged cells (customer columns merged across child sub-rows) or repeated values (customer data copied into each child sub-row)? Merged cells are harder to filter in Excel; repeated values are easier for data processing.
- [ ] Customer.id shown as «Номер клиента» — must match the identifier used in scenario 10 (Find Profile) and shown in scenario 03 (Discount QR). Confirm all three reference the same field.
- [ ] Coupon cell format: exact per-line string format for active coupons?
- [ ] Customers with zero active coupons: coupon cell empty or «—»?
- [ ] Column ordering: exact column order in file?
- [ ] File name format: e.g. `sorvancy_export_2026-05-17.xlsx`?
- [ ] survey_completed flag: include in export or omit?
