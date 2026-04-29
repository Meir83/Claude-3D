"""Gradio entry point. Run with: uv run img2print"""

import gradio as gr

from img2print.ui.main_tab import build_main_tab


def main() -> None:
    demo = build_main_tab()
    demo.queue(
        # bpy is NOT thread-safe; force single-worker for Blender operations.
        max_size=10,
    ).launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
    )


if __name__ == "__main__":
    main()
