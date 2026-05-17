-- Migration: add survey_completed, opt_out_marketing to customers
ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS survey_completed BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS opt_out_marketing BOOLEAN NOT NULL DEFAULT FALSE;

-- Migration: fix children.birthdate to nullable
ALTER TABLE children
    ALTER COLUMN birthdate DROP NOT NULL;

-- Migration: create staff table
CREATE TABLE IF NOT EXISTS staff (
    id SERIAL PRIMARY KEY,
    max_user_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    phone VARCHAR(20),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    is_owner BOOLEAN NOT NULL DEFAULT FALSE,
    customer_mode BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Migration: create coupons table
CREATE TABLE IF NOT EXISTS coupons (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    value INTEGER NOT NULL,
    max_payment_pct INTEGER NOT NULL,
    valid_until TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'active'
);

-- Migration: create broadcasts table
CREATE TABLE IF NOT EXISTS broadcasts (
    id SERIAL PRIMARY KEY,
    source_message_id BIGINT NOT NULL,
    source_chat_id BIGINT NOT NULL,
    created_by INTEGER REFERENCES staff(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    scheduled_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    recipient_count INTEGER NOT NULL,
    sent_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0
);

-- Migration: create broadcast_recipients table
CREATE TABLE IF NOT EXISTS broadcast_recipients (
    id SERIAL PRIMARY KEY,
    broadcast_id INTEGER NOT NULL REFERENCES broadcasts(id) ON DELETE CASCADE,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending',
    sent_at TIMESTAMPTZ,
    error TEXT,
    UNIQUE (broadcast_id, customer_id)
);

-- Seed: insert owner if OWNER_MAX_USER_ID is set (run manually with your owner's user_id)
-- INSERT INTO staff (max_user_id, is_owner) VALUES (<YOUR_MAX_USER_ID>, TRUE)
-- ON CONFLICT (max_user_id) DO NOTHING;
