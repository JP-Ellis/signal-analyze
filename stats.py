"""Analysis of the data"""

import logging
import pickle
import time
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
LAST_UPDATE = time.time()
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
                # Histogram
                html.Div(
                    [
                        html.H2("Histogram"),
                        html.Div(
                            [
                                dcc.Dropdown(
                                    id="histogram-reduction",
                                    options=[
                                        {
                                            "label": "Day of Week",
                                            "value": "day_of_week",
                                        },
                                        {
                                            "label": "Time of Day",
                                            "value": "time_of_day",
                                        },
                                    ],
                                    value="time_of_day",
                                    clearable=False,
                                ),
                                dcc.Dropdown(
                                    id="histogram-value",
                                    options=[
                                        {"label": "Messages", "value": "messages"},
                                        {"label": "Words", "value": "words"},
                                        {"label": "Characters", "value": "characters"},
                                    ],
                                    value="messages",
                                    clearable=False,
                                ),
                            ]
                        ),
                        dcc.Loading(dcc.Graph(id="histogram-figure")),
                    ],
                    className="histogram",
                ),
                # Emoji
                html.Div(
                    [
                        html.H2("Emoji Use"),
                        dcc.Loading(dcc.Graph(id="emoji-figure")),
                        dcc.Slider(
                            id="emoji-threshold",
                            min=0,
                            max=100,
                            step=5,
                            value=10,
                            dots=True,
                            marks={v: f"{v}" for v in range(0, 100 + 1, 10)},
                        ),
                    ],
                    className="emoji",
                ),
                # Conversation starter
                html.Div(
                    [
                        html.H2("Conversation starter"),
                        dcc.Loading(dcc.Graph(id="conversation-starter-figure")),
                        dcc.Slider(
                            id="conversation-starter-threshold",
                            min=0,
                            max=6,
                            step=0.5,
                            value=2,
                            dots=True,
                            marks={v: f"{v}h" for v in range(0, 6 + 1, 1)},
                        ),
                    ],
                    className="conversation-starter",
                ),
            ],
            className="content",
        ),
    ]
)


def load_messages():
    """Load the messages, possibly updating the global variable if needed."""
    global LAST_UPDATE
    global MESSAGES

    if MESSAGES is None or time.time() - LAST_UPDATE > 60:
        LOGGER.info("Updating messages...")
        LAST_UPDATE = time.time()
        MESSAGES = db.fetch_messages(CONFIG, as_dataframe=True)
    else:
        LOGGER.debug("Using pre-fetched messages.")

    return MESSAGES.copy()


def select_conversation(messages, conversation):
    """Select those messages which belong to the selected conversation."""
    if conversation:
        messages = messages[messages["conversation_id"] == conversation.encode("UTF-8")]

    return messages


def split_messages(messages, conversation):
    """Select those messages which belong to the selected conversation and split
    them into incoming and outgoing messages."""
    messages = select_conversation(messages, conversation)

    return (messages.query("type == 'incoming'"), messages.query("type == 'outgoing'"))


def filter_timeline(messages, timeline_data):
    """Filter messages selecting only those messages in the timeline's range."""
    if timeline_data is None:
        return messages

    if "xaxis.range" in timeline_data:
        start, end = timeline_data["xaxis.range"]
    elif "xaxis.range[0]" in timeline_data:
        start = timeline_data["xaxis.range[0]"]
        end = timeline_data["xaxis.range[1]"]
    else:
        return messages

    start = pd.to_datetime(start)
    end = pd.to_datetime(end)
    messages = messages[(start < messages["sent_at"]) & (messages["sent_at"] < end)]
    return messages


@APP.callback(
    Output("timeline-figure", "figure"),
    [Input("timeline-value", "value"), Input("conversation", "value")],
)
def timeline(value, conversation):
    """Create a timeline of the timeline showing how much activity there was on
    each day."""

    messages = load_messages()
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


@APP.callback(
    Output("histogram-figure", "figure"),
    [
        Input("histogram-value", "value"),
        Input("histogram-reduction", "value"),
        Input("conversation", "value"),
        Input("timeline-figure", "relayoutData"),
    ],
)
def histogram(value, reduction, conversation, timeline_data):
    """Create a histogram of the conversation, reducing the data as per the
    reduction."""

    messages = load_messages()
    messages = filter_timeline(messages, timeline_data)

    messages["messages"] = messages["body"].apply(lambda x: 1 if x else 0)
    messages["words"] = messages["body"].apply(lambda x: len(x.split()) if x else 0)
    messages["characters"] = messages["body"].apply(lambda x: len(x) if x else 0)
    messages["time_of_day"] = messages["sent_at"].apply(
        lambda t: t.hour + t.minute / 60 + t.second / 60 / 60
    )
    messages["day_of_week"] = messages["sent_at"].apply(lambda t: t.weekday())
    messages.sort_values(by=reduction, inplace=True)

    incoming, outgoing = split_messages(messages, conversation)

    hist_options = {"opacity": 0.5}
    layout = {"bargap": 0.2, "bargroupgap": 0.0}

    if reduction == "day_of_week":
        print(messages[value].unique())
        hist_options["nbinsx"] = 7
        # hist_options["xbins"] = {"size": 1}
        layout["xaxis"] = {
            "type": "category",
            "tickmode": "array",
            "tickvals": [0, 1, 2, 3, 4, 5, 6],
            "ticktext": [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ],
        }
    elif reduction == "time_of_day":
        hist_options["nbinsx"] = 24
        # hist_options["xbins"] = {"size": 1}
        layout["xaxis"] = {"tick0": 0, "dtick": 1}

    data = [
        go.Histogram(
            x=incoming[reduction], y=incoming[value], name="Received", **hist_options
        ),
        go.Histogram(
            x=outgoing[reduction], y=outgoing[value], name="Sent", **hist_options
        ),
    ]

    if incoming.size < outgoing.size:
        data.reverse()

    return dict(data=data, layout=layout)


@APP.callback(
    Output("emoji-figure", "figure"),
    [
        Input("emoji-threshold", "value"),
        Input("conversation", "value"),
        Input("timeline-figure", "relayoutData"),
    ],
)
def emoji_use(threshold, conversation, timeline_data):
    """Create a histogram of the conversation, reducing the data as per the
    reduction."""

    messages = load_messages()
    messages = filter_timeline(messages, timeline_data)

    messages["emoji"] = (
        messages["body"]
        .apply(lambda txt: txt if txt else "")
        .apply(lambda txt: [l for l in txt if l in EMOJI_SET])
    )

    incoming, outgoing = split_messages(messages, conversation)
    values, counts = np.unique(incoming["emoji"].sum(), return_counts=True)
    in_emojis = pd.Series(index=values, data=counts)
    values, counts = np.unique(outgoing["emoji"].sum(), return_counts=True)
    out_emojis = pd.Series(index=values, data=counts)

    data = pd.concat(
        {"incoming": in_emojis, "outgoing": out_emojis}, axis=1, sort=False
    ).fillna(0)
    data["total"] = data["incoming"] + data["outgoing"]
    data.sort_values(by="total", inplace=True, ascending=False)
    data = data.query(f"total >= {threshold}")

    hist_options = {"opacity": 0.5}
    layout = {"bargap": 0.2, "bargroupgap": 0.0}

    data = [
        go.Bar(x=data.index, y=data["incoming"], name="Received", **hist_options),
        go.Bar(x=data.index, y=data["outgoing"], name="Sent", **hist_options),
    ]

    if incoming.size < outgoing.size:
        data.reverse()

    return dict(data=data, layout=layout)


@APP.callback(
    Output("conversation-starter-figure", "figure"),
    [
        Input("conversation-starter-threshold", "value"),
        Input("conversation", "value"),
        Input("timeline-figure", "relayoutData"),
    ],
)
def conversation_starter(threshold, conversation, timeline_data):
    """Create a pie chart of who initiates conversations"""
    if conversation:
        conversation_label = CONVS[conversation.encode("UTF-8")]
    else:
        conversation_label = "Others"

    messages = load_messages()
    messages = filter_timeline(messages, timeline_data)
    messages = select_conversation(messages, conversation)

    threshold = timedelta(seconds=threshold * 3600)
    conversations = [
        {
            "starter": messages.iloc[0]["type"],
            "start": messages.iloc[0]["sent_at"],
            "last": messages.iloc[0]["sent_at"],
        }
    ]
    for _, msg in messages.iterrows():
        if msg["sent_at"] - conversations[-1]["last"] < threshold:
            conversations[-1]["last"] = msg["sent_at"]
        else:
            conversations.append(
                {
                    "starter": msg["type"],
                    "start": msg["sent_at"],
                    "last": msg["sent_at"],
                }
            )
    conversations = pd.DataFrame(conversations)
    conversations["length"] = conversations["last"] - conversations["start"]

    data = conversations["starter"].value_counts().to_frame()
    data.index = data.index.map({"outgoing": "Me", "incoming": conversation_label})
    data["msg_count"] = 0
    for idx in data.index:
        data.loc[idx, "msg_count"] = len(messages.query(f"type == '{idx}'").index)
    data.sort_values(by="msg_count", inplace=True)

    layout = {}

    data = [go.Pie(labels=data.index, values=data["starter"])]

    return dict(data=data, layout=layout)


def main(debug):
    """Start the plot.ly server"""
    LOGGER.info("Starting plot.ly server")

    APP.run_server(debug=debug)
