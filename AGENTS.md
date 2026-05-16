# AGENTS.md — Инструкции для Claude Code

## О проекте

Бот для мессенджера **Max** магазина детской одежды **Сорванцы**.

Задачи бота:
- Регистрация покупателей с данными о детях
- Выдача фиксированной скидки после регистрации
- Будущее: маркетинговые рассылки по сегментам (день рождения, школьники и т.д.)

## Specs

Project specs live in `specs/`. Read relevant specs before implementing features or changing behavior.

```
specs/
├── glossary.md          # domain terms
├── entities/            # data model specs (customer, child, discount)
├── scenarios/           # user-facing behavior specs
└── nfr/                 # non-functional requirements
```

To generate or update specs from a natural language description, use `/spec-analyst`.

## Критическое требование: Max Bot API

**ОБЯЗАТЕЛЬНО** перед реализацией любых методов бота читай `docs/max-botapi.md`.
Не выдумывай сигнатуры методов и параметры — опирайся только на документацию.

Библиотека: `maxapi` (установка: `pip install maxapi`, источник: https://github.com/love-apples/maxapi)

Ключевые паттерны из документации:
- Бот: `Bot(token)`, диспетчер: `Dispatcher()`
- Polling: `await dp.start_polling(bot)`
- Handlers: `@dp.message_created()`, `@dp.bot_started()`, `@dp.message_callback()` и др.
- Состояния: `MemoryContext` из `maxapi.context` (get_state/set_state/update_data/get_data/clear)
- Клавиатуры: `InlineKeyboardBuilder` или `ButtonsPayload` + типы кнопок
- Ответ на сообщение: `await event.message.answer(text, attachments=[...])`

## Структура проекта

```
max-bot/
├── AGENTS.md               # этот файл — главные инструкции
├── CLAUDE.md               # перенаправляет сюда
├── README.md
├── pyproject.toml
├── .env                    # секреты (не в git)
├── .env.example
├── main.py                 # точка входа
├── config.py               # настройки из .env
├── docs/
│   └── max-botapi.md       # документация по API (читать перед разработкой)
├── src/
│   ├── states.py           # enum состояний регистрации
│   ├── keyboards.py        # фабрики клавиатур
│   ├── db/
│   │   ├── connection.py   # пул asyncpg
│   │   └── migrations.sql  # DDL схемы БД
│   ├── handlers/
│   │   ├── start.py        # /start, приветствие
│   │   └── registration.py # FSM регистрации
│   ├── models/
│   │   ├── customer.py     # CRUD покупателей
│   │   └── child.py        # CRUD детей
│   └── services/
│       └── discount.py     # логика скидок
└── scripts/
    └── migrate.py          # запуск миграций БД
```

## Схема БД

### customers
| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL PK | |
| max_user_id | BIGINT UNIQUE NOT NULL | ID пользователя в Max |
| max_username | VARCHAR(255) | username в Max |
| first_name | VARCHAR(255) | |
| last_name | VARCHAR(255) | |
| phone | VARCHAR(20) | |
| discount_percent | INT DEFAULT 10 | фиксированная скидка |
| registered_at | TIMESTAMPTZ DEFAULT NOW() | |

### children
| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL PK | |
| customer_id | INT FK → customers.id | |
| name | VARCHAR(255) | имя ребенка |
| gender | VARCHAR(10) | 'male' / 'female' |
| birthdate | DATE | дата рождения |
| created_at | TIMESTAMPTZ DEFAULT NOW() | |

## Запуск регистрации

Покупатель сканирует QR-код на кассе → нажимает «Старт» в Max → автоматически запускается сценарий.
Регистрация возможна и вне кассы (ссылка на бота).

## Сценарий регистрации (FSM)

Состояния определены в `src/states.py`:

1. `/start` или `bot_started` → проверяем регистрацию
   - уже зарегистрирован → приветствие + кнопка «Показать скидку»
   - не зарегистрирован → запускаем FSM
2. `AWAITING_FIRST_NAME` → имя
3. `AWAITING_LAST_NAME` → фамилия
4. `AWAITING_PHONE` → телефон
5. `AWAITING_CHILD_NAME` → имя ребёнка
6. `AWAITING_CHILD_GENDER` → пол (кнопки: Мальчик / Девочка)
7. `AWAITING_CHILD_BIRTHDATE` → дата рождения (ДД.ММ.ГГГГ)
8. `AWAITING_MORE_CHILDREN` → добавить ещё? (кнопки: Да / Нет)
9. `REGISTERED` → сохранить в БД, показать кнопку «Показать скидку»

Дети буферизуются в `MemoryContext` как список, customer + все children сохраняются в одной транзакции.

## Показ скидки

- Кнопка «🏷 Показать скидку кассиру» — inline callback `show_discount`
- Команда `/discount`
- Показывается карточка с именем покупателя и размером скидки — покупатель показывает экран кассиру

## Правила разработки

1. Async везде (asyncio, SQLAlchemy async, maxapi)
2. Конфиг только через `config.py` (python-dotenv), никаких хардкодов
3. БД через SQLAlchemy ORM (`src/db/orm.py` — mapped classes `Customer`, `Child`); сессия через `get_session_factory()()` как async context manager; не открывать прямые соединения в хэндлерах
4. Обработка ошибок: логировать, не падать
5. Состояния хранить в `MemoryContext` (in-memory, встроено в maxapi)
6. Модели (`customer.py`, `child.py`) — только ORM-запросы (`select`, `session.add`, `flush`), никакой бизнес-логики; принимают `AsyncSession`, возвращают ORM-объекты
7. Скидка в процентах берётся из `config.DISCOUNT_PERCENT`

## Рассылки (будущее)

Планируется отдельный cron-скрипт `scripts/newsletter.py`:
- Выборка по дате рождения детей → рассылка накануне ДР
- Выборка школьников → рассылка в августе
- Выборка по полу → гендерные кампании

Пока не реализовывать, но проектировать БД с учётом этих запросов.

## Переменные окружения

| Переменная | Описание |
|-----------|----------|
| `BOT_TOKEN` | Токен бота Max |
| `DB_HOST` | Хост PostgreSQL |
| `DB_PORT` | Порт (5432) |
| `DB_NAME` | Имя БД |
| `DB_USER` | Пользователь БД |
| `DB_PASSWORD` | Пароль БД |
| `DISCOUNT_PERCENT` | Размер скидки (%) |


## Language Rules

- All AI ↔ developer communication (responses, explanations, docs, comments): **English**
- Bot user-facing text (messages, buttons, prompts to customers): **Russian**
- AGENTS.md and technical docs: **English**

## Output Style: Caveman Mode (Always On)

All natural-language output in this project MUST follow the rules below,
equivalent to the `/caveman full` mode of the `caveman` skill
(https://github.com/JuliusBrussee/caveman). No invocation needed — this is the
permanent default for every agent in this repository.

# Caveman Mode

## Core Rule

Respond like smart caveman. Cut articles, filler, pleasantries. Keep all technical substance.

## Grammar

* Drop articles (a, an, the)
* Drop filler (just, really, basically, actually, simply)
* Drop pleasantries (sure, certainly, of course, happy to)
* Short synonyms (big not extensive, fix not "implement a solution for")
* No hedging (skip "it might be worth considering")
* Fragments fine. No need full sentence
* Technical terms stay exact. "Polymorphism" stays "polymorphism"
* Code blocks unchanged. Caveman speak around code, not in code
* Error messages quoted exact. Caveman only for explanation

## Pattern

```
[thing] [action] [reason]. [next step].
```

Not:

> Sure! I'd be happy to help you with that. The issue you're experiencing is likely caused by...

Yes:

> Bug in auth middleware. Token expiry check use `<` not `<=`. Fix:

## Examples

**User:** Why is my React component re-rendering?

**Normal (69 tokens):** "The reason your React component is re-rendering is likely because you're creating a new object reference on each render cycle. When you pass an inline object as a prop, React's shallow comparison sees it as a different object every time, which triggers a re-render. I'd recommend using useMemo to memoize the object."

**Caveman (19 tokens):** "New object ref each render. Inline object prop = new ref = re-render. Wrap in `useMemo`."

---

**User:** How do I set up a PostgreSQL connection pool?

**Caveman:**

```
Use `pg` pool:
```

```
const pool = new Pool({
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
})
```

```
max = concurrent connections. Keep under DB limit. idleTimeout kill stale conn.
```

## Auto-clarity rule

Caveman drops to normal prose for security warnings, irreversible-action confirmations, multi-step sequences where fragment ambiguity risks misread, and when user repeats a question. Resumes after the clear part.

## Boundaries

* Code: write normal. Caveman English only
* Git commits: normal
* PR descriptions: normal
* User say "stop caveman" or "normal mode": revert immediately