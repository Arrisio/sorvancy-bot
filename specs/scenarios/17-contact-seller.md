# Scenario: Contact Seller

## Goal
Customer opens direct chat with store owner in Max client, in one tap, without bot involvement.

## Actors
- Customer (registered)
- Owner (store owner — chat recipient, passive)

## Trigger
Customer clicks «Связаться с продавцом» button in `registered_keyboard`.

## Preconditions
- Customer registered (keyboard shown)
- `config.OWNER_CHAT_URL` non-empty — otherwise button hidden, see N1

## Main flow
1. Customer sees «Связаться с продавцом» in `registered_keyboard` — link button, not a handler button
2. Customer clicks
3. Max client opens chat with Owner by URL
4. Bot receives no event — no message, no callback, no DB write

## Alternative flows

None. Link button has no branches.

## Negative scenarios

### N1: `OWNER_CHAT_URL` empty
- Cause: Owner never set profile username in Max client, or config value not filled
- Button «Связаться с продавцом» not rendered in `registered_keyboard` — row 2 contains survey-conditional button only
- No message, no placeholder, no error to Customer — scenario simply unavailable
- Applies to every keyboard build; button appears as soon as config value is set (bot restart)

## Postconditions
- No DB change
- `Customer.last_touch` NOT updated — pure link, no tracking (explicit decision)

## Owner chat URL

Format: `https://max.ru/<username>` — Owner's public profile link.

Source: Owner copies it from own profile in Max client (profile settings → profile link). Value stored in config as `OWNER_CHAT_URL`.

Cannot be derived from `config.OWNER_ID` or Owner phone:
- Bot API exposes no username lookup by `max_user_id`
- `LinkButton.url` accepts http/https only — no custom scheme
- Phone-based link would expose Owner PII

Changing the recipient (owner substitution, different support account) = config change + bot restart. No runtime switching.

## NFR refs
- `ux-style-guide.md` §2.1 (persistent keyboards)

## Open questions
- [ ] Loss of `last_touch` on this action: scenario 13 Excel column «Последняя активность» now reflects QR views only (scenario 03). Confirm acceptable for reporting.
- [ ] Code divergence: `src/keyboards.py` uses `MessageButton(text=CONTACT_STAFF_BTN_TEXT)` and `src/handlers/start.py` has `on_contact_staff` handler writing `last_touch` and answering «Свяжитесь с нашим магазином: TBD.» Both must go — button becomes `LinkButton`, handler deleted.
- [ ] `OWNER_CHAT_URL` not yet in `config.py`, `.env.example`, README env table.
