# Scenario: Birthday Reminder

## Goal
Bot sends birthday reminder to Customer 3 days before child's birthday and issues a discount coupon. Fires yearly while child is under 18.

## Actors
- Bot (scheduled job)
- Customer (notification recipient)

## Trigger
Daily scheduled job fires.

## Preconditions
- Child.birthdate IS NOT NULL
- month+day of Child.birthdate = month+day of (today + 3 days)
- Child's age at upcoming birthday < 18 (i.e. year_of(today + 3 days) − Child.birthdate.year < 18)
- Child belongs to Customer with known max_user_id

## Main flow

1. Job queries Children where birthdate IS NOT NULL AND month+day of birthdate = month+day of (today + 3 days)
2. Skip child if age at upcoming birthday ≥ 18
3. Skip child if `birthday_reminded_year = year_of(today + 3 days)` — already reminded this year
4. For each remaining child: load parent Customer
5. Decline child's name to Russian genitive case (e.g. «Маша» → «Маши», «Дима» → «Димы»); uses Russian morphology library (pymorphy2 or equivalent)
6. Issue coupon to Customer: type=`birthday`, value=`FinancialConfig.birthday_coupon_value`, max_payment_pct=`FinancialConfig.birthday_coupon_max_pct`, valid_until=now()+`FinancialConfig.birthday_coupon_valid_days` days, display_name=`"ДР: {value} ₽ до {ДД.ММ.ГГ}"`
7. Send message to Customer:
   «У [имя в родительном падеже] через три дня день рождения. Вот вам купон на скидку — [birthday_coupon_value] руб., действителен до [дата].»
8. Set Child.birthday_reminded_year = year_of(today + 3 days)

## Coupon parameters

Read from `FinancialConfig` at issuance time (scenario 22). Defaults:

| Field | Default |
|-------|---------|
| `birthday_coupon_value` | 300 |
| `birthday_coupon_valid_days` | 7 |
| `birthday_coupon_max_pct` | 30 |

## Deduplication

- `Child.birthday_reminded_year` (int, nullable) tracks last year reminder was sent.
- Compared against `year_of(today + 3 days)` — not `year_of(today)` — handles Dec 30 → Jan 2 birthday edge case.
- Multiple job runs same day: step 3 skips already-processed children.
- Yearly recurrence: each calendar year `birthday_reminded_year` differs → reminder fires again.
- Customer with multiple children whose birthdays fall on same day: one message per child (no batching at this stage).

## Postconditions
- Coupon issued with params from env vars
- Customer received birthday reminder message
- Child.birthday_reminded_year set to year of upcoming birthday

## NFR refs
- pii.md

## Open questions
- [x] `birthday_coupon_max_pct` default: 30%. RESOLVED.
