# NFR: Middleware Routing

## Scope
Every incoming message to the bot — before any handler runs.

## Rules

### User lookup

Middleware executes on each message:

1. Extract `max_user_id` from incoming message
2. Query Staff table for this `max_user_id`
3. If not found in Staff: query Customer table for this `max_user_id`
4. Inject result into handler context (see Context injection below)

### Routing decision

| Lookup result | Route |
|---------------|-------|
| Staff found + `customer_mode = false` | Staff branch (staff/superuser handlers) |
| Staff found + `customer_mode = true` + Customer record exists | Customer branch |
| Staff found + `customer_mode = true` + no Customer record | Registration branch → scenario 01 |
| Customer found (no Staff row) | Customer branch |
| Neither found | Registration branch → scenario 01 |

After successful registration while in `customer_mode = true`: subsequent messages route to Customer branch until superuser unsets the flag via `/mode`.

### `/mode` command exception

`/mode` is intercepted before routing decision. Always handled as superuser command regardless of `customer_mode` value. If sending user has no Staff row with `is_owner = true`: command ignored or rejected.

### Context injection

Middleware injects into handler context:

| Key | Type | Content |
|-----|------|---------|
| `staff` | Staff \| None | Loaded Staff record if found; None otherwise |
| `customer` | Customer \| None | Loaded Customer record if found; None otherwise |
| `route` | enum | `staff` \| `customer` \| `registration` |

Handlers receive pre-loaded entities — no additional DB lookup needed for actor identity.

### Staff in customer_mode: Customer record

When `customer_mode = true`: middleware loads Customer record for the same `max_user_id` (if exists) and injects as `customer`. If no Customer record exists: `customer = None`; routing proceeds to registration branch. Once registration completes, Customer row exists for this `max_user_id`; subsequent messages route to Customer branch.

## Open questions

- [ ] Middleware failure (DB unreachable): reject message silently, or send error to user?
- [ ] Context key name for `route`: confirm naming convention used in codebase.
