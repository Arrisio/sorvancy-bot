-- Покупатели
CREATE TABLE IF NOT EXISTS customers (
    id               SERIAL PRIMARY KEY,
    max_user_id      BIGINT UNIQUE NOT NULL,
    max_username     VARCHAR(255),
    first_name       VARCHAR(255),
    last_name        VARCHAR(255),
    phone            VARCHAR(20),
    discount_percent INT NOT NULL DEFAULT 10,
    registered_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Дети покупателей
CREATE TABLE IF NOT EXISTS children (
    id            SERIAL PRIMARY KEY,
    customer_id   INT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    name          VARCHAR(255) NOT NULL,
    gender        VARCHAR(10) NOT NULL CHECK (gender IN ('male', 'female')),
    birthdate     DATE NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE customers ADD COLUMN IF NOT EXISTS birthdate DATE;

-- Индексы для рассылок
CREATE INDEX IF NOT EXISTS idx_children_birthdate ON children (
    EXTRACT(MONTH FROM birthdate),
    EXTRACT(DAY FROM birthdate)
);
CREATE INDEX IF NOT EXISTS idx_children_gender ON children (gender);
