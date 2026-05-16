Есть идея формировать ФРД, ну, и требования на разработке для и агента через систему описания сущности из конкретных сценариев. Да, тот душный сценарий регистрации, сценарий покупки, сценарий выделения бонусных баллов укона. И допустим, три необходимости какого-либо изменения. Я ношу изменения в сценарий, а им агент claude code уже сам как в дельту, но изменения в год. Насколько жизнеспособны и оправданы такой подход для этапа MVP текущего бота, насколько он применяется, как best practice агентной разработки. Если целесообразен, то предложи шаблон описания сце8:04 PMClaude responded: Сценарно-ориентированная разработка для MVP ботаСценарно-ориентированная разработка для MVP бота
Type B: [Рекомендация, уверенность 8/10]
Подход жизнеспособен, более того — близок к индустриальному стандарту для агентной разработки. Называется по-разному: scenario-driven development, BDD-lite, spec-first agentic workflow. Anthropic, Cursor, Aider — все толкают примерно туда же.
Почему работает для агента
Агент (Claude Code в том числе) лучше работает с декларативным описанием поведения, чем с императивными ТЗ. Сценарий = чёрный ящик с входом, выходом, состояниями. Агент сам выводит:

модели данных (из упоминаемых сущностей)
API/handlers (из триггеров и шагов)
валидации (из ограничений в шагах)
тесты (сценарий = готовый test case)

Когда меняешь сценарий — агент диффает старую и новую версию, генерит миграцию + патч кода. Это работает потому, что сценарий — single source of truth, а не разбросанные требования.
Где подход проседает
Не панацея. Слабые места:
Нефункциональные требования. Производительность, безопасность, retention PII, идемпотентность — в сценарии прячутся плохо. Нужен отдельный раздел NFR или cross-cutting concerns.
Архитектурные решения. Сценарий не скажет "используй repository pattern" или "FSM здесь, а не там". Это слой выше — ADR (Architecture Decision Records) рядом со сценариями.
Граничные случаи. Сценарий описывает happy path + явные альтернативы. Редкие edge cases агент додумывает сам, и тут он часто фантазирует. Нужны явные negative scenarios.
Дрейф документации. Если код менялся мимо сценария — расхождение. Лечится тем, что код всегда генерится из сценария, не наоборот. Дисциплина.
Применимость для текущего MVP
Для бота Сорванцов — почти идеально. Причины:

Домен узкий: регистрация, профиль, скидка, потом покупки/баллы
Сценариев мало (4-6 на MVP)
Бот по природе сценарен — пользователь идёт по веткам диалога
FSM регистрации = буквально сценарий в коде
Max API молодой, лучше держать абстракцию над ним отдельно — сценарий описывает что, адаптер решает как

Best practice или нет
Полноценный BDD (Gherkin + Cucumber) — устаревает, тяжёл. Но облегчённая сценарная спецификация для LLM-агентов — это растущая практика. Шаблоны от:

GitHub Spec Kit (spec-driven development для агентов) — https://github.com/github/spec-kit
Anthropic Claude Code best practices — рекомендуют writing specs before code — https://www.anthropic.com/engineering/claude-code-best-practices
Cursor rules / AGENTS.md — тот же паттерн, но рассыпан по правилам

Подтверждаю: search показал, что spec-driven development именно для агентов оформился в 2024-2025 как отдельная практика, не маркетинг.
Шаблон описания сценария
Предлагаю двухуровневую структуру: каталог сущностей + сценарии. Сущности живут отдельно, сценарии на них ссылаются. Так агент не дублирует поля при изменениях.
Файловая структура
/specs
  /entities
    customer.md
    kid.md
    discount.md
  /scenarios
    01-registration.md
    02-discount-issuance.md
    03-profile-edit.md
  /nfr
    security.md
    pii-retention.md
  /adr
    001-fsm-choice.md
    002-db-access-pattern.md
  glossary.md
Шаблон сущности (entities/customer.md)
markdown# Entity: Customer

## Purpose
Registered store customer with profile and kids.

## Fields
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | server-generated |
| max_user_id | bigint | unique, not null | from Max API |
| full_name | text | not null, 2-100 chars | |
| phone | text | E.164, unique, not null | validated on input |
| discount_code | text | unique, nullable | issued once post-registration |
| created_at | timestamptz | not null | |
| updated_at | timestamptz | not null | |

## Invariants
- One Customer per max_user_id
- discount_code issued exactly once, never regenerated
- phone normalized to E.164 before persistence

## Relations
- has_many: Kid (cascade delete)

## PII classification
- full_name, phone: PII level 2
- See nfr/pii-retention.md

## States
N/A (no lifecycle states)
Шаблон сценария (scenarios/01-registration.md)
markdown# Scenario: Customer Registration

## Goal
New user registers, provides personal data + kids data, receives discount code.

## Actors
- User (unregistered, interacts via Max bot)
- Bot
- Database

## Preconditions
- User has Max account
- User started chat with bot (sent /start or equivalent)
- No Customer exists with this max_user_id

## Trigger
User sends /start command.

## Main flow

1. Bot greets, explains program, asks for full name
   - Input: text, 2-100 chars, cyrillic + spaces + hyphen
   - On invalid: re-prompt with error "Имя должно быть от 2 до 100 символов"

2. Bot requests phone
   - Preferred: Max "share contact" button
   - Fallback: text input, normalized to E.164
   - On duplicate phone in DB: error "Этот номер уже зарегистрирован"

3. Bot asks "Add a kid?" [Yes / Finish]
   - If Yes → step 4
   - If Finish and zero kids added → error "Add at least one kid"
   - If Finish and ≥1 kid → step 8

4. Bot asks kid's name (same validation as customer name)

5. Bot asks kid's gender [Boy / Girl]

6. Bot asks kid's DOB
   - Format: DD.MM.YYYY
   - Validation: age 0-18, not in future

7. Bot asks school grade
   - Range: 0-11 (0 = not in school yet)
   - Auto-suggest based on DOB, user can override
   - Return to step 3

8. Bot persists Customer + Kids atomically (single transaction)

9. Bot generates discount_code (see entities/discount.md)

10. Bot sends confirmation with discount_code

## Alternative flows

### A1: User abandons mid-flow
- Partial state stored in FSM (Redis/in-memory)
- TTL: 24h
- On /start within TTL: resume from last step
- On /start after TTL: restart

### A2: User sends /cancel
- FSM cleared
- No DB writes
- Bot responds "Регистрация отменена"

## Negative scenarios

### N1: DB write fails on step 8
- No partial data persists (transaction rollback)
- User sees: "Произошла ошибка, попробуйте /start"
- Error logged with max_user_id

### N2: Already registered user runs /start
- Bot detects existing Customer by max_user_id
- Skips registration, shows profile + discount code

## Postconditions
- Customer row exists
- ≥1 Kid row linked to Customer
- discount_code persisted on Customer
- FSM state cleared

## Data touched
- Customer (created)
- Kid (created, 1..N)

## Idempotency
- Re-running /start does not create duplicate Customer
- Re-clicking buttons within a step is no-op

## NFR refs
- security.md: phone validation, rate limit on /start
- pii-retention.md: kid DOB handling

## Open questions
- [ ] Max API: supports "share contact" button? Verify.
- [ ] Phone format for non-RU numbers — accept or reject?
Шаблон NFR (nfr/security.md)
markdown# NFR: Security

## Applies to
All scenarios involving user input or PII.

## Rules

### Input validation
- All text inputs: length cap, type check, sanitize before logging
- Phone: E.164 strict, reject otherwise
- DOB: parse strict format, reject ambiguous

### Rate limiting
- /start: max 5 per max_user_id per hour
- Registration flow steps: max 30 inputs per session

### Logging
- Never log full phone, only last 4 digits
- Never log kid names in plain text — hash for correlation
- discount_code: log only on issuance event, not on every read

### Secrets
- Bot token, DB URL, Redis URL: .env only
- pydantic-settings for loading
- No defaults in code for production secrets
Шаблон ADR (adr/001-fsm-choice.md)
markdown# ADR 001: FSM Implementation

## Status
Accepted, 2026-05-16

## Context
Registration flow has 8+ steps with branching. Need state persistence across user messages.

## Decision
Custom FSM on top of Redis. Max SDK does not provide aiogram-style FSM.

## Alternatives considered
- In-memory FSM: rejected, loses state on restart
- DB-backed FSM: rejected, write amplification

## Consequences
+ Survives restarts
+ TTL natively supported by Redis
- Extra infra dependency (Redis)

## Open
- [ ] Confirm Max API does not have built-in conversation state
Workflow при изменениях
Допустим, добавляешь второго ребёнка-обязательного. Процесс:

Правишь scenarios/01-registration.md — меняешь шаг 3 ("at least one" → "at least two")
Коммитишь дельту
Скармливаешь агенту: "Apply spec diff from commit X to codebase"
Агент диффает старый и новый сценарий, генерит:

правку валидации в handler
новый тест на N2-like case
возможно миграцию, если изменилась модель



Ключевая дисциплина — код никогда не правится без правки спеки. Иначе расхождение. Можно ввести pre-commit hook, проверяющий что в одном коммите тронуты и spec, и код.
Что делать прямо сейчас
Если идея заходит — начнём с того, что я набросаю:

glossary.md — словарь домена (Customer, Kid, Discount, FSM state names)
entities/*.md — три сущности
scenarios/01-registration.md — полный сценарий регистрации по шаблону
nfr/pii-retention.md — что критично для детских данных

Потом по этим артефактам Claude Code соберёт скелет проекта. Дальше — добавляем сценарий выдачи скидки, профиля, и т.д.
Подтверждаешь подход и начинаем со словаря + сущностей? Или сначала хочешь увидеть полный пример одного сценария вживую на регистрации?