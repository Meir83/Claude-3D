"""Main Gradio tab — image upload, style selector, per-style params, generate, preview."""

from typing import Any

import gradio as gr

from img2print.core import registry
from img2print.styles.base import StyleParam
from img2print.ui.params import build_param_components, collect_params
from img2print.ui.preview import get_preview_path


def build_main_tab() -> gr.Blocks:
    styles = registry.list_styles()
    style_names = [s["name"] for s in styles]
    style_display = {s["name"]: s["display_name"] for s in styles}
    style_desc = {s["name"]: s["description"] for s in styles}
    display_names = [style_display[n] for n in style_names]

    # Pre-build param components for every style.
    # Order matters: we'll pass them all to generate() and slice by style.
    _style_params: dict[str, list[StyleParam]] = {}
    _style_groups: dict[str, gr.Group] = {}
    _style_components: dict[str, list[gr.components.Component]] = {}

    with gr.Blocks(title="img2print — Image to 3D Print") as demo:
        gr.Markdown(
            "# img2print\n"
            "Convert any 2D image into a 3D-printable model. "
            "Upload an image, choose a style, tune the parameters, then click **Generate**."
        )

        with gr.Row():
            # Left column: image + style selector.
            with gr.Column(scale=1, min_width=280):
                image_input = gr.Image(
                    label="Upload Image",
                    type="filepath",
                    sources=["upload", "clipboard"],
                    height=260,
                )
                style_dropdown = gr.Dropdown(
                    choices=display_names,
                    value=display_names[0] if display_names else None,
                    label="Style",
                )
                style_description = gr.Markdown(
                    f"*{style_desc[style_names[0]]}*" if style_names else ""
                )

            # Right column: per-style parameter groups.
            with gr.Column(scale=2):
                for i, name in enumerate(style_names):
                    style_cls = registry.get(name)
                    sparams = style_cls.params()
                    _style_params[name] = sparams
                    with gr.Group(visible=(i == 0)) as grp:
                        gr.Markdown(f"### {style_display[name]} Parameters")
                        comps = build_param_components(sparams)
                    _style_groups[name] = grp
                    _style_components[name] = comps

        with gr.Row():
            generate_btn = gr.Button("⚡ Generate", variant="primary", scale=2)
            status_text = gr.Textbox(
                label="Status", value="Upload an image and click Generate.", interactive=False, scale=3
            )

        with gr.Row():
            with gr.Column():
                preview_3d = gr.Model3D(label="3D Preview", height=380)
            with gr.Column():
                download_stl = gr.File(label="Download STL")
                stats_json = gr.JSON(label="Mesh Stats")
                warnings_text = gr.Textbox(
                    label="Warnings", interactive=False, lines=3, visible=False
                )

        # --- Flat list of all param components (preserves insertion order). ---
        all_components: list[gr.components.Component] = []
        for name in style_names:
            all_components.extend(_style_components[name])

        # ---- Event: style dropdown change ----
        def on_style_change(display_name: str) -> list[Any]:
            name = _display_to_name(display_name, style_display)
            desc = f"*{style_desc.get(name, '')}*" if name else ""

            # One visibility update per group, in style_names order.
            group_updates = [
                gr.update(visible=(sname == name)) for sname in style_names
            ]
            return [desc] + group_updates

        style_dropdown.change(
            fn=on_style_change,
            inputs=[style_dropdown],
            outputs=[style_description] + [_style_groups[n] for n in style_names],
        )

        # ---- Event: generate button ----
        def on_generate(
            image_path: str | None,
            display_name: str,
            *all_param_values: Any,
        ) -> tuple[Any, Any, str, dict, Any, Any]:
            if image_path is None:
                return None, None, "Please upload an image first.", {}, gr.update(visible=False)

            name = _display_to_name(display_name, style_display)
            if not name:
                return None, None, "Unknown style selected.", {}, gr.update(visible=False)

            # Extract this style's param values from the flat list.
            idx = style_names.index(name)
            offset = sum(len(_style_params[sname]) for sname in style_names[:idx])
            n_params = len(_style_params[name])
            raw_values = list(all_param_values)[offset : offset + n_params]
            params_dict = collect_params(_style_params[name], raw_values)

            try:
                from img2print.core.pipeline import run

                result = run(image_path, name, params_dict)
                preview = get_preview_path(result.preview_path)
                has_warnings = bool(result.warnings)
                warn_text = "\n".join(result.warnings)
                return (
                    preview,
                    result.mesh_path,
                    f"Done! {result.stats.get('triangle_count', '?'):,} triangles.",
                    result.stats,
                    gr.update(visible=has_warnings, value=warn_text),
                )
            except NotImplementedError as e:
                return None, None, f"Not yet implemented: {e}", {}, gr.update(visible=False)
            except Exception as e:
                return None, None, f"Error: {e}", {}, gr.update(visible=False)

        generate_btn.click(
            fn=on_generate,
            inputs=[image_input, style_dropdown] + all_components,
            outputs=[preview_3d, download_stl, status_text, stats_json, warnings_text],
        )

    return demo


def _display_to_name(display_name: str, display_map: dict[str, str]) -> str:
    for name, disp in display_map.items():
        if disp == display_name:
            return name
    return ""
