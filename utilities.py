"""Utility functions"""

import json
import logging
import os
import shutil
from datetime import datetime

import db

LOGGER = logging.getLogger(__name__)


def conversation_mapping(config):
    """Map the conversation ID to the name."""
    conversations = db.fetch_conversations(config)
    return {
        c["id"]: c["name"] if c["name"] else c["profile_name"] for c in conversations
    }


def parse_message_json(s):
    """Parse a message's JSON converting (as many) fields as possible into more
    useful types (such as integers to booleans, and integers to datetime
    objects.)
    """
    js = json.loads(s)

    js["received_at"] = datetime.fromtimestamp(js["received_at"] / 1000)
    js["sent_at"] = datetime.fromtimestamp(js["sent_at"] / 1000)
    js["timestamp"] = datetime.fromtimestamp(js["timestamp"] / 1000)
    if "decrypted_at" in js:
        js["decrypted_at"] = datetime.fromtimestamp(js["decrypted_at"] / 1000)
    if "expirationStartTimestamp" in js and js["expirationStartTimestamp"] is not None:
        js["expirationStartTimestamp"] = datetime.fromtimestamp(
            js["expirationStartTimestamp"] / 1000
        )

    js["hasAttachments"] = bool(js["hasAttachments"])
    if "hasVisualMediaAttachments" in js:
        js["hasVisualMediaAttachments"] = bool(js["hasVisualMediaAttachments"])

    return js


def export_attachments(config, messages):
    """Export the attachments associated with all the messages."""
    LOGGER.info("Exporting all attachments.")
    conv_map = conversation_mapping(config)
    messages = messages[messages["has_attachments"]]

    for _, msg in messages.iterrows():
        js = msg["json"]
        for attachment in js["attachments"]:
            if "path" not in attachment:
                LOGGER.warn(f"{msg['id']}: Attachment does not specified a path")
                continue

            ext = attachment["contentType"].lower().split("/")[-1]
            attachment_id = attachment["path"].split("/")[-1]
            name = "{}.{}.{}".format(
                msg["sent_at"].strftime("%Y-%m-%d-%H:%M:%S"), attachment_id[:8], ext
            )

            src = config["signal_dir"] / "attachments.noindex" / attachment["path"]
            dst = (
                config["output_dir"] / conv_map[msg["conversation_id"]] / "files" / name
            )
            if not src.is_file():
                LOGGER.warning(f"Skipping {src} (file does not exist)")
                return

            if dst.is_file():
                LOGGER.debug(f"Skipping {dst} (destination exists)")
                return

            dst.parent.mkdir(exist_ok=True)
            shutil.copy(src, dst)
            os.utime(
                dst, times=(msg["sent_at"].timestamp(), msg["sent_at"].timestamp())
            )
