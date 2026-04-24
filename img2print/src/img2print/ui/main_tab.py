"""Main Gradio tab — image upload, style selector, dynamic params, generate, preview."""

from typing import Any

import gradio as gr

from img2print.core import registry
from img2print.ui.params import build_param_components, collect_params
from img2print.ui.preview import get_preview_path


def _style_choices() -> list[str]:
    return [s["name"] for s in registry.list_styles()]


def _style_display_map() -> dict[str, str]:
    return {s["name"]: s["display_name"] for s in registry.list_styles()}


def build_main_tab() -> gr.Blocks:
    style_names = _style_choices()
    display_map = _style_display_map()
    display_names = [display_map[n] for n in style_names]

    with gr.Blocks(title="img2print") as demo:
        gr.Markdown("# img2print\nConvert 2D images into 3D-printable models.")

        with gr.Row():
            with gr.Column(scale=1):
                image_input = gr.Image(
                    label="Upload Image",
                    type="filepath",
                    sources=["upload", "clipboard"],
                )
                style_dropdown = gr.Dropdown(
                    choices=display_names,
                    value=display_names[0] if display_names else None,
                    label="Style",
                )
                style_description = gr.Markdown("")

            with gr.Column(scale=2):
                params_group = gr.Group()
                with params_group:
                    param_components: list[gr.components.Component] = []

        with gr.Row():
            generate_btn = gr.Button("Generate", variant="primary")
            status_text = gr.Textbox(label="Status", interactive=False)

        with gr.Row():
            with gr.Column():
                preview_3d = gr.Model3D(label="3D Preview")
            with gr.Column():
                download_stl = gr.File(label="Download STL")
                stats_json = gr.JSON(label="Mesh Stats")
                warnings_text = gr.Textbox(label="Warnings", interactive=False)

        # --- callbacks ---

        def on_style_change(display_name: str) -> tuple[str, list[Any]]:
            name = _display_to_name(display_name, display_map)
            if name is None:
                return "", []
            style_cls = registry.get(name)
            desc = next(
                (s["description"] for s in registry.list_styles() if s["name"] == name), ""
            )
            params = style_cls.params()
            updates = [gr.update(value=p.default) for p in params]
            return f"*{desc}*", updates

        def on_generate(image_path: str | None, display_name: str, *param_values: Any) -> tuple:
            if image_path is None:
                return None, None, "Please upload an image.", {}, ""

            name = _display_to_name(display_name, display_map)
            if name is None:
                return None, None, "Unknown style.", {}, ""

            style_cls = registry.get(name)
            raw_params = collect_params(style_cls.params(), list(param_values))

            try:
                from img2print.core.pipeline import run

                result = run(image_path, name, raw_params)
                preview = get_preview_path(result.preview_path)
                warnings = "\n".join(result.warnings) if result.warnings else "None"
                return (
                    preview,
                    result.mesh_path,
                    "Done!",
                    result.stats,
                    warnings,
                )
            except NotImplementedError as e:
                return None, None, f"Not yet implemented: {e}", {}, ""
            except Exception as e:
                return None, None, f"Error: {e}", {}, ""

        # Wire up style change → update description + param defaults.
        # (Dynamic param rendering requires page reload in Gradio 4.x —
        #  params are rendered for all styles and shown/hidden via visibility.)
        style_dropdown.change(
            fn=on_style_change,
            inputs=[style_dropdown],
            outputs=[style_description],
        )

        generate_btn.click(
            fn=on_generate,
            inputs=[image_input, style_dropdown],
            outputs=[preview_3d, download_stl, status_text, stats_json, warnings_text],
        )

    return demo


def _display_to_name(display_name: str, display_map: dict[str, str]) -> str | None:
    for name, disp in display_map.items():
        if disp == display_name:
            return name
    return None
