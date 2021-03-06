from math import ceil

LBS_IN_KG = 2.2046226218


def lbs_to_kg(weight: float):
    return weight*LBS_IN_KG


def kg_to_lbs(weight: float):
    return weight/LBS_IN_KG


weight_conversion = {
        "lbs": lbs_to_kg,
        "kg": kg_to_lbs
        }

quantity_conversion = {
        "few": lambda x: min(8, x),
        "medium": lambda x: ceil(0.25*x),
        "many": lambda x: ceil(0.5*x),
        "all": lambda x: None
        }


def color_gen(num_colors=3):
    yield from itertools.cycle(bokeh.palettes.Colorblind[num_colors])


def calculate_1rm_epley(w: float, r: int):
    """Calculates estimated 1 RM using the Epley formula

    weight w for r reps.
    """

    if r == 1:
        return w
    if r == 0:
        return 0

    if w == 0:
        w = 1

    return round(w*(1 + r/30), 2)



def calculate_1rm_brzycki(w: float, r: int):
    """Calculates estimated 1 RM using the Epley formula

    weight w for r reps.
    """

    if r == 0:
        return 0

    if w == 0:
        w = 1

    return round(w*36/(37 - r), 2)

def get_1rm(w: float, r: int):
    if r < 8:
        return calculate_1rm_brzycki(w, r)
    elif r > 10:
        return calculate_1rm_epley(w, r)
    elif r == 8:
        return 0.25*calculate_1rm_epley(w, r) + 0.75*calculate_1rm_brzycki(w, r)
    elif r == 9:
        return 0.5*calculate_1rm_epley(w, r) + 0.5*calculate_1rm_brzycki(w, r)
    elif r == 10:
        return 0.75*calculate_1rm_epley(w, r) + 0.25*calculate_1rm_brzycki(w, r)


def get_volume(w: float, r: int, w_max: float, cutoff: float = 0.):
    if w == 0:
        w = 1

    set_max = get_1rm(w, r)
    if set_max < cutoff*w_max:
        return 0

    return w*r


def style_fig(fig):
    fig.background_fill_color = "#EAEAF1"
    fig.grid.grid_line_color = "white"
    fig.grid.grid_line_width = 2
    fig.xaxis.ticker.desired_num_ticks = 8
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
    # Turn of pan/drag by default
    fig.toolbar.active_drag = None
    fig.sizing_mode = "scale_both"

    return fig
