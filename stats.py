"""Analysis of the data"""

import logging
import pickle
from datetime import timedelta

import dash
import dash_core_components as dcc
import dash_html_components as html
import emoji
import numpy as np
import pandas as pd
import plotly.graph_objs as go
from dash.dependencies import Input, Output

import db
import utilities

LOGGER = logging.getLogger(__name__)

EMOJI_SET = set(emoji.UNICODE_EMOJI)

LOGGER.debug("Unpickling configuration")
CONFIG = pickle.load(open(".config.pkl", "rb"))
CONVS = utilities.conversation_mapping(CONFIG)

APP = dash.Dash("signal-statistics")
# APP.config["suppress_callback_exceptions"] = True
APP.layout = html.Div(
    [
        # Header
        html.Div(
            [
                html.Span("Signal Conversation Statistics", className="title"),
                html.Div(
                    [
                        dcc.Dropdown(
                            id="conversation",
                            options=sorted(
                                [
                                    {"label": v, "value": k.decode("UTF-8")}
                                    for k, v in CONVS.items()
                                ],
                                key=lambda o: o["label"],
                            ),
                        )
                    ],
                    className="conversation-selector",
                ),
            ],
            className="header",
        ),
        # Content
        html.Div(
            [
                # Timeline
                html.Div(
                    [
                        html.H2("Conversation Timeline"),
                        dcc.Tabs(
                            [
                                dcc.Tab(label="Messages", value="messages"),
                                dcc.Tab(label="Words", value="words"),
                                dcc.Tab(label="Characters", value="characters"),
                            ],
                            id="timeline-value",
                            value="messages",
                        ),
                        dcc.Loading(dcc.Graph(id="timeline-figure")),
                    ],
                    className="timeline",
                ),
            ],
            className="content",
        ),
    ]
)


def split_messages(messages, conversation):
    """Select those messages which belong to the selected conversation and split
    them into incoming and outgoing messages."""
    if conversation:
        messages = messages[messages["conversation_id"] == conversation.encode("UTF-8")]

    return (messages.query("type == 'incoming'"), messages.query("type == 'outgoing'"))


@APP.callback(
    Output("timeline-figure", "figure"),
    [Input("timeline-value", "value"), Input("conversation", "value")],
)
def timeline(value, conversation):
    """Create a timeline of the timeline showing how much activity there was on
    each day."""

    messages = db.fetch_messages(CONFIG, as_dataframe=True)
    messages["messages"] = messages["body"].apply(lambda x: 1 if x else 0)
    messages["words"] = messages["body"].apply(lambda x: len(x.split()) if x else 0)
    messages["characters"] = messages["body"].apply(lambda x: len(x) if x else 0)

    incoming, outgoing = split_messages(messages, conversation)

    hist_options = {"xbins": {"size": "1D"}, "histfunc": "sum", "opacity": 0.5}
    layout = {
        "xaxis": {
            "name": "Date",
            "type": "date",
            "rangeselector": {
                "buttons": [
                    {
                        "label": "1m",
                        "count": 1,
                        "step": "month",
                        "stepmode": "backward",
                    },
                    {
                        "label": "6m",
                        "count": 6,
                        "step": "month",
                        "stepmode": "backward",
                    },
                    {"step": "all"},
                ]
            },
            "rangeslider": {"visible": True},
        },
        "barmode": "overlay",
    }

    data = [
        go.Histogram(
            x=incoming["sent_at"], y=incoming[value], name="Received", **hist_options
        ),
        go.Histogram(
            x=outgoing["sent_at"], y=outgoing[value], name="Sent", **hist_options
        ),
    ]

    if incoming.size < outgoing.size:
        data.reverse()

    return dict(data=data, layout=layout)


def main():
    """Start the plot.ly server"""
    LOGGER.info("Starting plot.ly server")

    APP.run_server(debug=True)
