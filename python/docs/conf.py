import os
import sys

# Add the project root (one level up from docs/) to sys.path
sys.path.insert(0, os.path.abspath(".."))

from hibachi_xyz import get_version

# -- Project information -----------------------------------------------------

project = "hibachi_xyz"
copyright = "2025, Hibachi Engineering Team"
author = "Hibachi Engineering Team"

release = get_version()
if "unknown" in release:
    raise RuntimeError(f"Unknown version {release=}")

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = False

# Suppress warnings for duplicate cross-references (classes exported from multiple modules)
suppress_warnings = ["ref.python"]

## Templates
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

## Http
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# Rendering
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}


extensions.append("sphinx.ext.linkcode")


def linkcode_resolve(domain: str, info: dict[str, str]) -> str | None:
    if domain != "py" or not info["module"]:
        return None
    filename = (
        info["module"]
        .replace(".", "/")
        .replace("hibachi_xyz/", "python-sdk/hibachi_xyz/")
    )
    return f"https://github.com/hibachi-xyz/yule-os/tree/v{release}/{filename}.py"
