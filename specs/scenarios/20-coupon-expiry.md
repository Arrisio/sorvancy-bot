# Scenario: Coupon Expiry

## Goal
Expired coupons get status flipped to `expired` in DB automatically, without user action.

## Actors
- Scheduler (system)

## Trigger
Scheduled job fires (daily or configurable interval).

## Preconditions
- DB accessible.
- At least one Coupon with `status = active` AND `valid_until ≤ now()`.

## Main flow
1. Scheduler fires expiry job.
2. System issues bulk update: `status → expired` WHERE `status = active` AND `valid_until ≤ now()`.
3. DB committed. No notifications, no side effects.

## Alternative flows
None.

## Negative scenarios
### N1: No expired coupons found
- Update affects 0 rows. Job exits silently.

## Postconditions
- All coupons with `valid_until ≤ now()` have `status = expired`.
- No `active` coupon with `valid_until ≤ now()` remains in DB.

## NFR refs
- None.

## Open questions
- [ ] Job interval: daily (midnight) or same as birthday_check (once per day at fixed time)?
