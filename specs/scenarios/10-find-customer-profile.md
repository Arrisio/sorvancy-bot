# Scenario: Find Customer Profile by ID (Staff)

## Goal
Staff member retrieves customer loyalty profile by entering Customer ID.

## Actors
- Staff (seller or superuser)
- Bot

## Trigger
Staff clicks «Найти профиль» button.

## Preconditions
- Acting user is registered in Staff table

## Main flow

1. Staff clicks «Найти профиль»
2. Bot sends: «Пришлите номер клиента»
3. Staff sends Customer ID (text message)
4. Bot loads Customer from DB by provided ID
5. Bot sends customer profile card (same format as scenario 06, step 3)

## Alternative flows

*(none)*

## Negative scenarios

### N1: Customer not found
- Bot response wording TBD — customer with given ID does not exist in DB

## Postconditions
- Staff sees customer profile with discount percent, active coupons, and action buttons
- No DB writes

## NFR refs
- pii.md

## Open questions
- [ ] Customer ID field: internal DB `id`, `max_user_id`, or a separate display number? Must match value shown in scenario 03.
- [ ] N1 bot response: exact wording when ID not found?
- [ ] FSM state for awaiting-ID step: named state or inline handler?
