# Scenario: Profile Editing

## Goal
Registered user views their profile; if questionnaire not started — offered to fill it; otherwise edits profile fields and children list.

## Actors
- User (registered, survey_completed = true or false)
- Bot
- Database

## Trigger
User clicks «Мой профиль» button in registered keyboard (payload `profile:view`).

## Preconditions
- Customer record exists in DB (scenario 01 complete)
- FSM state = REGISTERED

## Main flow

### Profile card

1. Bot checks if questionnaire started (see A5 for unfilled case).

2. Bot sends profile card message:

```
👤 Ваш профиль

Имя: Анна
Фамилия: Смирнова
Дата рождения: 15.03.1985

👧 Дети:
  1. Маша · Девочка · 12.06.2018
  2. Артём · Мальчик · —

[✏️ Имя]            [✏️ Фамилия]
[✏️ Дата рождения]  [✏️ Телефон]
[👶 Управление детьми]
[Отказаться от рассылок] / [Получать рассылки]
[← Главное меню]
```

Fields with null values shown as «не указано». If 0 children: no children section; [👶 Управление детьми] still shown.

Opt-out button label depends on `opt_out_marketing` flag:
- `false` → button: «Отказаться от рассылок»
- `true` → button: «Получать рассылки»

Clicking either toggles `opt_out_marketing` in DB and refreshes profile card with updated button label.

2. User presses any button.

### Editing a customer field

Triggered by any [✏️ X] button on profile card.

3. Bot sends single field re-ask message:

```
Введите новое значение — [field label]:
Текущее: [current value / не указано]

[Оставить текущее]  [Очистить поле]  [← Назад]
```

For optional fields (last_name, birthdate, phone): [Очистить поле] shown — sets field to null.
For required field (first_name): [Очистить поле] not shown.

4. User types new value or clicks [Оставить текущее] / [Очистить поле].

5. Bot writes update to DB immediately. Bot edits profile card message with updated data. State returns to REGISTERED (profile card shown).

### Children management

Triggered by [👶 Управление детьми] on profile card.

6. Bot sends children list:

```
👶 Ваши дети:
  1. Маша · Девочка · 12.06.2018 (7 лет)
  2. Артём · Мальчик · — 

[✏️ Маша]  [✏️ Артём]
[➕ Добавить ребёнка]
[← Назад к профилю]
```

7. User selects action.

#### 7a. Edit existing child

User clicks [✏️ Child name] → bot sends child card:

```
👧 Маша
Пол: Девочка
Дата рождения: 12.06.2018

[✏️ Имя]   [✏️ Пол]   [✏️ Дата рождения]
[🗑 Удалить]
[← Назад к списку]
```

User clicks [✏️ X]:
- Bot sends single question for that field (same pattern as customer field editing)
- User answers → DB updated immediately → bot re-shows updated child card

#### 7b. Delete child

User clicks [🗑 Удалить] on child card → confirm prompt:

```
Удалить [Имя] из профиля? Это действие нельзя отменить.

[✅ Да, удалить]  [← Отмена]
```

[✅ Да, удалить] → delete Child record from DB → re-show children list (updated).
[← Отмена] → re-show child card.

#### 7c. Add child

User clicks [➕ Добавить ребёнка] → 3-step sub-form:

| Step | State | Bot sends | User action |
|------|-------|----------|-------------|
| A | ADDING_CHILD_NAME | «Как зовут ребёнка?» + [← Отмена] | Types name |
| B | ADDING_CHILD_GENDER | «Ваш ребёнок — мальчик или девочка?» + [Мальчик] [Девочка] [← Назад] | Clicks button |
| C | ADDING_CHILD_BIRTHDATE | «Когда день рождения у ребёнка? (ДД.ММ.ГГГГ)» + [Пропустить] [← Назад] | Types or skips |

After step C: create Child record in DB (name + gender from session; birthdate or null). Re-show children list with new child added.

Back within add-child sub-form:
- ADDING_CHILD_BIRTHDATE → ADDING_CHILD_GENDER
- ADDING_CHILD_GENDER → ADDING_CHILD_NAME
- ADDING_CHILD_NAME ([← Отмена]) → discard new child draft → re-show children list

[← Назад к списку] from children list → re-show profile card.

## Back navigation

| Current state | Back navigates to |
|--------------|------------------|
| Profile card | REGISTERED — registered keyboard (main menu) |
| Editing customer field | Profile card (no DB write, change discarded) |
| Children list | Profile card |
| Child card | Children list |
| Editing child field | Child card (no DB write, change discarded) |
| Delete confirmation | Child card |
| ADDING_CHILD_NAME | Children list (discard new child draft) |
| ADDING_CHILD_GENDER | ADDING_CHILD_NAME |
| ADDING_CHILD_BIRTHDATE | ADDING_CHILD_GENDER |

## Alternative flows

### A1: Invalid date input (editing birthdate fields)
- Bot: «Не понял дату. Введите в формате ДД.ММ.ГГГГ (разделитель любой):»
- State unchanged, user retries

### A2: DB write fails on field update or child add/delete
- Bot: «Не удалось сохранить изменение. Попробуйте ещё раз.»
- No partial write; user retries from current step

### A3: User has 0 children (never filled child data)
- Profile card: no children section; [👶 Управление детьми] still shown
- Children list shows: «У вас пока нет детей в профиле.» + [➕ Добавить ребёнка] + [← Назад к профилю]

### A4: survey_completed = false, partial data present
- Profile card shown with whatever data exists (fields show «не указано» for null)
- [👶 Управление детьми] available
- Adding child with birthdate → if survey_completed transitions False → True: create Coupon (same rule as scenario 02)

### A5: Questionnaire never started (no fields filled)
- Bot sends simplified profile message:

```
👤 Ваш профиль

Анкета не заполнена

[Заполнить анкету]
[← Главное меню]
```

- [Заполнить анкету] triggers scenario 02 (survey)
- No field edit buttons shown

## MemoryContext keys during profile editing

| Key | Content |
|-----|---------|
| `max_user_id` | Customer identifier |
| `edit.field` | Customer field being edited (e.g., `first_name`) |
| `edit.child_id` | DB id of child being edited/deleted |
| `edit.child_field` | Child field being edited |
| `new_child.name` | Name for child being added (cleared after save) |
| `new_child.gender` | Gender for child being added |

## Postconditions
- Customer fields updated in DB immediately on each confirmed edit
- Child records created, updated, or deleted in DB immediately
- If any edit causes survey_completed to transition False → True: Coupon created
- FSM state = REGISTERED after any action sequence

## NFR refs
- pii.md: child birthdate, name, phone handling

## Open questions
- [ ] Phone editing: phone was collected via contact-share button in survey. Editing via text input (type phone number) or via another contact-share button? Decide UX.
- [ ] Profile card update method: edit existing message in place (requires storing `profile_mid` in session) or send new message? Max messenger API support for editMessageText needed.
- [ ] Children list: show child age (computed from birthdate)? Shown in 7a example — confirm.
- [ ] Max children per customer: no limit defined. Confirm.
- [ ] A5 trigger condition: "never started" = `first_name IS NULL`? Or `survey_completed = false` AND all fields null? Define exact DB check.
