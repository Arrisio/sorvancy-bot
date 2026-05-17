# Scenario: Contact Seller

## Goal
Customer initiates contact with store staff from bot.

## Actors
- Customer (registered)
- Bot

## Trigger
Customer clicks «Связаться с продавцом» button.

## Preconditions
- Customer exists in DB

## Main flow

> **TODO: main flow content TBD**

1. Customer clicks «Связаться с продавцом»
2. Bot handles button press
3. `Customer.last_touch` set to current datetime
4. *(Further steps TBD)*

## Alternative flows

> TBD

## Negative scenarios

> TBD

## Postconditions
- `Customer.last_touch` set to current datetime
- *(Further postconditions TBD)*

## NFR refs
- TBD

## Open questions
- [ ] Main flow content: what does bot do after Customer clicks «Связаться с продавцом»? (UI, message, contact info shown, etc.)
