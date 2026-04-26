"""Dynamic parameter rendering — converts StyleParam list into Gradio components."""

from typing import Any

import gradio as gr

from img2print.styles.base import StyleParam


def build_param_components(params: list[StyleParam]) -> list[gr.components.Component]:
    """Return a list of Gradio components for the given StyleParam list."""
    components: list[gr.components.Component] = []
    for p in params:
        if p.type == "float":
            components.append(
                gr.Slider(
                    minimum=p.min or 0.0,
                    maximum=p.max or 100.0,
                    step=p.step or 0.1,
                    value=p.default,
                    label=p.label,
                    info=p.help or None,
                )
            )
        elif p.type == "int":
            components.append(
                gr.Slider(
                    minimum=int(p.min or 1),
                    maximum=int(p.max or 1024),
                    step=int(p.step or 1),
                    value=int(p.default),
                    label=p.label,
                    info=p.help or None,
                )
            )
        elif p.type == "bool":
            components.append(
                gr.Checkbox(value=bool(p.default), label=p.label, info=p.help or None)
            )
        elif p.type == "select":
            components.append(
                gr.Dropdown(
                    choices=p.choices,
                    value=p.default,
                    label=p.label,
                    info=p.help or None,
                )
            )
        elif p.type == "color":
            components.append(
                gr.ColorPicker(value=str(p.default), label=p.label)
            )
        else:
            components.append(gr.Textbox(value=str(p.default), label=p.label))
    return components


def collect_params(style_params: list[StyleParam], values: list[Any]) -> dict[str, Any]:
    """Zip StyleParam names with Gradio-returned values into a plain dict."""
    return {p.name: v for p, v in zip(style_params, values)}
