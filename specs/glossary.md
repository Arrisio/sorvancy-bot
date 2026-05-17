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
| Coupon | Single-use monetary benefit issued to a Customer. Covers part of purchase up to `value` rubles and `max_payment_pct`% of total. Expires at `valid_until`. |
| registered_keyboard | Button set for registered users: "Показать код на скидку" + "Мой профиль". |
| unregistered_keyboard | Button set for new users: "Зарегистрироваться и получить скидку". |
| Staff | Store personnel account in the bot — either seller or owner. Created at DB seed (owner) or via contact card forwarding (sellers). |
| Owner | Staff member with `is_owner = true`. Single business owner with elevated permissions. Seeded at DB init. |
| Contact card | Max messenger message type carrying user identity fields (max_user_id, phone, first_name, last_name, username). Used for seller registration flow. |
| Deeplink | Max Messenger URL embedded in customer's QR code. When followed by seller, triggers "show customer profile" command in bot. Synonymous with Ссылка in project terminology. |
| Ссылка | Project term for deeplink. See Deeplink. |
| Профиль (staff view) | Bot message sent to Seller showing customer's discount percent, active coupons (value + expiry), inline coupon buttons, and "Изменить % скидки" button. Triggered by deeplink (scenario 06). Distinct from customer-facing «Мой профиль». |
