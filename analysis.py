"""Analysis of the data"""

import logging
from datetime import timedelta

import dash
import dash_core_components as dcc
import dash_html_components as html
import emoji
import numpy as np
import pandas as pd
import plotly.graph_objs as go

# import plotly.plotly as py

STYLESHEETS = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

LOGGER = logging.getLogger(__name__)
APP = dash.Dash(__name__)
EMOJI_SET = set(emoji.UNICODE_EMOJI)


def main(messages, conv_map):
    """Main analysis entry point."""
    LOGGER.info("Analysing data")
    messages = process_messages(messages, conv_map)

    conv_map_inverse = {v: k for k, v in conv_map.items()}

    print(list(conv_map_inverse.keys()))

    APP.layout = html.Div(
        children=[
            html.H1(children="Signal Analytics"),
            histogram_messages_per_day(messages, conv_map),
            histogram_words_per_day(messages, conv_map),
            histogram_day_of_week(messages, conv_map),
            histogram_time_of_day(messages, conv_map),
            conversation_starter(messages, conv_map),
            emoji_use(messages, conv_map),
        ]
    )

    APP.run_server(debug=True)


def process_messages(messages, conv_map):
    """Processes the messages and perform so initial calculations on the bulk."""
    messages = messages.copy()
    messages["words"] = messages["body"].apply(lambda x: len(x.split()) if x else 0)
    messages["dayofweek"] = messages["sent_at"].apply(lambda t: t.weekday())
    messages["time"] = messages["sent_at"].apply(
        lambda t: t.hour + t.minute / 60 + t.second / 3600
    )
    messages["emoji"] = (
        messages["body"]
        .apply(lambda txt: txt if txt else "")
        .apply(lambda txt: [l for l in txt if l in EMOJI_SET])
    )

    return messages


def histogram_messages_per_day(messages, conv_map):
    """Create a histogram binning messages per day"""
    incoming = messages[messages["type"] == "incoming"]["sent_at"]
    outgoing = messages[messages["type"] == "outgoing"]["sent_at"]

    hist_options = {"xbins": {"size": "1D"}, "opacity": 0.5}

    data = [
        go.Histogram(x=incoming, name="Received", **hist_options),
        go.Histogram(x=outgoing, name="Sent", **hist_options),
    ]

    if incoming.size < outgoing.size:
        data.reverse()

    layout = {
        "title": "Messages per day",
        "xaxis": {
            "name": "Date",
            "type": "date",
            "rangeselector": {
                "buttons": [
                    [
                        {
                            "count": 1,
                            "label": "1m",
                            "step": "month",
                            "stepmode": "backward",
                        },
                        {
                            "count": 6,
                            "label": "6m",
                            "step": "month",
                            "stepmode": "backward",
                        },
                        {"step": "all"},
                    ]
                ]
            },
            "rangeslider": {"visible": True},
        },
        "barmode": "overlay",
    }

    figure = dict(data=data, layout=layout)
    return dcc.Graph(id="histogram-messages-per-day", figure=figure)


def histogram_words_per_day(messages, conv_map):
    """Create a histogram binning words per day."""
    incoming = messages[messages["type"] == "incoming"][["sent_at", "words"]]
    outgoing = messages[messages["type"] == "outgoing"][["sent_at", "words"]]

    hist_options = {"xbins": {"size": "1D"}, "histfunc": "sum", "opacity": 0.5}

    data = [
        go.Histogram(
            x=incoming["sent_at"], y=incoming["words"], name="Received", **hist_options
        ),
        go.Histogram(
            x=outgoing["sent_at"], y=outgoing["words"], name="Sent", **hist_options
        ),
    ]

    if incoming.size < outgoing.size:
        data.reverse()

    layout = {
        "title": "Words per day",
        "xaxis": {
            "name": "Date",
            "type": "date",
            "rangeselector": {
                "buttons": [
                    [
                        {
                            "count": 1,
                            "label": "1m",
                            "step": "month",
                            "stepmode": "backward",
                        },
                        {
                            "count": 6,
                            "label": "6m",
                            "step": "month",
                            "stepmode": "backward",
                        },
                        {"step": "all"},
                    ]
                ]
            },
            "rangeslider": {"visible": True},
        },
        "barmode": "overlay",
    }

    figure = dict(data=data, layout=layout)
    return dcc.Graph(id="histogram-words-per-day", figure=figure)


def histogram_time_of_day(messages, conv_map):
    """Create a histogram of messages per time of day."""
    incoming = messages[messages["type"] == "incoming"]["time"]
    outgoing = messages[messages["type"] == "outgoing"]["time"]

    hist_options = {"opacity": 0.5}

    data = [
        go.Histogram(x=incoming, name="Received", **hist_options),
        go.Histogram(x=outgoing, name="Sent", **hist_options),
    ]
    if incoming.size < outgoing.size:
        data.reverse()

    layout = {
        "title": "Messages per Time of Day",
        "xaxis": {"type": "time", "dtick": 1},
        "barmode": "overlay",
    }

    figure = dict(data=data, layout=layout)
    return dcc.Graph(id="histogram-time-of-day", figure=figure)


def histogram_day_of_week(messages, conv_map):
    """Create a histogram of messages per day of the week."""
    messages.sort_values(by="dayofweek", inplace=True)

    incoming = messages[messages["type"] == "incoming"]["dayofweek"]
    outgoing = messages[messages["type"] == "outgoing"]["dayofweek"]

    hist_options = {"histfunc": "count"}

    data = [
        go.Histogram(x=incoming, name="Received", **hist_options),
        go.Histogram(x=outgoing, name="Sent", **hist_options),
    ]

    if incoming.size < outgoing.size:
        data.reverse()

    layout = {
        "title": "Messages per day of the week",
        "xaxis": {
            "type": "category",
            "tickmode": "array",
            "tickvals": list(range(7)),
            "ticktext": [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ],
        },
        "bargap": 0.2,
        "bargroupgap": 0.0,
    }

    figure = dict(data=data, layout=layout)
    return dcc.Graph(id="histogram-day-of-week", figure=figure)


def conversation_starter(messages, conv_map, hours=1.5):
    """Create a pie chart of who starts conversations"""
    conversations = []
    conversation = [messages.iloc[0]]
    for _, msg in messages.iterrows():
        if msg["sent_at"] - conversation[-1]["sent_at"] < timedelta(
            seconds=hours * 3600
        ):
            conversation.append(msg)
        else:
            conversations.append(conversation)
            conversation = [msg]
    conversations.append(conversation)

    starter = (conv[0] for conv in conversations)
    starter = pd.Series(
        ["Other" if msg["type"] == "incoming" else "Me" for msg in starter]
    )
    starter = starter.value_counts()

    data = [go.Pie(labels=starter.index, values=starter.values)]

    figure = dict(data=data)
    return dcc.Graph(id="conversation-starter", figure=figure)


def emoji_use(messages, conv_map):
    """Create a histogram of emoji use"""
    incoming = messages[messages["type"] == "incoming"]["emoji"].sum()
    in_emojis, in_count = np.unique(incoming, return_counts=True)
    incoming = pd.Series(index=in_emojis, data=in_count)

    outgoing = messages[messages["type"] == "outgoing"]["emoji"].sum()
    out_emojis, out_count = np.unique(outgoing, return_counts=True)
    outgoing = pd.Series(index=out_emojis, data=out_count)

    data = pd.concat(
        {"incoming": incoming, "outgoing": outgoing}, axis=1, sort=False
    ).fillna(0)
    data["total"] = data["incoming"] + data["outgoing"]
    data.sort_values(by="total", inplace=True, ascending=False)

    hist_options = {}

    data = [
        go.Bar(x=data.index, y=data["incoming"], name="Received", **hist_options),
        go.Bar(x=data.index, y=data["outgoing"], name="Sent", **hist_options),
    ]

    layout = {"title": "Emojis Used", "bargap": 0.2, "bargroupgap": 0.0}

    figure = dict(data=data, layout=layout)
    return dcc.Graph(id="emoji-use", figure=figure)
