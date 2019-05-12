import logging
from pathlib import Path

import click

import db
import utilities

LOGGER = logging.getLogger(__name__)


@click.command(__name__.replace("_", "-"))
@click.option(
    "-f",
    "--format",
    type=click.Choice(["csv", "sql", "json"]),
    default="csv",
    help="Set the output format.",
)
@click.option(
    "-o",
    "--output-dir",
    default="./export/",
    type=click.Path(file_okay=False),
    help="Set the export directory.",
)
@click.option(
    "--attachments/--no-attachments",
    "export_attachments",
    default=False,
    help="Toggle whether attachments are exported as well.",
)
@click.pass_context
def main(ctx, fmt, output_dir, export_attachments):
    """Export all conversations.
    """
    LOGGER.info("Export all conversations into '{output_dir}'.")

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    if fmt == "sql":
        db.dump_messages(ctx.obj["config"], output_dir)
        return

    messages = db.fetch_messages(ctx.obj["config"], as_dataframe=True)

    for col in messages.columns:
        LOGGER.debug(f"Column '{col}' type: {messages[col].dtype}")

    conv_map = utilities.conversation_mapping(ctx.obj["config"])

    for c_id, c_name in conv_map.items():
        LOGGER.info(f"Exporting conversation '{c_name}'")
        conv_dir = output_dir / c_name
        conv_dir.mkdir(exist_ok=True)
        if fmt == "csv":
            messages[messages["conversation_id"] == c_id].to_csv(
                conv_dir / "messages.csv", index=False
            )
        elif fmt == "json":
            messages[messages["conversation_id"] == c_id].to_json(
                conv_dir / "messages.json", orient="records"
            )

    if export_attachments:
        utilities.export_attachments(ctx.obj["config"], messages)
