# Domain Glossary

| Term | Definition |
|------|------------|
| Customer | Registered buyer. Created in DB on first button click (minimal record). Profile enriched via optional survey. |
| Child | Kid linked to Customer. Collected during survey. Drives birthday and school-year marketing. |
| Discount | Integer percent stored on Customer. Fixed at registration from config. Displayed as QR or text card. |
| Survey | Optional questionnaire after phase 1 registration. Collects first_name, birthdate, and 1+ Children. |
| FSM | Finite state machine managing multi-step survey dialog. States defined in `src/states.py`. |
| MemoryContext | maxapi in-memory per-user state store (`maxapi.context.MemoryContext`). Lost on bot restart. |
| QR code | Discount card shown to cashier. Generated dynamically; format: `SORVANCY:DISCOUNT:{user_id}:{pct}%`. |
| max_user_id | Unique user identifier from Max messenger. Primary external key for Customer lookup. |
| Phase 1 | Minimal registration: Customer row created with max_user_id + discount_percent only. |
| Phase 2 | Survey: enriches Customer with first_name, birthdate; creates Child rows. |
| Cashier | Store staff who reads discount QR or text card from customer's phone screen. |
| Coupon | Single-use monetary benefit issued to a Customer. Covers part of purchase up to `value` rubles and `max_payment_pct`% of total. Expires at `valid_until`. `display_name` (≤40 chars) is the label shown on coupon buttons and lists. |
| registered_keyboard | Persistent keyboard for registered Customer. Button routing: `specs/ux-style-guide.md` §2.1. |
| unregistered_keyboard | Button set for new users: «Зарегистрироваться и получить скидку». |
| registered_keyboard_with_contact | Keyboard shown in scenario 01 step 6 immediately after registration. Same buttons as `registered_keyboard` (customer keyboard). |
| survey_offer_keyboard | Transient keyboard shown in scenario 01 step 7: «Пропустить», «Заполнить анкету». |
| Staff | Store personnel account in the bot — either seller or owner. Created at DB seed (owner) or via contact card forwarding (sellers). |
| Owner | Staff member with `is_owner = true`. Elevated permissions. Multiple simultaneous owners allowed (substitute owners). Seeded owner identified by `config.OWNER_ID`; their flag cannot be revoked. |
| Суперпользователь | Project synonym for Owner. Staff member with `is_owner = true`. |
| Contact card | Max messenger message type carrying user identity fields (max_user_id, phone, first_name, last_name, username). Used for seller registration flow. |
| Deeplink | Max Messenger URL embedded in customer's QR code. When followed by seller, triggers "show customer profile" command in bot. Synonymous with Ссылка in project terminology. |
| Ссылка | Project term for deeplink. See Deeplink. |
| Профиль (staff view) | Bot message sent to Seller showing customer's discount percent, active coupons (value + expiry), inline coupon buttons, and "Изменить % скидки" button. Triggered by deeplink (scenario 06). Distinct from customer-facing «Мой профиль». |
| Broadcast / Рассылка | Mass message forwarded to a filtered set of customers. Created by Superuser; may start immediately or at a scheduled time. Stored as Broadcast entity. |
| opt_out_marketing | Boolean flag on Customer. When true, Customer is excluded from all Broadcast recipient lists. Toggled by Customer from own profile card. |
| Номер клиента | Customer identifier shown on discount card (scenario 03) and entered by staff in scenario 10. Exact field TBD — see open question in scenario 03. |
| staff_keyboard | Persistent keyboard for Staff (`is_owner = false`, `customer_mode = false`). Button routing: `specs/ux-style-guide.md` §2.1. |
| superuser_keyboard | Persistent keyboard for Superuser (`is_owner = true`, `customer_mode = false`). Button routing: `specs/ux-style-guide.md` §2.1. |
| FinancialConfig | Singleton DB entity (one row) holding all owner-editable financial parameters: registration discount %, and value/validity/max-pct for survey and birthday coupons. See `specs/entities/financial-config.md`. |
