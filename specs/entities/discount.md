# Entity: Discount

## Purpose
Not a DB table. Discount is an integer percent stored on Customer. Displayed as QR or text card shown to cashier.

## Structure

- Stored as `customers.discount_percent` (int)
- Source: `config.DISCOUNT_PERCENT` (env var `DISCOUNT_PERCENT`, default 10)
- Same value for all customers (config-level, not per-customer in MVP)

## Display modes

### Primary: QR code image
- Data format: `SORVANCY:DISCOUNT:{max_user_id}:{discount_percent}%`
- Generated with `qrcode` library (box_size=10, border=4)
- Sent as image attachment (`InputMediaBuffer`)
- Triggered by: "Показать код на скидку" button, `/discount` command, `show_discount` callback

### Fallback: text card
- Used when QR generation raises exception
- Format: ASCII box with store name + percent + customer first_name
- Cashier reads text from screen

## Invariants

- discount_percent set once at phase 1 registration, not updated afterward
- QR generated on demand, not stored in DB
- Cashier validates by eye or manual process (no POS integration in MVP)

## Open questions

- [ ] Survey completion promises "+2% discount" in bot message — not implemented. Fix copy or implement increment?
- [ ] Cashier validation: manual eye-check or QR scanner? If scanner, what does scanner do with the data?
- [ ] Future: per-customer discount tiers (loyal customer, birthday month, etc.)?
