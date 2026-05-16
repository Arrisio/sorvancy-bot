# Max Bot API — Документация по библиотеке maxapi

Источник: https://github.com/love-apples/maxapi

**ВАЖНО**: Рабочая документация для разработки. Перед вызовом любого метода бота сверяйся с этим файлом.

---

## Установка

```bash
pip install maxapi
```

Для webhook (FastAPI):
```bash
pip install maxapi[fastapi]
```

Dev-версия:
```bash
pip install git+https://github.com/love-apples/maxapi.git
```

---

## Авторизация

Токен передаётся через `Authorization` header (query param `access_token` — deprecated, возвращает 401).

API endpoint: `https://botapi.max.ru`

---

## Базовая структура

```python
import asyncio
from maxapi import Bot, Dispatcher
from maxapi.types import MessageCreated

bot = Bot('your_token')
dp = Dispatcher()

@dp.message_created()
async def handle(event: MessageCreated):
    await event.message.answer('Привет!')

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
```

---

## Методы бота (Bot)

### Сообщения

```python
send_message(
    chat_id: int = None,
    user_id: int = None,
    text: str,
    attachments: List[Attachment] = None,
    link: NewMessageLink = None,
    notify: bool = None,
    parse_mode: ParseMode = None
) -> SendedMessage
```
*chat_id или user_id — одно из двух обязательно.*

```python
edit_message(
    message_id: str,
    text: str = None,
    attachments: List[Attachment] = None,
    link: NewMessageLink = None,
    notify: bool = None,
    parse_mode: ParseMode = None
) -> EditedMessage

delete_message(message_id: str) -> DeletedMessage

get_messages(
    chat_id: int,
    message_ids: List[str] = None,
    from_time: datetime | int = None,
    to_time: datetime | int = None,
    count: int = 50
) -> Messages

get_message(message_id: str) -> Messages

pin_message(chat_id: int, message_id: str, notify: bool = None) -> PinnedMessage

delete_pin_message(chat_id: int) -> DeletedPinMessage
```

### Информация о боте

```python
get_me() -> User

change_info(
    name: str = None,
    description: str = None,
    commands: List[BotCommand] = None,
    photo: Dict = None
) -> User

set_my_commands(*commands: BotCommand) -> User
```

### Чаты

```python
get_chats(count: int = 50, marker: int = None) -> Chats

get_chat_by_id(id: int) -> Chat

get_chat_by_link(link: str) -> Chat

edit_chat(
    chat_id: int,
    title: str = None,
    pin: str = None,
    notify: bool = None,
    icon: PhotoAttachmentRequestPayload = None
) -> Chat

delete_chat(chat_id: int) -> DeletedChat
```

### Участники чата

```python
get_chat_members(chat_id: int, user_ids: List[str] = None) -> GettedMembersChat

get_chat_member(chat_id: int, user_id: str) -> GettedMembersChat

add_chat_members(chat_id: int, user_ids: List[str]) -> AddedMembersChat

kick_chat_member(chat_id: int, user_id: str, block: bool = None) -> RemovedMemberChat

get_list_admin_chat(chat_id: int) -> GettedListAdminChat

add_list_admin_chat(chat_id: int, user_ids: List[str]) -> AddedListAdminChat

remove_admin(chat_id: int, user_ids: List[str]) -> RemovedAdmin

get_me_from_chat(chat_id: int) -> ChatMember

delete_me_from_chat(chat_id: int) -> DeletedBotFromChat
```

### Обновления и действия

```python
get_updates() -> UpdateUnion

send_action(chat_id: int, action: SenderAction) -> SendedAction

send_callback(
    callback_id: str,
    message: str = None,
    notification: bool = None
) -> SendedCallback
```

### Webhook

```python
# Подписка / отписка
subscribe_webhook(url: str) -> Subscribed
unsubscribe_webhook() -> Unsubscribed
get_subscriptions() -> GettedSubscriptions
```

### Медиа и файлы

```python
get_video(video_token: str) -> Video

get_upload_url(type: UploadType) -> GettedUploadUrl

upload_media(media: InputMedia | InputMediaBuffer) -> UploadedMedia
```

---

## События (Events)

Все хэндлеры — async функции. Декоратор принимает необязательный фильтр.

| Событие | Декоратор | Тип события |
|---------|-----------|-------------|
| Новое сообщение | `@dp.message_created()` | `MessageCreated` |
| Бот добавлен в чат | `@dp.bot_added()` | `BotAdded` |
| Бот удалён из чата | `@dp.bot_removed()` | `BotRemoved` |
| Пользователь запустил бота | `@dp.bot_started()` | `BotStarted` |
| Пользователь остановил бота | `@dp.bot_stopped()` | `BotStopped` |
| Диалог очищен | `@dp.dialog_cleared()` | `DialogCleared` |
| Диалог заглушён | `@dp.dialog_muted()` | `DialogMuted` |
| Диалог разглушён | `@dp.dialog_unmuted()` | `DialogUnmuted` |
| Название чата изменено | `@dp.chat_title_changed()` | `ChatTitleChanged` |
| Нажата кнопка callback | `@dp.message_callback()` | `MessageCallback` |
| Чат создан | `@dp.message_chat_created()` | `MessageChatCreated` |
| Сообщение изменено | `@dp.message_edited()` | `MessageEdited` |
| Сообщение удалено | `@dp.message_removed()` | `MessageRemoved` |
| Пользователь добавлен | `@dp.user_added()` | `UserAdded` |
| Пользователь удалён | `@dp.user_removed()` | `UserRemoved` |

### Пример с фильтром

```python
from maxapi import F
from maxapi.types import MessageCreated, Command

@dp.message_created(F.message.body.text)
async def echo(event: MessageCreated):
    await event.message.answer(f"Повторяю: {event.message.body.text}")

@dp.message_created(Command('start'))
async def on_start(event: MessageCreated):
    await event.message.answer("Добро пожаловать!")
```

---

## Контекст и состояния (MemoryContext)

```python
from maxapi.context import MemoryContext
```

Передаётся как параметр хэндлера автоматически.

```python
MemoryContext(chat_id: int, user_id: int)
```

### Методы

```python
await context.get_data() -> dict          # получить все данные
await context.set_data(data: dict)        # полная замена данных
await context.update_data(**kwargs)       # добавить/изменить ключи
await context.set_state(state)            # установить состояние (None = сброс)
await context.get_state() -> Any          # получить текущее состояние
await context.clear()                     # очистить всё
```

### Пример FSM

```python
from maxapi.types import MessageCreated, Command
from maxapi.context import MemoryContext

class States:
    AWAITING_NAME = 'awaiting_name'
    DONE = 'done'

@dp.message_created(Command('start'))
async def start(event: MessageCreated, context: MemoryContext):
    await context.set_state(States.AWAITING_NAME)
    await event.message.answer("Как вас зовут?")

@dp.message_created(F.message.body.text)
async def get_name(event: MessageCreated, context: MemoryContext):
    state = await context.get_state()
    if state == States.AWAITING_NAME:
        name = event.message.body.text
        await context.update_data(name=name)
        await context.set_state(States.DONE)
        await event.message.answer(f"Привет, {name}!")
```

---

## Клавиатуры

### InlineKeyboardBuilder

```python
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types import CallbackButton, LinkButton

builder = InlineKeyboardBuilder()
builder.row(
    CallbackButton(text="Да", payload="yes"),
    CallbackButton(text="Нет", payload="no")
)
await event.message.answer(text='Подтвердить?', attachments=[builder.as_markup()])
```

### ButtonsPayload (декларативный)

```python
from maxapi.types import ButtonsPayload, CallbackButton

buttons = [
    [CallbackButton(text="Кнопка 1", payload="btn1")],
    [CallbackButton(text="Кнопка 2", payload="btn2")],
]
payload = ButtonsPayload(buttons=buttons)
await event.message.answer(text='Выберите:', attachments=[payload])
```

### Типы кнопок

| Класс | Назначение | Ключевые параметры |
|-------|-----------|-------------------|
| `CallbackButton` | Callback-событие | `text`, `payload` |
| `LinkButton` | Открыть URL | `text`, `url` |
| `ChatButton` | Создать чат | `text`, `chat_title`, `chat_description` |
| `RequestGeoLocationButton` | Запросить геолокацию | `text` |
| `MessageButton` | Быстрое сообщение | `text` |
| `RequestContactButton` | Запросить контакт | `text` |
| `OpenAppButton` | Открыть мини-приложение | `text`, `web_app`, `contact_id` |

Все импортируются из `maxapi.types`.

### Обработка callback

```python
from maxapi.types import MessageCallback
from maxapi.context import MemoryContext

@dp.message_callback()
async def handle_callback(event: MessageCallback, context: MemoryContext):
    payload = event.callback.payload
    await event.bot.send_callback(
        callback_id=event.callback.callback_id,
        notification="Принято"
    )
    # обработать payload...
```

---

## Webhook

### Встроенный aiohttp

```python
async def main():
    await dp.handle_webhook(bot=bot, host='0.0.0.0', port=8080)
```

### FastAPI

```python
pip install maxapi[fastapi]
```

```python
from maxapi.webhook.fastapi import FastAPIMaxWebhook

webhook = FastAPIMaxWebhook(dp=dp, bot=bot)
app = webhook.app

# запуск через uvicorn
```

**Важно**: перед polling удалить webhook-подписку: `await bot.unsubscribe_webhook()`.

---

## Polling

```python
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
```

---

## Доступ к данным события

```python
# В message_created:
event.message.body.text        # текст сообщения
event.message.sender.user_id   # ID отправителя
event.message.sender.name      # имя отправителя
event.message.chat_id          # ID чата

# Ответ:
await event.message.answer(text="...", attachments=[...])

# Прямой вызов метода бота:
await event.bot.send_message(user_id=123, text="...")

# В bot_started:
event.user.user_id             # ID пользователя
event.user.name                # имя пользователя

# В message_callback:
event.callback.payload         # payload кнопки
event.callback.callback_id     # ID для send_callback
event.callback.user.user_id    # ID нажавшего
```

---

## Router (маршрутизация по модулям)

```python
from maxapi import Dispatcher, Router

router = Router()

@router.message_created()
async def handler(event):
    ...

dp = Dispatcher()
dp.include_router(router)
```

---

## SenderAction (индикатор активности)

Показывает статус «пишет...», «отправляет фото...» и т.д.

```python
from maxapi.enums.sender_action import SenderAction

await bot.send_action(chat_id=chat_id, action=SenderAction.TYPING_ON)
await bot.send_action(chat_id=chat_id, action=SenderAction.SENDING_PHOTO)
await bot.send_action(chat_id=chat_id, action=SenderAction.SENDING_VIDEO)
await bot.send_action(chat_id=chat_id, action=SenderAction.SENDING_FILE)
```

---

## Форматирование текста

```python
from maxapi.enums.parse_mode import TextFormat
from maxapi.utils.formatting import (
    Bold, Italic, Underline, Strikethrough,
    Code, Heading, Link, Text, UserMention,
)
```

### Составной текст через Text

```python
content = Text(
    Bold("Жирный"),
    " | ",
    Italic("Курсив"),
    " | ",
    Underline("Подчёркнутый"),
    " | ",
    Strikethrough("Зачёркнутый"),
    "\n\n",
    Heading("Заголовок"),
    "\n",
    Code("print('hello')"),
    "\n\n",
    Link("Max.ru", url="https://max.ru"),
)

# HTML-режим
await event.message.answer(content.as_html(), format=TextFormat.HTML)

# Markdown-режим
await event.message.answer(content.as_markdown(), format=TextFormat.MARKDOWN)
```

### Упоминание пользователя

```python
sender = event.message.sender
content = Text(
    "Привет, ",
    UserMention(sender.full_name, user_id=sender.user_id),
    "!",
)
await event.message.answer(content.as_html(), format=TextFormat.HTML)
```

---

## Медиа: отправка и получение

```python
from maxapi.types.input_media import InputMedia, InputMediaBuffer
```

### Отправка из файла

```python
await bot.send_action(chat_id=chat_id, action=SenderAction.SENDING_PHOTO)
media = InputMedia(path="path/to/image.jpg")
await bot.send_message(chat_id=chat_id, text="Фото:", attachments=[media])
```

### Отправка из буфера (in-memory)

```python
media = InputMediaBuffer(buffer=png_bytes, filename="image.png")
await bot.send_message(chat_id=chat_id, text="Фото:", attachments=[media])
```

### Предзагрузка (upload_media)

Загрузить один раз — отправлять по token многим пользователям.

```python
uploaded = await bot.upload_media(InputMedia(path="image.jpg"))
await bot.send_message(
    chat_id=chat_id,
    text="Отправлено по token:",
    attachments=[uploaded],
)
```

### Обработка входящих вложений

```python
from maxapi.types.attachments.image import Image
from maxapi.types.attachments.video import Video
from maxapi.types.attachments.audio import Audio
from maxapi.types.attachments.file import File
from maxapi.types.attachments.sticker import Sticker

@dp.message_created(F.message.body.attachments)
async def on_attachment(event: MessageCreated) -> None:
    first = event.message.body.attachments[0]
    if isinstance(first, Image):
        label, action = "фото", SenderAction.SENDING_PHOTO
    elif isinstance(first, Video):
        label, action = "видео", SenderAction.SENDING_VIDEO
    elif isinstance(first, (Audio, File)):
        label, action = "файл", SenderAction.SENDING_FILE
    elif isinstance(first, Sticker):
        label, action = "стикер", SenderAction.SENDING_FILE
    else:
        label, action = "вложение", SenderAction.SENDING_FILE

    chat_id = event.message.recipient.chat_id
    await bot.send_action(chat_id=chat_id, action=action)
    await event.message.answer(f"Получено: {label}")

    # Переслать оригинальное сообщение обратно
    await event.message.forward(chat_id=chat_id)
```

---

## Middleware

```python
from maxapi.filters.middleware import BaseMiddleware
```

### Базовая структура

```python
from collections.abc import Awaitable, Callable
from typing import Any

class MyMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event_object: Any,
        data: dict[str, Any],
    ) -> Any:
        # до хендлера
        data["my_key"] = "value"
        result = await handler(event_object, data)
        # после хендлера
        return result
```

### Регистрация

```python
dp.outer_middleware(ErrorHandlingMiddleware())  # внешний (первый в цепочке)
dp.middleware(LoggingMiddleware())              # внутренний
dp.middleware(ThrottleMiddleware(rate=1.0))
```

Порядок: `outer_middleware` → `middleware` → хендлер.

### Инжекция данных в хендлер

Middleware кладёт данные в `data` — хендлер получает их как kwargs:

```python
class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event_object, data):
        data["event_type"] = type(event_object).__name__
        return await handler(event_object, data)

@dp.message_created(F.message.body.text)
async def on_text(event: MessageCreated, event_type: str = "unknown"):
    await event.message.answer(f"Тип: {event_type}")
```

### Rate limiting (ThrottleMiddleware)

```python
import time

class ThrottleMiddleware(BaseMiddleware):
    def __init__(self, rate: float = 1.0):
        self._last_call: dict[int, float] = {}
        self._rate = rate

    async def __call__(self, handler, event_object, data):
        user_id = None
        msg = getattr(event_object, "message", None)
        if msg and getattr(msg, "sender", None):
            user_id = msg.sender.user_id
        callback = getattr(event_object, "callback", None)
        if callback:
            user_id = callback.user.user_id

        if user_id is not None:
            now = time.monotonic()
            if now - self._last_call.get(user_id, 0.0) < self._rate:
                return None  # слишком часто — игнорировать
            self._last_call[user_id] = now

        return await handler(event_object, data)
```

### Перехват ошибок (ErrorHandlingMiddleware)

```python
class ErrorHandlingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event_object, data):
        try:
            return await handler(event_object, data)
        except Exception as exc:
            logging.exception(exc)
            if isinstance(event_object, MessageCreated):
                await event_object.message.answer("Внутренняя ошибка.")
            elif isinstance(event_object, MessageCallback):
                await event_object.answer(notification="Ошибка.")
            return None
```

---

## Типизированные CallbackPayload

Аналог `aiogram CallbackData`. Типизированные payload-классы с автоматической сериализацией/десериализацией.

```python
from maxapi.filters.callback_payload import CallbackPayload
```

### Определение классов

```python
class CategoryPayload(CallbackPayload, prefix="cat"):
    category_id: str

class ItemPayload(CallbackPayload, prefix="item"):
    category_id: str
    item_id: str

class BackPayload(CallbackPayload, prefix="back"):
    pass  # payload без полей — просто маркер
```

### Использование в кнопках

```python
payload_str = CategoryPayload(category_id="1").pack()
CallbackButton(text="Электроника", payload=payload_str)
```

### Фильтрация и получение в хендлере

```python
@dp.message_callback(CategoryPayload.filter())
async def on_category(event: MessageCallback, payload: CategoryPayload) -> None:
    # payload автоматически десериализован
    cat_id = payload.category_id
    await event.answer()  # убирает «часики» на кнопке
```

### event.answer() в callback-хендлерах

```python
await event.answer()                          # тихое подтверждение
await event.answer(notification="Готово!")    # всплывающее уведомление
```

### Пример: каталог товаров с навигацией

```python
from maxapi.filters.callback_payload import CallbackPayload
from maxapi.types.attachments.buttons.callback_button import CallbackButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

class CategoryPayload(CallbackPayload, prefix="cat"):
    category_id: str

class ItemPayload(CallbackPayload, prefix="item"):
    category_id: str
    item_id: str

CATEGORIES = {"1": "Электроника", "2": "Одежда"}
ITEMS = {
    "1": {"101": "Смартфон", "102": "Ноутбук"},
    "2": {"201": "Футболка"},
}

@dp.message_created(CommandStart())
async def on_start(event: MessageCreated) -> None:
    builder = InlineKeyboardBuilder()
    for cat_id, cat_name in CATEGORIES.items():
        builder.row(CallbackButton(
            text=cat_name,
            payload=CategoryPayload(category_id=cat_id).pack(),
        ))
    await event.message.answer("Выберите категорию:", attachments=[builder.as_markup()])

@dp.message_callback(CategoryPayload.filter())
async def on_category(event: MessageCallback, payload: CategoryPayload) -> None:
    await event.answer()
    items = ITEMS.get(payload.category_id, {})
    builder = InlineKeyboardBuilder()
    for item_id, item_name in items.items():
        builder.row(CallbackButton(
            text=item_name,
            payload=ItemPayload(category_id=payload.category_id, item_id=item_id).pack(),
        ))
    await bot.send_message(
        user_id=event.callback.user.user_id,
        text="Выберите товар:",
        attachments=[builder.as_markup()],
    )

# Fallback для неизвестных payload
@dp.message_callback(F.callback.payload)
async def on_unknown(event: MessageCallback) -> None:
    await event.answer(notification="Действие не поддерживается.")
```

---

## Администрирование чата

### Команды управления

```python
# Закрепить сообщение (reply-контекст)
linked = event.message.link
if linked:
    await bot.pin_message(chat_id=chat_id, message_id=linked.message.mid)

# Удалить сообщение
await bot.delete_message(message_id=linked.message.mid)

# Редактировать сообщение
await bot.edit_message(message_id=message_id, text="Новый текст")

# Информация о чате
chat = await bot.get_chat_by_id(id=chat_id)
# chat.title, chat.chat_id, chat.type, chat.participants_count

# Список участников (первые N)
result = await bot.get_chat_members(chat_id=chat_id, count=10)
for m in result.members:
    print(m.full_name, m.user_id)
```

### Системные события чата

```python
from maxapi.types.updates.chat_title_changed import ChatTitleChanged
from maxapi.types.updates.user_added import UserAdded
from maxapi.types.updates.user_removed import UserRemoved

@dp.chat_title_changed()
async def on_title_changed(event: ChatTitleChanged) -> None:
    # event.chat_id, event.title, event.user.full_name
    await bot.send_message(
        chat_id=event.chat_id,
        text=f"Название изменено на «{event.title}»",
    )

@dp.user_added()
async def on_user_added(event: UserAdded) -> None:
    # event.chat_id, event.user.full_name, event.user.user_id
    await bot.send_message(chat_id=event.chat_id, text=f"Привет, {event.user.full_name}!")

@dp.user_removed()
async def on_user_removed(event: UserRemoved) -> None:
    await bot.send_message(chat_id=event.chat_id, text=f"{event.user.full_name} покинул чат.")
```

---

## Дополнительные поля событий

```python
# Доступ к chat_id через recipient
chat_id = event.message.recipient.chat_id

# Linked message (сообщение, на которое ответили)
linked = event.message.link
if linked:
    mid = linked.message.mid  # ID сообщения

# full_name отправителя
full_name = event.message.sender.full_name

# Пересылка сообщения
await event.message.forward(chat_id=chat_id)
```
