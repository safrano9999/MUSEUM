-- PostgreSQL schema for ROUTINE
-- Equivalent to telegram_bot_dump.sql (MariaDB/MySQL)

-- ── Tables ────────────────────────────────────────────────────────────────────

DROP TABLE IF EXISTS routine_log;
DROP TABLE IF EXISTS routine_items;

CREATE TABLE routine_items (
    id    SERIAL PRIMARY KEY,
    label VARCHAR(100) NOT NULL
);

CREATE TABLE routine_log (
    id           SERIAL PRIMARY KEY,
    session_date DATE        NOT NULL,
    item_id      INTEGER     NOT NULL,
    checked_at   TIMESTAMP   DEFAULT NULL,
    note         VARCHAR(255) DEFAULT NULL,
    CONSTRAINT uq_session_item UNIQUE (session_date, item_id),
    CONSTRAINT fk_item FOREIGN KEY (item_id) REFERENCES routine_items (id)
);

-- ── Sample data ───────────────────────────────────────────────────────────────

INSERT INTO routine_items (id, label) VALUES
(1,  'Task 1'),
(2,  'Task 2'),
(3,  'Task 3'),
(4,  'Task 4'),
(5,  'Task 5'),
(6,  'Task 6'),
(7,  'Task 7'),
(8,  'Task 8'),
(9,  'Task 9'),
(10, 'Task 10'),
(11, 'Task 11'),
(12, 'Task 12'),
(13, 'Task 13'),
(14, 'Task 14'),
(15, 'Task 15');

-- Keep sequence in sync after explicit id inserts
SELECT setval('routine_items_id_seq', (SELECT MAX(id) FROM routine_items));

-- ── Daily reset (optional) ────────────────────────────────────────────────────
-- The bot initialises today's entries lazily on first /routine call,
-- so the job below is not strictly required.
--
-- If you want pre-population at midnight anyway, install pg_cron:
--   shared_preload_libraries = 'pg_cron'   (postgresql.conf)
--   CREATE EXTENSION pg_cron;
--
-- Then schedule:
--   SELECT cron.schedule(
--       'routine_daily_reset',
--       '0 0 * * *',
--       $$INSERT INTO routine_log (session_date, item_id)
--         SELECT CURRENT_DATE, id FROM routine_items
--         ON CONFLICT DO NOTHING$$
--   );
