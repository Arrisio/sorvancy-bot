# Scenario: Redeem Coupon

## Goal
Seller marks a customer's coupon as used at point of sale.

## Actors
- Seller (Staff)
- Customer
- Bot

## Trigger
Seller clicks coupon button on customer profile message (scenario 06).

## Preconditions
- Seller received customer profile message (via scenario 06 or scenario 10) with at least one active coupon
- Target coupon: `status = active` AND `valid_until > now()`

## Main flow

1. Seller clicks coupon button; bot receives coupon identifier
2. Bot sends seller: «Использовать купон «[coupon name]»?»
   Buttons: [Да] [Нет]
3. Seller clicks [Да]
4. Bot sets `Coupon.status = used`, `Coupon.used_at = now()` in DB
5. Bot sends seller: «Купон «[coupon name]» использован.»
6. Bot sends customer: «Купон «[coupon name]» использован.»

## Alternative flows

### A1: Seller clicks [Нет]
- No DB write; scenario ends

## Negative scenarios

### N1: Coupon expired or used between profile render and seller confirmation
- Step 4: coupon not active → bot sends seller: «Купон уже недействителен.» No DB write.

## Postconditions
- `Coupon.status = used`, `Coupon.used_at` set in DB
- Seller and customer both received notification naming the coupon

## Open questions
- [ ] "Coupon name" in notification messages: which field maps to display name? `type` field value, or separate field needed?
- [ ] Coupon button payload: encodes `coupon.id`? Confirm routing mechanism.
- [ ] After redemption: bot re-shows updated profile to seller automatically, or scenario ends?
