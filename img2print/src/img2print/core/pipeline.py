"""Main orchestrator: load → preprocess → dispatch → validate → return."""

import os
import tempfile
from typing import Any

from img2print.core import registry
from img2print.core.image_io import load_and_validate, preprocess
from img2print.core.mesh_validator import validate
from img2print.styles.base import StyleResult


def run(
    image_path: str,
    style_name: str,
    params: dict[str, Any],
    output_dir: str | None = None,
) -> StyleResult:
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="img2print_")

    os.makedirs(output_dir, exist_ok=True)

    image = load_and_validate(image_path)
    image = preprocess(image, target_max_dim=2048)

    style_cls = registry.get(style_name)
    style = style_cls()

    result = style.generate(image, params, output_dir)

    if result.mesh_path and os.path.exists(result.mesh_path):
        validation = validate(result.mesh_path, attempt_repair=True)
        result.warnings.extend(validation.warnings)
        result.stats.update(validation.stats)
        if validation.repaired:
            result.stats["repaired"] = True

    return result
