"""List conversations command"""

import base64
import logging

import click
from termcolor import colored

import db

LOGGER = logging.getLogger(__name__)


@click.command(__name__.replace("_", "-"))
@click.option(
    "--show-id/--hide-id",
    "show_id",
    default=False,
    help=(
        "Toggle the display conversation ID. For group conversation, the ID is"
        "base64 encoded."
    ),
)
@click.option(
    "--show-message-count/--hide-message-count",
    "show_message_count",
    default=True,
    help="Toggle the display of message counts.",
)
@click.pass_context
def main(ctx, show_id, show_message_count):
    """List all the conversations in Signal.
    """
    LOGGER.debug("Listing all conversations in the database.")

    count = 0

    if show_message_count:
        messages = db.fetch_messages(ctx.obj["config"])

    print(colored("Private conversations:", "white", attrs=["bold"]))
    conversations = db.fetch_conversations(ctx.obj["config"], conv_type="private")
    for conv in conversations:
        count += 1

        output = []
        output.append(colored("->", "blue"))
        if show_id:
            output.append(colored(conv["id"].decode("utf-8"), "green"))
        output.append(
            colored(conv["name"] if conv["name"] else conv["profile_name"], "white")
        )
        if show_message_count:
            count = len([c for c in messages if c["conversation_id"] == conv["id"]])
            output.append(colored(f"[{count} messages]"))

        print(" ".join(output))

    print("")
    print(colored("Group conversations:", "white", attrs=["bold"]))
    conversations = db.fetch_conversations(ctx.obj["config"], conv_type="group")
    for conv in conversations:
        count += 1

        output = []
        output.append(colored("->", "blue"))
        if show_id:
            output.append(
                colored(base64.b64encode(conv["id"]).decode("utf-8"), "green")
            )
        output.append(
            colored(conv["name"] if conv["name"] else conv["profile_name"], "white")
        )
        output.append(f"({len(conv['members'])} members)")
        if show_message_count:
            count = len([c for c in messages if c["conversation_id"] == conv["id"]])
            output.append(colored(f"[{count} messages]"))

        print(" ".join(output))

    print("")
    print(colored(f"{count} conversations in total.", "green"))
