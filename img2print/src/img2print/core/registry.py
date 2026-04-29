"""Auto-discovers and registers all StyleBase subclasses from styles/."""

import importlib
import pkgutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from img2print.styles.base import StyleBase

_registry: dict[str, type["StyleBase"]] = {}


def _discover() -> None:
    if _registry:
        return
    styles_pkg = Path(__file__).parent.parent / "styles"
    for module_info in pkgutil.iter_modules([str(styles_pkg)]):
        if module_info.name == "base":
            continue
        importlib.import_module(f"img2print.styles.{module_info.name}")

    from img2print.styles.base import StyleBase

    for cls in StyleBase.__subclasses__():
        if hasattr(cls, "name") and cls.name:
            _registry[cls.name] = cls


def list_styles() -> list[dict]:
    _discover()
    return [
        {"name": cls.name, "display_name": cls.display_name, "description": cls.description}
        for cls in _registry.values()
    ]


def get(name: str) -> type["StyleBase"]:
    _discover()
    if name not in _registry:
        available = list(_registry.keys())
        raise KeyError(f"Style '{name}' not found. Available: {available}")
    return _registry[name]
