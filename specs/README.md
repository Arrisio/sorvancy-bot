# Specs — Developer Agent Guide

Instructions for an AI coding agent implementing features in this project.

---

## What this project is

Max messenger loyalty bot for **Сорванцы** (children's clothing store).
Customers register via bot, get a discount card (QR), and manage their profile.
Staff look up customers and redeem coupons. Owner manages broadcasts and staff.

---

## Stack

| Layer | Tech |
|-------|------|
| Bot framework | `maxapi` (Max messenger SDK) |
| Language | Python 3.12+ async |
| DB | PostgreSQL via SQLAlchemy async (`asyncpg` driver) |
| ORM | SQLAlchemy 2.x declarative (`src/db/orm.py`) |
| Session factory | `async_sessionmaker` (`src/db/connection.py`) |
| FSM state | `maxapi.context.MemoryContext` — in-memory, lost on restart |
| Config | `config.py` + `.env` via `python-dotenv` |

---

## Codebase layout

```
src/
  db/
    connection.py     # engine + session factory (singleton)
    orm.py            # SQLAlchemy models (source of truth for DB schema)
  models/             # DB access functions per entity (async, session-scoped)
    customer.py
    child.py
  handlers/           # maxapi event handlers, registered via dp.*()
    start.py
    registration.py
  services/           # pure logic (QR generation, message formatters)
    discount.py
  states.py           # FSM state string constants
  keyboards.py        # keyboard/button builder functions

specs/                # THIS directory — full product spec
```

---

## How to read specs before implementing

**Always read before coding.** For any feature:

1. **Scenario** (`specs/scenarios/NN-slug.md`) — what the feature does, step by step, preconditions, postconditions, edge cases
2. **Entity** (`specs/entities/<name>.md`) — DB fields, invariants, relations
3. **Keyboards** (`specs/keyboards.md`) — which keyboard belongs to which actor
4. **NFR** (`specs/nfr/`) — cross-cutting rules (PII, middleware routing, broadcast delivery)
5. **Glossary** (`specs/glossary.md`) — term definitions; check before inventing names

Read in that order. Do not invent behavior not described in specs.

---

## Implementing a scenario — checklist

```
[ ] Read scenario file fully, including Open questions
[ ] Read all entity files referenced in the scenario
[ ] Read existing src/ code to find what already exists
[ ] Note spec↔code divergences (see Known divergences section below)
[ ] Add missing ORM columns to src/db/orm.py
[ ] Add/update model functions in src/models/<entity>.py
[ ] Register handlers in src/handlers/<feature>.py
[ ] Add keyboard builders to src/keyboards.py if needed
[ ] Add FSM states to src/states.py if needed
```

---

## Key patterns from existing code

### Handler registration

```python
async def register_foo_handlers(dp):
    @dp.message_created(F.message.body.text == SOME_BTN_TEXT)
    async def on_foo(event: MessageCreated, context: MemoryContext):
        ...
```

Handlers are registered inside an `async def register_*_handlers(dp)` function. Call these from the main entrypoint.

### DB session usage

```python
async with get_session_factory()() as session:
    customer = await customer_model.get_by_max_id(session, user_id)
    # session commits on exit if no exception
```

Never share sessions across handler calls. One `async with` block per handler.

### FSM state

```python
state = await context.get_state()
await context.set_state(RegistrationState.REGISTERED)
await context.update_data(key=value)
data = await context.get_data()
```

MemoryContext is per-user, in-memory. **Lost on bot restart.** Do not rely on it for data that must survive restarts (use DB instead).

### Sending messages

```python
await bot.send_message(user_id=user_id, text="...", attachments=[keyboard()])
await event.message.answer(text="...", attachments=[keyboard()])
```

### Keyboards

`src/keyboards.py` exports builder functions returning `ButtonsPayload.pack()` (reply keyboard) or `InlineKeyboardBuilder.as_markup()` (inline keyboard). Add new builders there.

---

## Middleware routing (not yet implemented)

Described in `specs/nfr/middleware-routing.md`. When implementing:
- Middleware runs on every message before any handler
- Checks Staff table first, then Customer table
- Injects `staff`, `customer`, `route` into context
- `/mode` command intercepted before routing

Until middleware is built, handlers do their own DB lookup (current pattern in `src/handlers/start.py`).

---

## Known spec↔code divergences

These are real inconsistencies between specs and current code. Follow **spec intent** when implementing; note the divergence if leaving old code in place.

| Location | Spec says | Code has | Action |
|----------|-----------|----------|--------|
| Scenario 03 / keyboards.md | Button: «Скидка» | `SHOW_DISCOUNT_BTN_TEXT = "Показать код на скидку"` | Rename constant when implementing scenario 03 |
| Customer entity | Fields: `survey_completed`, `opt_out_marketing` | Not in `src/db/orm.py` | Add columns + migration |
| Staff entity | Full Staff model with `is_owner`, `customer_mode` | No Staff ORM model exists | Create `src/db/orm.py` Staff class |
| Coupon entity | Full Coupon model | No Coupon ORM model | Create |
| Broadcast / BroadcastRecipient | Full models | No ORM models | Create |
| `src/states.py` | Spec uses `AWAITING_NAME` | Code has `AWAITING_FIRST_NAME` | Use code name; update spec if needed |
| Child.birthdate | Spec: nullable (optional) | ORM: `nullable=False` | Fix ORM to match spec |

---

## Open questions — how to handle

Every spec file may have an `## Open questions` section with `[ ]` items. These are **unresolved decisions**.

- **Do not invent answers.** Do not implement a guess.
- If a feature you need to implement has an unresolved open question that blocks you: stop and report it. Do not proceed with assumptions.
- If an open question is irrelevant to the task at hand: skip it and implement what is clear.

---

## What is implemented vs specced

| Area | Spec exists | Code exists |
|------|-------------|-------------|
| Registration (01) | ✓ | ✓ partial |
| Survey (02) | ✓ | ✓ partial |
| Discount QR (03) | ✓ | ✓ partial |
| Staff registration (04) | ✓ | ✗ |
| Profile edit (05) | ✓ | ✗ |
| Show customer profile / staff (06) | ✓ | ✗ |
| Edit discount (07) | ✓ | ✗ |
| Redeem coupon (08) | ✓ | ✗ |
| Staff list (09) | ✓ | ✗ |
| Find customer by ID (10) | ✓ | ✗ |
| Broadcast create (11) | ✓ | ✗ |
| Broadcast list (12) | ✓ | ✗ |
| Excel export (13) | ✓ | ✗ |
| Switch customer mode (14) | ✓ | ✗ |
| Middleware routing | ✓ NFR | ✗ |
| Staff ORM model | ✓ entity | ✗ |
| Coupon ORM model | ✓ entity | ✗ |
| Broadcast ORM models | ✓ entity | ✗ |
