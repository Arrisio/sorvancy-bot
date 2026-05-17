# Scenario: Show Customer Profile (Staff)

## Goal
Seller receives customer's loyalty profile after scanning QR deeplink.

## Actors
- Seller (Staff, registered)
- Bot

## Trigger
Seller follows deeplink (scans customer QR or opens link) — bot receives deeplink command containing customer identifier.

## Preconditions
- Seller is registered in Staff table
- Customer identified by deeplink payload exists in DB

## Main flow

1. Bot receives deeplink command from seller; extracts customer identifier
2. Bot loads Customer from DB; loads active coupons (`status = active` AND `valid_until > now()`)
3. Bot sends profile message to seller:

```
👤 [first_name] [last_name]
Скидка: N%

🎟 Купоны:
  1. Купон «[name]» — [value] ₽, действует до [valid_until]
  2. …

[Купон «…»]  [Купон «…»]
[Изменить % скидки]
[Выдать купон]
```

Each coupon button triggers scenario 08. "Изменить % скидки" triggers scenario 07. "Выдать купон" triggers scenario 15.

## Postconditions
- Seller sees customer's discount percent and active coupons with action buttons
- No DB writes

## NFR refs
- pii.md

## Open questions
- [ ] Auth check: profile shown only to registered Staff, or any user who follows deeplink?
- [ ] Customer has zero active coupons: show «Нет активных купонов» or omit coupon section?
- [ ] Coupon button label: exact format? (e.g., «Купон 300 ₽» or «Купон "anket"»?)
- [ ] Profile message format: exact layout TBD — confirm fields shown (first_name + last_name + discount_percent + coupons cover all cases?)
