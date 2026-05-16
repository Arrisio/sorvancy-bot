# NFR: PII Handling

## Scope
All personal data collected or stored by bot.

## Data classification

| Data | Class | Notes |
|------|-------|-------|
| max_user_id | Internal ID | Not PII; messenger-assigned, not linkable outside Max |
| max_username | Low sensitivity | User-chosen display name |
| first_name | PII | Customer-provided |
| birthdate (Customer) | PII | Customer-provided |
| Child.name | PII (minor) | Higher protection: data of a child |
| Child.birthdate | PII (minor) | Enables age inference |
| Child.gender | PII (minor) | |
| phone | PII | Reserved column; not yet collected |

## Rules

### Logging
- Never log Child names or birthdates in plaintext
- max_user_id: safe to log (internal identifier)
- first_name: OK at INFO level for operation confirmation; not in debug loops

### Storage
- All PII stored in PostgreSQL only
- MemoryContext holds PII only during active survey (in-flight; lost on restart)
- On survey cancel or completion: PII moves to DB or is discarded; MemoryContext not explicitly cleared but irrelevant post-`REGISTERED` state

### Secrets
- BOT_TOKEN, DB credentials: `.env` file only, never in code
- Loaded via `python-dotenv` in `config.py`

## Open questions
- [ ] Russian 152-ФЗ compliance: data subject deletion/export rights — not implemented. Required before production?
- [ ] Children data (minors): does parental consent flow need to be explicit in bot UX?
- [ ] Retention policy: how long to keep Customer/Child data if user never returns?
