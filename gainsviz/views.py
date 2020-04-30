from gainsviz import app
import gainsviz.models as models

import itertools
import uuid
import numpy as np
from pathlib import Path

from flask import (render_template, request, send_from_directory, session, 
        url_for, redirect, jsonify, flash)
import pandas as pd
from bokeh.plotting import figure, curdoc, output_file, show
from bokeh.layouts import column
from bokeh.models import Select, Row, ColumnDataSource
from bokeh.models.widgets import Panel, Tabs
from bokeh.models.tools import HoverTool 
from bokeh.transform import factor_cmap
from bokeh.embed import components
import bokeh.palettes


PLT_HEIGHT = 250
PLT_WIDTH = 900

PRIMARY_COLOR_LIGHT = "#f38869"
SECONDARY_COLOR = "#41b3a3"

MIME_TYPES = ("text/csv", "text/comma-separated-values")


def style_fig(fig):
    fig.background_fill_color = "#EAEAF1"
    fig.grid.grid_line_color = "white"
    fig.grid.grid_line_width = 2
    # fig.xaxis.ticker.desired_num_ticks = 8
    fig.yaxis.ticker.desired_num_ticks = 3
    fig.axis.axis_line_color = "white"
    fig.axis.major_tick_line_color = "white"
    fig.axis.minor_tick_line_color = "white"
    # fig.border_fill_color = SECONDARY_COLOR
    # fig.axis.major_label_text_color = "white"
    # fig.title.text_color = "white"
    # fig.toolbar.autohide = True

    # Remove Bokeh help tool
    fig.toolbar.tools.pop(-1)
    fig.sizing_mode = "scale_both"

    return fig



@app.route("/")
def index():
    return render_template("index.html", title="gains::viz")


@app.route("/about")
def about():
    return render_template("about.html", title="gains::viz")


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if request.method == "POST":
        f = request.files["file"]
        unit = request.form["unit"]
        try:
            cutoff = float(request.form["cutoff"])/100
        except Exception as e:
            print(e)
            cutoff = -1

        if cutoff < 0 or cutoff > 1:
            flash(f"Invalid cutoff percentage", "danger")
            return redirect(url_for("index"))

        if not f:
            flash("No file selected", "danger")
            return redirect(url_for("index"))
        if (mimetype := f.mimetype) not in MIME_TYPES:
            flash(f"Invalid file format {mimetype}", "danger")
            return redirect(url_for("index"))

        df = pd.read_csv(f, sep=";")
        df.loc[:, "Date"] = pd.to_datetime(df["Date"]).dt.date

        df.loc[df["Weight Unit"] != unit, "Weight"] \
                = df.loc[df["Weight Unit"] != unit, :].apply(
                        lambda x: models.weight_conversion[unit](x["Weight"]), 
                        axis=1)
        df["Weight"].fillna(1, inplace=True)
        df["Weight"].replace(0, 1, inplace=True)

        unique_exercises = list(df["Exercise Name"].value_counts().index)

        tabs = []
        exercises = unique_exercises
        for ex in exercises:
            df_ex = df.loc[df["Exercise Name"] == ex].copy()

            
            # Calculate estimated 1 RM of set
            df_ex.loc[:, "Est. 1 RM"] = df_ex.apply(
                    lambda x: models.get_1rm(x["Weight"], x["Reps"]), axis=1)

            df_ex["Workout 1 RM"] = df_ex.groupby(
                    "Date")["Est. 1 RM"].transform("max")

            # Calculate total volume of set
            # df_ex.loc[:, "Set Volume"] = df_ex["Weight"]*df_ex["Reps"]
            df_ex.loc[:, "Set Volume"] = df_ex.apply(
                    lambda x: models.get_volume(
                        x["Weight"], x["Reps"], x["Workout 1 RM"], cutoff=cutoff), 
                    axis=1)

            # Group all exercises by date performed on
            d = df_ex.groupby("Date")[["Set Volume", "Est. 1 RM"]].agg(
                    {
                        "Set Volume": "sum", 
                        "Est. 1 RM": ["max", "idxmax"]
                    })
            d.columns = d.columns.droplevel()
            d.dropna(inplace=True)

            # Get Reps/Weight of the maximal 1 RM value of each date
            d.loc[:, "Reps"] = df_ex.loc[d["idxmax"], "Reps"].values
            d.loc[:, "Weight"] = df_ex.loc[d["idxmax"], "Weight"].values

            d.index = pd.to_datetime(d.index)
            d.rename(
                    columns={"max": "Est. 1 RM", "sum": "Total Daily Volume"}, 
                    inplace=True)
            d2 = d.resample("D").asfreq(0)
            d2.drop(columns="idxmax", inplace=True)
            
            # Group all workouts by week (starting on Monday)
            d3 = d2.resample("W-MON").agg(
                    {
                        "Total Daily Volume": "sum", 
                        "Est. 1 RM": ["max", "idxmax"]
                    })
            d3.columns = d3.columns.droplevel()
            d3.fillna(0, inplace=True)


            # Get Reps/Weight/Workout Date of the maximal 1 RM value of week
            d3.loc[:, "Reps"] = d2.loc[d3["idxmax"], "Reps"].values
            d3.loc[:, "Weight"] = d2.loc[d3["idxmax"], "Weight"].values
            d3.loc[:, "Workout Date"] = d3["idxmax"].dt.strftime("%d %B %Y")

            d3.drop(columns="idxmax", inplace=True)
            d3.rename(
                    columns={"max": "Est. 1 RM", "sum": "Total Weekly Volume"}, 
                    inplace=True)
            d3.loc[d3["Total Weekly Volume"] == 0, "Total Weekly Volume"] = None
            d3.loc[d3["Est. 1 RM"] == 0, "Est. 1 RM"] = None

            source = ColumnDataSource(d3)

            hover = HoverTool()
            hover.tooltips=[
                ("Reps", "@Reps"),
                ("Weight", "@Weight"),
                ("Est. 1 RM", "@{Est. 1 RM}"),
                ("Date", "@{Workout Date}"),
            ]
            
            fig1 = figure(
                    title="Total Weekly Volume",
                    y_axis_label=f"Weight [{unit}]",
                    width=PLT_WIDTH, 
                    height=PLT_HEIGHT,
                    x_axis_type="datetime")
            fig1.circle(
                    x="Date", y="Total Weekly Volume",
                    source=source,
                    color=SECONDARY_COLOR,
                    size=5)

            fig1 = style_fig(fig1)

            fig2 = figure(
                    title="Est. 1 RM",
                    y_axis_label=f"Weight [{unit}]",
                    width=PLT_WIDTH, 
                    height=PLT_HEIGHT,
                    x_axis_type="datetime")
            fig2.circle(
                    x="Date", y="Est. 1 RM",
                    source=source,
                    color=PRIMARY_COLOR_LIGHT,
                    size=5)
            fig2 = style_fig(fig2)
            fig2.add_tools(hover)

            tab = Panel(child=column(fig1, fig2), title=ex)
            tabs.append(tab)

        div, script = components(Tabs(tabs=tabs))
        
        return render_template("dashboard.html", 
                title="gains::viz",
                div=div, 
                script=script) 
