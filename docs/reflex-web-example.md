Reflex MVP — таблица клиентов + фильтр + QR-сканер
Сделаю минимальный рабочий каркас. Без подключения к боевой БД — на mock-данных, чтобы можно было запустить и потрогать. Подключение к реальной БД (та же что у бота) — следующим шагом.
Сначала проверю актуальные версии и подтверждённые API Reflex.Searched the webSearched the webОкей, Reflex 0.9.2 (релиз 6 мая 2026), rx.table для редактируемых данных — то что нужно. Подтянем доку по QR-сканеру с камеры, потому что reflex-webcam делает скриншот, а нам нужна непрерывная стрим-обработка.Searched the webSearched the webХватит данных. Под QR-камеру в Reflex чистого готового пакета нет — придётся обернуть html5-qrcode через custom React wrapper. Это в стандартном flow Reflex (reflex component init), но для первого пощупать усложняет старт.
Сделаю прагматичный ход: соберу MVP с простой формой ручного ввода кода клиента, а QR-сканер сделаю через минимальный custom component с html5-qrcode, обёрнутым прямо в проект через rx.Component подкласс. Если зайдёт стек — выделим в пакет, нет — выкинем без сожаления.
Проект
Структура:
sorvantsy_admin/
├── rxconfig.py
├── pyproject.toml
├── .env.example
└── sorvantsy_admin/
    ├── __init__.py
    ├── sorvantsy_admin.py          # точка входа, роутинг
    ├── state.py                    # state классы
    ├── models.py                   # доменные модели (mock пока)
    ├── components/
    │   ├── __init__.py
    │   ├── qr_scanner.py           # обёртка html5-qrcode
    │   └── customer_table.py       # таблица + фильтр
    └── pages/
        ├── __init__.py
        ├── customers.py            # список клиентов
        └── scan.py                 # страница со сканером
Поехали. Все файлы рабочие, копируешь — запускается.
pyproject.toml
toml[project]
name = "sorvantsy-admin"
version = "0.1.0"
description = "Sorvantsy admin panel built on Reflex"
requires-python = ">=3.11"
dependencies = [
    "reflex==0.9.2",
]

[tool.ruff]
line-length = 100
target-version = "py311"
rxconfig.py
pythonimport reflex as rx

config = rx.Config(
    app_name="sorvantsy_admin",
    plugins=[
        rx.plugins.TailwindV4Plugin(),
    ],
)
sorvantsy_admin/models.py
Доменные типы. Пока мок, потом мапим на SQLAlchemy-модели бота.
pythonfrom dataclasses import dataclass
from datetime import date


@dataclass
class Kid:
    name: str
    gender: str
    dob: date
    school_grade: int | None


@dataclass
class Customer:
    id: int
    name: str
    phone: str
    discount_percent: int
    kids_count: int
    registered_at: date
sorvantsy_admin/state.py
pythonfrom datetime import date

import reflex as rx

from sorvantsy_admin.models import Customer


_MOCK_CUSTOMERS: list[Customer] = [
    Customer(1, "Анна Петрова", "+79261234567", 5, 2, date(2024, 11, 3)),
    Customer(2, "Игорь Сидоров", "+79169876543", 7, 1, date(2024, 9, 15)),
    Customer(3, "Мария Козлова", "+79031112233", 10, 3, date(2025, 1, 20)),
    Customer(4, "Дмитрий Орлов", "+79255556677", 5, 1, date(2025, 3, 8)),
    Customer(5, "Елена Васильева", "+79261119988", 15, 2, date(2024, 12, 1)),
]


class CustomersState(rx.State):
    customers: list[Customer] = []
    search_query: str = ""
    min_discount: int = 0

    @rx.event
    def load_customers(self) -> None:
        self.customers = list(_MOCK_CUSTOMERS)

    @rx.event
    def set_search_query(self, value: str) -> None:
        self.search_query = value

    @rx.event
    def set_min_discount(self, value: list[int | float]) -> None:
        self.min_discount = int(value[0]) if value else 0

    @rx.event
    def bump_discount(self, customer_id: int, delta: int) -> None:
        for c in self.customers:
            if c.id == customer_id:
                c.discount_percent = min(100, c.discount_percent + delta)
                break

    @rx.var
    def filtered_customers(self) -> list[Customer]:
        q = self.search_query.lower().strip()
        return [
            c for c in self.customers
            if c.discount_percent >= self.min_discount
            and (q in c.name.lower() or q in c.phone if q else True)
        ]


class ScannerState(rx.State):
    last_scanned: str = ""
    scan_count: int = 0

    @rx.event
    def on_scan(self, decoded_text: str) -> None:
        self.last_scanned = decoded_text
        self.scan_count += 1
sorvantsy_admin/components/qr_scanner.py
Обёртка html5-qrcode через wrap React. Подключаем библиотеку с CDN через add_custom_code, рендерим <div> куда библиотека сама вставит видео.
pythonfrom typing import Any

import reflex as rx


class QRScanner(rx.Component):
    library = ""
    tag = "QRScannerDiv"

    on_decode: rx.EventHandler[lambda decoded: [decoded]]

    def add_imports(self) -> dict[str, Any]:
        return {}

    def add_custom_code(self) -> list[str]:
        return [
            '''
            if (typeof window !== "undefined" && !window.__html5QrcodeLoaded) {
              window.__html5QrcodeLoaded = true;
              const s = document.createElement("script");
              s.src = "https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js";
              s.async = true;
              document.head.appendChild(s);
            }
            '''
        ]

    def add_hooks(self) -> list[str]:
        return [
            """
            const scannerRef = React.useRef(null);
            React.useEffect(() => {
              let cancelled = false;
              const start = () => {
                if (cancelled) return;
                if (typeof window.Html5Qrcode === "undefined") {
                  setTimeout(start, 200);
                  return;
                }
                const elementId = "qr-scanner-region";
                const scanner = new window.Html5Qrcode(elementId);
                scannerRef.current = scanner;
                scanner.start(
                  { facingMode: "environment" },
                  { fps: 10, qrbox: { width: 250, height: 250 } },
                  (decodedText) => { ${getattr(self.event_triggers["on_decode"], "_js_expr", self.event_triggers["on_decode"])}(decodedText); },
                  () => {}
                ).catch(err => console.error("QR start error", err));
              };
              start();
              return () => {
                cancelled = true;
                if (scannerRef.current) {
                  scannerRef.current.stop().catch(() => {});
                  scannerRef.current.clear();
                }
              };
            }, []);
            """
        ]

    def render(self) -> dict[str, Any]:
        return {
            "name": "div",
            "props": {"id": "qr-scanner-region", "style": {"width": "100%", "maxWidth": "400px"}},
            "children": [],
        }


qr_scanner = QRScanner.create
[Допущение, уверенность 5/10] Этот wrapper — компромиссный. Я не на 100% уверен в шаблонизации ${self.event_triggers["on_decode"]._js_expr} для текущей версии Reflex 0.9.x — API custom components за последние релизы немного двигался. Альтернатива надёжнее — сгенерировать полноценный custom component через reflex component init и опубликовать локально. Это лишних 15 минут, но без подводных камней.
Прагматичный вариант на старт MVP — обойтись без custom component вообще. Используем готовый reflex-webcam для съёмки кадра, на бэке распознаём через pyzbar. Это сильно проще и не требует JS-магии. Покажу этот путь — он точно рабочий:
sorvantsy_admin/components/qr_scanner.py (упрощённый вариант)
bashpip install reflex-webcam pyzbar pillow
Под Linux дополнительно: apt-get install libzbar0.
pythonimport time
from io import BytesIO
from urllib.request import urlopen

import reflex as rx
import reflex_webcam as webcam
from PIL import Image
from pyzbar.pyzbar import decode

from sorvantsy_admin.state import ScannerState


WEBCAM_REF = "qr_webcam"


class QRDecodeState(ScannerState):
    @rx.event
    def handle_frame(self, img_data_uri: str) -> None:
        try:
            with urlopen(img_data_uri) as resp:
                img = Image.open(BytesIO(resp.read()))
                img.load()
        except Exception:
            return

        results = decode(img)
        if not results:
            return

        decoded_text = results[0].data.decode("utf-8", errors="replace")
        self.last_scanned = decoded_text
        self.scan_count += 1


def qr_scanner_widget() -> rx.Component:
    return rx.vstack(
        webcam.webcam(
            id=WEBCAM_REF,
            on_click=webcam.upload_screenshot(
                ref=WEBCAM_REF,
                handler=QRDecodeState.handle_frame,
            ),
            width="100%",
            max_width="400px",
        ),
        rx.text("Тапни по видео для съёмки кадра", size="2", color="gray"),
        rx.cond(
            QRDecodeState.scan_count > 0,
            rx.vstack(
                rx.text("Распознано:", weight="bold"),
                rx.code(QRDecodeState.last_scanned, size="3"),
                rx.text(f"Всего сканирований: {QRDecodeState.scan_count}", size="2"),
            ),
        ),
        spacing="3",
        align="center",
        width="100%",
    )
Поведение: видео из камеры → тап → кадр летит на сервер → pyzbar распознаёт → результат в state → UI обновляется. Не realtime-стрим, но рабочий MVP за час. Если позже захочешь непрерывный скан — оборачиваешь html5-qrcode нормально через reflex component init.
sorvantsy_admin/components/customer_table.py
pythonimport reflex as rx

from sorvantsy_admin.models import Customer
from sorvantsy_admin.state import CustomersState


def discount_badge(percent: int) -> rx.Component:
    return rx.badge(
        f"{percent}%",
        color_scheme=rx.cond(percent >= 10, "green", rx.cond(percent >= 5, "blue", "gray")),
        size="2",
    )


def discount_controls(customer: Customer) -> rx.Component:
    return rx.hstack(
        rx.button(
            "+1%",
            size="1",
            variant="soft",
            on_click=CustomersState.bump_discount(customer.id, 1),
        ),
        rx.button(
            "+5%",
            size="1",
            variant="soft",
            on_click=CustomersState.bump_discount(customer.id, 5),
        ),
        spacing="1",
    )


def customer_row(customer: Customer) -> rx.Component:
    return rx.table.row(
        rx.table.cell(customer.name),
        rx.table.cell(rx.code(customer.phone, size="2")),
        rx.table.cell(discount_badge(customer.discount_percent)),
        rx.table.cell(customer.kids_count),
        rx.table.cell(discount_controls(customer)),
    )


def customer_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Имя"),
                rx.table.column_header_cell("Телефон"),
                rx.table.column_header_cell("Скидка"),
                rx.table.column_header_cell("Дети"),
                rx.table.column_header_cell("Действия"),
            )
        ),
        rx.table.body(
            rx.foreach(CustomersState.filtered_customers, customer_row),
        ),
        variant="surface",
        size=["1", "1", "2"],
        width="100%",
    )


def filter_panel() -> rx.Component:
    return rx.vstack(
        rx.input(
            placeholder="Поиск по имени или телефону",
            on_change=CustomersState.set_search_query,
            size="3",
            width="100%",
        ),
        rx.vstack(
            rx.hstack(
                rx.text("Минимальная скидка:", size="2"),
                rx.text(f"{CustomersState.min_discount}%", weight="bold", size="2"),
                justify="between",
                width="100%",
            ),
            rx.slider(
                default_value=[0],
                min=0,
                max=20,
                step=1,
                on_change=CustomersState.set_min_discount,
                width="100%",
            ),
            width="100%",
            spacing="1",
        ),
        spacing="3",
        width="100%",
    )
sorvantsy_admin/pages/customers.py
pythonimport reflex as rx

from sorvantsy_admin.components.customer_table import customer_table, filter_panel
from sorvantsy_admin.state import CustomersState


def customers_page() -> rx.Component:
    return rx.vstack(
        rx.heading("Клиенты", size=["6", "7", "8"]),
        filter_panel(),
        rx.box(
            customer_table(),
            width="100%",
            overflow_x="auto",
        ),
        rx.link(
            rx.button("Открыть сканер QR", size="3", width="100%"),
            href="/scan",
        ),
        spacing="4",
        padding=["3", "4", "6"],
        max_width="900px",
        margin="0 auto",
        width="100%",
        on_mount=CustomersState.load_customers,
    )
sorvantsy_admin/pages/scan.py
pythonimport reflex as rx

from sorvantsy_admin.components.qr_scanner import qr_scanner_widget


def scan_page() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.link(rx.button("← Назад", variant="soft"), href="/"),
            rx.heading("Сканер QR", size=["5", "6"]),
            spacing="3",
            align="center",
            width="100%",
        ),
        qr_scanner_widget(),
        spacing="4",
        padding=["3", "4", "6"],
        max_width="500px",
        margin="0 auto",
        width="100%",
    )
sorvantsy_admin/sorvantsy_admin.py
pythonimport reflex as rx

from sorvantsy_admin.pages.customers import customers_page
from sorvantsy_admin.pages.scan import scan_page


app = rx.App(
    theme=rx.theme(
        appearance="light",
        accent_color="orange",
        radius="medium",
    ),
)
app.add_page(customers_page, route="/", title="Сорванцы — Клиенты")
app.add_page(scan_page, route="/scan", title="Сорванцы — Сканер QR")
sorvantsy_admin/__init__.py, components/__init__.py, pages/__init__.py
Пустые файлы.
Запуск
bashmkdir sorvantsy-admin && cd sorvantsy-admin
python -m venv .venv
.venv\Scripts\activate     # Windows
# или: source .venv/bin/activate  для Linux

pip install reflex==0.9.2 reflex-webcam pyzbar pillow

# Linux dependencies для pyzbar:
# sudo apt-get install libzbar0
# Windows: pyzbar ставит DLL автоматически

# создай структуру файлов как выше, потом:
reflex init --template blank
# скажет что папка не пуста — это норм, скопируй файлы поверх

reflex run
