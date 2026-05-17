# Scenario: Fallback — Unknown Message

## Goal
User who sent unrecognised message sees a helpful prompt with their keyboard instead of silence.

## Actors
- Any actor (Customer, unregistered User, Staff, Superuser)
- Bot

## Trigger
Text message arrives and no handler in the routing chain matches (falls through all state checks).

## Preconditions
- FSM state is `REGISTERED` or `None` (no active multi-step flow).

## Main flow

1. Bot sends fallback message:
   «Извините, я глупый бот и вас не понял, но вы можете явно выбрать одно из следующих действий.»

2. Bot resends actor-appropriate persistent keyboard (per `specs/keyboards.md`):

   | route | keyboard |
   |-------|----------|
   | `registration` | `unregistered_keyboard` |
   | `customer` | `registered_keyboard` |
   | `staff`, `is_owner = false` | `staff_keyboard` |
   | `staff`, `is_owner = true` | `superuser_keyboard` |

## Alternative flows
None.

## Negative scenarios
None.

## Postconditions
- FSM state unchanged.
- User sees keyboard appropriate for their actor type.

## NFR refs
- nfr/middleware-routing.md: `route` value available from middleware context.

## Open questions
None.
