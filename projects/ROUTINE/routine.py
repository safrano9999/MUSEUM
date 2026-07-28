"""
routine plugin — daily routine checklist with inline keyboard
Supports MySQL/MariaDB (default) and PostgreSQL via DB_DRIVER env variable.
"""

import os
import logging
from datetime import date

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logger = logging.getLogger("routine")

DB_DRIVER    = os.getenv("DB_DRIVER", "mysql")
DB_HOST      = os.getenv("DB_HOST", "127.0.0.1")
_default_port = "5432" if DB_DRIVER == "pgsql" else "3306"
DB_PORT      = int(os.getenv("DB_PORT", _default_port))
DB_NAME      = os.getenv("DB_NAME", "telegram_bot")
DB_USER      = os.getenv("DB_USER", "botuser")
DB_PASS      = os.getenv("DB_PASS", "")

TOTAL_ITEMS = 15


def _db():
    if DB_DRIVER == "pgsql":
        import psycopg2
        return psycopg2.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, password=DB_PASS,
            dbname=DB_NAME,
        )
    else:
        import mysql.connector
        return mysql.connector.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, password=DB_PASS,
            database=DB_NAME,
        )


def today() -> str:
    return date.today().isoformat()


def init_session():
    conn = _db()
    cur  = conn.cursor()
    d    = today()
    for i in range(1, TOTAL_ITEMS + 1):
        if DB_DRIVER == "pgsql":
            cur.execute(
                "INSERT INTO routine_log (session_date, item_id) VALUES (%s, %s)"
                " ON CONFLICT DO NOTHING",
                (d, i),
            )
        else:
            cur.execute(
                "INSERT IGNORE INTO routine_log (session_date, item_id) VALUES (%s, %s)",
                (d, i),
            )
    conn.commit()
    cur.close()
    conn.close()


def build_keyboard() -> InlineKeyboardMarkup:
    conn = _db()
    cur  = conn.cursor()
    if DB_DRIVER == "pgsql":
        cur.execute(
            """
            SELECT ri.id, ri.label,
                   CASE WHEN rl.checked_at IS NOT NULL THEN 1 ELSE 0 END AS checked
            FROM routine_items ri
            JOIN routine_log rl ON ri.id = rl.item_id AND rl.session_date = %s
            ORDER BY ri.id
            """,
            (today(),),
        )
    else:
        cur.execute(
            """
            SELECT ri.id, ri.label,
                   IF(rl.checked_at IS NOT NULL, 1, 0) AS checked
            FROM routine_items ri
            JOIN routine_log rl ON ri.id = rl.item_id AND rl.session_date = %s
            ORDER BY ri.id
            """,
            (today(),),
        )
    rows    = cur.fetchall()
    cur.close()
    conn.close()

    buttons = []
    row     = []
    for item_id, label, checked in rows:
        icon = "✅" if checked else "☐"
        row.append(InlineKeyboardButton(
            f"{icon} {label}",
            callback_data=f"routine_toggle:{item_id}",
        ))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    return InlineKeyboardMarkup(buttons)


def done_count() -> int:
    conn = _db()
    cur  = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM routine_log WHERE session_date = %s AND checked_at IS NOT NULL",
        (today(),),
    )
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count


def toggle_item(item_id: int):
    conn = _db()
    cur  = conn.cursor()
    if DB_DRIVER == "pgsql":
        cur.execute(
            "SELECT CASE WHEN checked_at IS NOT NULL THEN 1 ELSE 0 END"
            " FROM routine_log WHERE session_date = %s AND item_id = %s",
            (today(), item_id),
        )
    else:
        cur.execute(
            "SELECT IF(checked_at IS NOT NULL, 1, 0) FROM routine_log"
            " WHERE session_date = %s AND item_id = %s",
            (today(), item_id),
        )
    row = cur.fetchone()
    if row:
        if row[0]:
            cur.execute(
                "UPDATE routine_log SET checked_at = NULL"
                " WHERE session_date = %s AND item_id = %s",
                (today(), item_id),
            )
        else:
            cur.execute(
                "UPDATE routine_log SET checked_at = NOW()"
                " WHERE session_date = %s AND item_id = %s",
                (today(), item_id),
            )
    conn.commit()
    cur.close()
    conn.close()


# ── Handlers ───────────────────────────────────────────────────────────────────

async def routine_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        init_session()
        keyboard = build_keyboard()
        count    = done_count()
        await update.message.reply_text(
            f"📋 Tagesroutine — {count}/{TOTAL_ITEMS} erledigt",
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.error(f"routine_cmd: {e}")
        await update.message.reply_text(f"❌ DB error: {e}")


async def toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        item_id = int(query.data.split(":")[1])
        init_session()
        toggle_item(item_id)
        keyboard = build_keyboard()
        count    = done_count()
        await query.edit_message_text(
            f"📋 Tagesroutine — {count}/{TOTAL_ITEMS} erledigt",
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.error(f"toggle_callback: {e}")
        await query.edit_message_text(f"❌ DB error: {e}")


# ── Plugin entry point ─────────────────────────────────────────────────────────

def register(app: Application):
    app.add_handler(CommandHandler("routine",  routine_cmd))
    app.add_handler(CallbackQueryHandler(toggle_callback, pattern=r"^routine_toggle:"))
