# Scenario: Staff Registration via Contact Card

## Goal
Owner registers a new seller in the bot by forwarding their Max contact card.

## Actors
- Seller (prospective)
- Owner (Staff with `is_owner = true`)
- Bot

## Trigger
Owner forwards a message containing a contact card to the bot.

## Preconditions
- Forwarding user has `is_owner = true` in Staff table
- Contact card message contains `max_user_id` and at least some of: `phone`, `first_name`, `last_name`, `username`

## Main flow

1. Owner forwards contact card to bot
2. Bot extracts `max_user_id`, `phone`, `first_name`, `last_name`, `username` from card/message attributes
3. Bot asks owner: «Вы хотите зарегистрировать [first_name last_name] как продавца?»
4. Owner confirms
5. Bot sends message to prospective seller: «Владелец магазина добавляет вас как продавца. Вы согласны?»
6. Seller confirms
7. Bot creates Staff record with extracted fields, `is_owner = false`
8. Bot notifies owner: «Продавец [first_name last_name] успешно добавлен.»
9. Bot notifies seller: «Вы добавлены как продавец в магазин Сорванцы.»

## Alternative flows

### A1: Seller already registered
- After step 2: Staff row with that `max_user_id` already exists → bot notifies owner, scenario ends without creating duplicate

## Negative scenarios

### N1: Owner declines at step 4
- Bot: «Регистрация отменена.» Scenario ends. Seller not contacted.

### N2: Seller declines at step 6
- Bot notifies owner: «Продавец отказался от регистрации.» Staff record not created.

## Postconditions
- New Staff row exists with `is_owner = false` and fields populated from contact card
- Owner and seller both received success notification

## NFR refs
- pii.md

## Open questions
- [ ] Timeout on seller confirmation: what if seller never responds?
- [ ] Which contact card fields are required for registration to proceed? If `first_name` or `max_user_id` missing — fail or proceed with nulls?
- [ ] Confirmation UI: free-text reply or inline buttons (Да/Нет)?
