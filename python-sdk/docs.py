# Run this file to create the docs
import os

from pydoc_markdown import PydocMarkdown
from pydoc_markdown.contrib.loaders.python import PythonLoader
from pydoc_markdown.contrib.processors.crossref import CrossrefProcessor
from pydoc_markdown.contrib.processors.filter import FilterProcessor
from pydoc_markdown.contrib.processors.smart import SmartProcessor
from pydoc_markdown.contrib.renderers.markdown import MarkdownRenderer
from pydoc_markdown.interfaces import Loader


def create_loaders(search_path: str, filelist: list[str]) -> list[Loader]:
    ignorelist = [filename.replace(".py", "") for filename in os.listdir(search_path)]
    loaders = []
    for file in filelist:
        loader_ws_account_list = ignorelist.copy()
        loader_ws_account_list.remove(file)
        loader = PythonLoader(
            search_path=[search_path],
            ignore_when_discovered=loader_ws_account_list,
        )
        loaders.append(loader)
    return loaders


loaders = create_loaders(
    "hibachi_xyz", ["api", "api_ws_account", "api_ws_trade", "api_ws_market"]
)

processors = [
    FilterProcessor(skip_empty_modules=True),
    CrossrefProcessor(),
    SmartProcessor(),
]

renderer = MarkdownRenderer(
    render_module_header=False,
    # filename="./api.md",
    render_toc=True,
)

config = PydocMarkdown(
    loaders=loaders,
    processors=processors,
    renderer=renderer,
)

modules = config.load_modules()
config.process(modules)
output = renderer.render_to_string(modules)

# readfile
header = open("doc_header.md", "r").read()
footer = open("doc_footer.md", "r").read()

with open("../README.md", "w") as f:
    f.write(header + output + footer)
