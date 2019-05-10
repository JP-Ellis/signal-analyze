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
MESSAGES = db.fetch_messages(CONFIG, as_dataframe=True)
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
                html.Div(
                    [
                        dcc.Tabs(
                            [
                                dcc.Tab(label="Messages per Day", value="messages"),
                                dcc.Tab(label="Words per Day", value="words"),
                                dcc.Tab(label="Characters per Day", value="characters"),
                            ],
                            id="day-histogram-value",
                            value="messages",
                        ),
                        dcc.Loading(dcc.Graph(id="day-histogram-figure")),
                    ],
                    className="day-histogram",
                )
            ],
            className="content",
        ),
    ]
)


def split_messages(conversation, messages=None):
    """Select those messages which belong to the selected conversation and split
    them into incoming and outgoing messages."""
    if not messages:
        messages = MESSAGES.copy()

    if conversation:
        messages = messages[messages["conversation_id"] == conversation.encode("UTF-8")]

    return (messages.query("type == 'incoming'"), messages.query("type == 'outgoing'"))


@APP.callback(
    Output("day-histogram-figure", "figure"),
    [Input("day-histogram-value", "value"), Input("conversation", "value")],
)
def day_histogram(value, conversation):
    """Create a histogram binning messages per day"""

    incoming, outgoing = split_messages(conversation)

    incoming["messages"] = incoming["body"].apply(lambda x: 1 if x else 0)
    incoming["words"] = incoming["body"].apply(lambda x: len(x.split()) if x else 0)
    incoming["characters"] = incoming["body"].apply(lambda x: len(x) if x else 0)
    outgoing["messages"] = outgoing["body"].apply(lambda x: 1 if x else 0)
    outgoing["words"] = outgoing["body"].apply(lambda x: len(x.split()) if x else 0)
    outgoing["characters"] = outgoing["body"].apply(lambda x: len(x) if x else 0)

    hist_options = {"xbins": {"size": "1D"}, "histfunc": "sum", "opacity": 0.5}

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

    return dict(data=data, layout=layout)


def main():
    LOGGER.info("Starting plot.ly server")

    APP.run_server(debug=True)
