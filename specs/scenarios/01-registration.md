# Scenario: Registration (Phase 1 — Minimal)

## Goal
New Max user gets registered and receives discount in one button click, no form required.

## Actors
- User (new, not in DB)
- Bot
- Database

## Trigger
- User clicks bot link (from QR at cashier desk or direct link) → Max fires `bot_started` event
- Or user sends `/start` command

## Preconditions
- No Customer with this max_user_id in DB

## Main flow

1. Bot sends welcome message + "Зарегистрироваться и получить скидку" button (`unregistered_keyboard`)

2. User clicks button (text match: `REGISTER_BTN_TEXT`)

3. Bot checks DB: no existing Customer

4. Bot creates Customer: `max_user_id`, `max_username`, `discount_percent` (from `config.DISCOUNT_PERCENT`)

5. Bot sets FSM state = `REGISTERED`, initializes MemoryContext: `max_user_id`, `max_username`, `children=[]`

6. Bot sends registration confirmation message (e.g., "Вы зарегистрированы! Ваша скидка — 10%.")
   with `registered_keyboard_with_contact`

7. Bot sends survey offer message ("Заполните анкету и получите ещё +2%...")
   with `survey_offer_keyboard` [Пропустить / Заполнить анкету]
   → stores sent message ID as `survey_offer_mid` in MemoryContext

## Alternative flows

### A1: Already-registered user triggers bot_started or /start
- Bot reads Customer from DB by max_user_id
- Bot sends welcome-back with discount percent + `registered_keyboard`
- FSM state set to `REGISTERED` if different
- No DB writes

### A2: DB write fails at step 4
- Exception logged with max_user_id
- User sees error + `unregistered_keyboard` (retry possible)
- No partial data (single Customer insert)

## Postconditions
- Customer row exists: max_user_id + discount_percent set
- FSM state = `REGISTERED`
- survey_offer_mid stored in MemoryContext
- User sees discount percent and survey offer

## NFR refs
- pii.md: max_username storage
