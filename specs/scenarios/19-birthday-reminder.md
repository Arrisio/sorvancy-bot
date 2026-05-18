# Scenario: Birthday Reminder

## Goal
Bot sends birthday reminder to Customer 3 days before a birthday (child's or customer's own) and issues a discount coupon.

## Actors
- Bot (scheduled job)
- Customer (notification recipient)

## Trigger
Daily scheduled job fires at `BROADCAST_WINDOW_START_HOUR` (default 10:00) Yekaterinburg time (`Asia/Yekaterinburg`). Bot calculates sleep until next occurrence of that hour on startup.

---

## Flow A: Child birthday reminder

### Preconditions
- Child.birthdate IS NOT NULL
- month+day of Child.birthdate = month+day of (today + 3 days)
- Child's age at upcoming birthday < 18 (i.e. year_of(today + 3 days) − Child.birthdate.year < 18)
- Child belongs to Customer with known max_user_id

### Steps
1. Job queries Children where birthdate IS NOT NULL AND month+day of birthdate = month+day of (today + 3 days)
2. Skip child if age at upcoming birthday ≥ 18
3. Skip child if `Child.birthday_reminded_year = year_of(today + 3 days)` — already reminded this year
4. For each remaining child: load parent Customer
5. Decline child's name to Russian genitive case (e.g. «Маша» → «Маши», «Дима» → «Димы»); uses Russian morphology library (pymorphy2 or equivalent)
6. Issue coupon to Customer: type=`birthday`, value=`FinancialConfig.birthday_coupon_value`, max_payment_pct=`FinancialConfig.birthday_coupon_max_pct`, valid_until=now()+`FinancialConfig.birthday_coupon_valid_days` days, display_name=`"ДР: {value} ₽ до {ДД.ММ.ГГ}"`
7. Send message to Customer:
   «У [имя в родительном падеже] через три дня день рождения. Вот вам купон на скидку — [birthday_coupon_value] руб., действителен до [дата].»
8. Set Child.birthday_reminded_year = year_of(today + 3 days)

---

## Flow B: Customer own birthday reminder

### Preconditions
- Customer.birthdate IS NOT NULL
- month+day of Customer.birthdate = month+day of (today + 3 days)
- Customer has known max_user_id

### Steps
1. Job queries Customers where birthdate IS NOT NULL AND month+day of birthdate = month+day of (today + 3 days)
2. Skip customer if `Customer.birthday_reminded_year = year_of(today + 3 days)` — already reminded this year
3. Issue coupon to Customer: same params as Flow A — type=`birthday`, value=`FinancialConfig.birthday_coupon_value`, max_payment_pct=`FinancialConfig.birthday_coupon_max_pct`, valid_until=now()+`FinancialConfig.birthday_coupon_valid_days` days, display_name=`"ДР: {value} ₽ до {ДД.ММ.ГГ}"`
4. Send message to Customer:

   «🎂 [Имя], через три дня — ваш день рождения!

   Сорванцы поздравляют вас заранее и дарят купон на [birthday_coupon_value] ₽.
   Действителен до [ДД.ММ.ГГ].

   С наступающим! 🥳»

5. Set Customer.birthday_reminded_year = year_of(today + 3 days)

**[Имя]** = Customer.first_name в именительном падеже. Если first_name IS NULL — приветственная строка опускается, сообщение начинается с «🎂 Через три дня…».

---

## Coupon parameters

Read from `FinancialConfig` at issuance time (scenario 22). Same config fields used for both flows. Defaults:

| Field | Default |
|-------|---------|
| `birthday_coupon_value` | 300 |
| `birthday_coupon_valid_days` | 7 |
| `birthday_coupon_max_pct` | 30 |

---

## Deduplication

**Child (Flow A):**
- `Child.birthday_reminded_year` (int, nullable) tracks last year reminder was sent.
- Compared against `year_of(today + 3 days)` — handles Dec 30 → Jan 2 birthday edge case.
- Multiple job runs same day: step 3 skips already-processed children.
- Yearly recurrence: each calendar year value differs → reminder fires again.
- Customer with multiple children whose birthdays fall on same day: one message per child (no batching).

**Customer (Flow B):**
- `Customer.birthday_reminded_year` (int, nullable) — same logic as child field.
- Compared against `year_of(today + 3 days)`.
- Customer whose birthdate coincides with a child's birthdate receives two separate messages (child reminder + own reminder).

---

## Postconditions
- Coupon issued with params from FinancialConfig
- Customer received birthday reminder message
- Flow A: Child.birthday_reminded_year set to year of upcoming birthday
- Flow B: Customer.birthday_reminded_year set to year of upcoming birthday

## NFR refs
- pii.md

## Open questions
- [x] `birthday_coupon_max_pct` default: 30%. RESOLVED.
- [ ] `Customer.birthday_reminded_year` field not in ORM or DB schema. Migration needed.
- [x] Flow A and Flow B run as single job or two separate jobs? RESOLVED: single job; Flow A first, then Flow B. UX degradation (two messages in quick succession) acceptable.
