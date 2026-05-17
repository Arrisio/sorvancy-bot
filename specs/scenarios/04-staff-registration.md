# Scenario: Staff Registration via Deep Link Invite

## Goal
Owner generates signed invite link valid for current calendar day; seller clicks link and gets registered automatically.

## Actors
- Owner (Staff with `is_owner = true`)
- Seller (prospective, not yet in Staff table)
- Bot

## Trigger
Owner presses «Добавить продавца» button in owner keyboard.

## Preconditions
- Pressing user has `is_owner = true` in Staff table
- «Добавить продавца» button appears in same row as «Показать продавцов» in `superuser_keyboard()`

## Token format

Deep Link payload = `base64url( owner_id ":" date ":" HMAC-SHA256(owner_id ":" date, SECRET_KEY) )`

Where:
- `owner_id` — Staff `max_user_id` of owner who generated link
- `date` — calendar date of generation, `YYYY-MM-DD` (server timezone)
- `SECRET_KEY` — bot secret from config (not bot token)

## Main flow

1. Owner presses «Добавить продавца»
2. Bot builds token: takes today's date + owner's `max_user_id`, computes HMAC-SHA256, encodes as base64url
3. Bot builds Deep Link with token as payload
4. Bot sends owner message containing Deep Link: «Перешлите это сообщение продавцу, которого хотите добавить. Ссылка действует сегодня и завтра.»
5. Owner forwards message to prospective seller outside bot
6. Seller clicks link → bot receives `bot_started` with payload = token
7. Bot decodes token, extracts `owner_id`, `date`, `signature`
8. Bot recomputes HMAC for `owner_id + today's date` — if mismatch → N1
9. Bot checks `today - date <= 1 day` — if older → N2
10. Bot creates Staff record: `max_user_id` from `event.user.user_id`, `first_name`/`last_name` from `event.user` (nulls allowed if absent), `is_owner = false`
11. Bot sends seller: «Вы зарегистрированы как продавец магазина «Сорванцы».»
12. Bot sends owner (by `owner_id` from token): «Продавец [first_name last_name] зарегистрирован.»

## Alternative flows

### A1: Seller already registered as Staff
- At step 10: Staff row with that `max_user_id` exists → bot sends seller: «Вы уже зарегистрированы как продавец.» → bot notifies owner: «Продавец уже зарегистрирован.» Scenario ends without duplicate.

## Negative scenarios

### N1: Invalid signature
- At step 8: HMAC mismatch → bot treats `bot_started` as regular unregistered user start. No error message about invite failure.

### N2: Link expired
- At step 9: token date older than 1 day → bot sends seller: «Ссылка устарела. Попросите владельца магазина выслать новую.»

### N3: Seller is already registered customer
- At step 10: `max_user_id` exists in Customer table but not Staff — registration proceeds normally; customer record untouched.

## Postconditions
- New Staff row exists with `is_owner = false`; `max_user_id`, `first_name`, `last_name` populated from `event.user`
- Seller received confirmation message
- Owner received notification with seller name

## NFR refs
- pii.md

## Open questions
None.
