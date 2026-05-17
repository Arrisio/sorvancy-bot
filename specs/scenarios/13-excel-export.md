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

One base row per Customer. If Customer has multiple children, expands into one sub-row per child. Customer-level columns **merged** across all child sub-rows (vertical merge). If Customer has no children: single row, child columns empty.

### Columns

**Customer columns** (merged vertically across child sub-rows when multiple children):

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

**Coupon column** (merged vertically across child sub-rows; wrap text enabled):

| Column | Content |
|--------|---------|
| Активные купоны | All active coupons in one cell, each coupon on separate line: «[type] — [value] ₽, до [valid_until]» |

Active coupon filter: `status = active` AND `valid_until > now()`.

### Formatting rules

1. **Merged cells** — for customers with 2+ children: all Customer columns and the «Активные купоны» column are merged vertically across child sub-rows. Merged cells: vertical align = center.
2. **Wrap text** — «Активные купоны» column always has `wrap_text = True`, so multiple coupons render on separate lines within the cell.
3. **Column auto-width** — all columns sized to fit widest content (header or data). No manual column resizing required after opening file.

## Postconditions
- Superuser receives `.xlsx` file named `sorvancy_export_YYYY-MM-DD.xlsx`
- No DB writes

## NFR refs
- pii.md

## Open questions
- [ ] Customer.last_touch absent from current code (`src/handlers/excel.py` base_row has 8 fields, omits last_touch). Add to export or keep omitted?
- [ ] Customers with zero active coupons: coupon cell empty or «—»?
- [ ] Column ordering: exact column order in file? Current code order assumed as canonical.
- [ ] survey_completed flag: include in export or omit?
