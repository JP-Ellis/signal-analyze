"""Utilities to connect to the database"""

import json
import logging
import subprocess
from datetime import datetime

import pandas as pd
from pysqlcipher3 import dbapi2 as sqlite

import settings
import utilities

LOGGER = logging.getLogger(__name__)


def get_key(config):
    """Obtain the key from the Signal configuration."""
    with open(config["signal_dir"] / "config.json", "r") as f:
        key = json.load(f)["key"]
        LOGGER.debug(f"Key: 0x{key[:3]}...{key[-3:]}")
        # LOGGER.debug(f"Key: 0x{key}")
        return key


def fetch(config, cmd):
    """Connect to the Signal database and return a cursor."""
    conn = sqlite.connect(str(config["signal_dir"] / "sql" / "db.sqlite"))
    conn.row_factory = sqlite.Row
    LOGGER.debug(f"Connected to {config['signal_dir'] / 'sql' / 'db.sqlite'}")

    try:
        c = conn.cursor()

        c.execute(f"PRAGMA key=\"x'{get_key(config)}'\"")
        for setting, value in settings.SQLCIPHER_SETTINGS.items():
            c.execute(f"PRAGMA {setting}={value}")

        c.execute(cmd)
        rows = c.fetchall()
        LOGGER.debug(f"Fetched {len(rows)} rows")

        return rows
    finally:
        conn.close()


def fetch_conversations(config, conv_type=None):
    """Fetch all the conversations from the database.

    The `type` can be either `"private"` or `"group"` for private and group
    conversations.  If left as `None`, all conversations are returned.

    """
    if conv_type is None:
        type_selection = ""
    elif conv_type in ["private", "group"]:
        type_selection = f'WHERE type = "{type}"'
    else:
        raise ValueError(f"Unknown conversation type '{type}'")

    rows = fetch(
        config,
        f"""
        SELECT
            cast(id AS BLOB) id,
            name,
            profileName profile_name,
            members
        FROM conversations
        {type_selection}
        """,
    )
    return rows


def fetch_messages(config, with_attachments=None, as_dataframe=True):
    """Fetch all the messages from the database.

    If `with_attachments` is not None, then only those messages with
    attachments will be returned.

    If `as_dataframe` is True, the data will be loaded and processed into a
    Pandas DataFrame
    """
    cond = []
    if not config["include_expiring"]:
        cond.append("expires_at is null")
    if with_attachments is not None:
        cond.append("has_attachments = 1")
    rows = fetch(
        config,
        f"""
        SELECT
            id,
            cast(conversationId as BLOB) conversation_id,
            sent_at,
            received_at,
            source,
            hasAttachments has_attachments,
            type,
            body,
            json
        FROM messages
        WHERE {' and '.join(cond)}
        ORDER BY sent_at ASC""",
    )

    if not as_dataframe:
        return rows

    rows = pd.DataFrame(rows, columns=rows[0].keys(), dtype=object)

    rows["sent_at"] = rows["sent_at"].apply(lambda x: datetime.fromtimestamp(x / 1000))
    rows["received_at"] = rows["received_at"].apply(
        lambda x: datetime.fromtimestamp(x / 1000)
    )
    rows["has_attachments"] = rows["has_attachments"].apply(bool)
    rows["json"] = rows["json"].apply(utilities.parse_message_json)

    return rows


def dump_messages(config, output_dir):
    """Connect to the Signal database and return a cursor."""

    tables = [
        "conversations",
        "messages",
        "messages_fts",
        "messages_fts_config",
        "messages_fts_content",
        "messages_fts_data",
        "messages_fts_docsize",
        "messages_fts_idx",
    ]

    sql = f"PRAGMA key=\"x'{get_key(config)}'\";\n"
    for setting, value in settings.SQLCIPHER_SETTINGS.items():
        sql += f"PRAGMA {setting}={value};\n"
    sql += f".out {output_dir / 'messages.sql'};\n"
    sql += ".headers on;\n"
    sql += f".dump {' '.join(tables)};\n"
    print(sql)

    subprocess.run(["sqlite3", config["signal_dir"] / "sql" / "db.sqlite", sql])
