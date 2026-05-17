# Scenario: Broadcast Delivery Execution

## Goal
System delivers pending broadcasts to recipients at scheduled time and notifies Owner on completion.

## Actors
- Bot (scheduled job)
- Owner (notification recipient)

## Trigger
Hourly scheduled job fires. Also fires immediately when Broadcast.status is set to `running` during scenario 11 (immediate send path).

## Preconditions
- ≥1 Broadcast exists with status=`pending` AND `scheduled_at ≤ now()`, OR status=`running` with ≥1 BroadcastRecipient in status=`pending`.

## Main flow

1. Job queries Broadcasts: status=`pending` AND `scheduled_at ≤ now()`
2. For each such Broadcast: set status → `running`
3. For each Broadcast with status=`running`: query BroadcastRecipients where status=`pending`
4. For each pending recipient: forward `source_message_id` from `source_chat_id` to recipient's `max_user_id`
5. On successful forward: mark BroadcastRecipient status=`sent`, sent_at=now()
6. On failed forward: mark BroadcastRecipient status=`failed`, store error text; continue to next recipient
7. After all recipients of a Broadcast are processed (no `pending` remain): set Broadcast status=`completed`; update `sent_count`, `failed_count`
8. Bot sends to creating Owner: «Рассылка {id} завершена. Отправлено успешно: {sent_count}. Не удалось доставить: {failed_count}.»

## Alternative flows

### A1: Immediate broadcast (from scenario 11)
- Broadcast created with status=`running`; delivery starts on next job cycle (within ≤1 hour) or immediately if job triggered inline — developer chooses simpler option.

## Negative scenarios

### N1: All recipients failed
- Broadcast still transitions to `completed`; sent_count=0, failed_count=recipient_count.
- Owner notified with full failure stats.

## Postconditions
- Broadcast.status=`completed`
- All BroadcastRecipient rows have status=`sent` or `failed` (none `pending`)
- Owner received completion notification

## NFR refs
- broadcast-delivery.md

## Open questions
- [ ] On bot restart mid-delivery: job expected to re-query `running` broadcasts and resume from pending recipients. Confirm idempotent behavior is desired.
