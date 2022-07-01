import argparse
import glob
import os
import json
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape
from ruamel.yaml import YAML

yaml = YAML()


@dataclass
class Templated:
    template: str
    data: str | dict


@dataclass
class Copy:
    source: str


files = {
    "index.html": Templated("templates/index.html", {}),
    "projects.html": Templated(
        "templates/projects.html", {"projects": "src/projects.json"}
    ),
    "blog.html": Templated(
        "templates/blog.html", {"posts": "src/blog/*.md"}
    ),  # FIGURE OUT SORTING
    "blog/test.html": Templated("templates/blogpost.html", "src/blog/test.md"),
    "blog/test2.html": Templated("templates/blogpost.html", "src/blog/test2.md"),
    "images/": Copy("images/"),
}

extension_configs = {
    "smarty": {
        "substitutions": {
            "'": "&#8217;",
            "...": "&#8230;",
        },
    },
}


def markdown_filter(text):
    return markdown.markdown(
        text, extensions=["smarty"], extension_configs=extension_configs
    )


def datetime_filter(arg, fmt):
    if isinstance(arg, str):
        arg = datetime.fromisoformat(arg)  # `date -Iminutes`
    return arg.strftime(fmt)


# delim = " " to limit words, "." to limit sentences
def limit_filter(text: str, delim, n):
    pos = 0
    for i in range(n):
        pos = text.find(delim, pos) + 1
        if pos == 0:
            return text
    return text[0:pos] + " ..."


def make_dirs(file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)


def load_json(path):
    with open(path) as f:
        return json.load(f)


def load_markdown(path):
    with open(path) as f:
        file = f.read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", file, re.DOTALL)
    data = yaml.load(m.group(1))
    data["content"] = markdown.markdown(
        m.group(2), extensions=["smarty"], extension_configs=extension_configs
    )
    data["filename"] = os.path.basename(path)
    return data


def expand_template_data(data):
    loaders = {".json": load_json, ".md": load_markdown}

    if isinstance(data, dict):
        return {k: expand_template_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [expand_template_data(e) for e in data]
    elif isinstance(data, str):
        loader = loaders.get(os.path.splitext(data)[1])
        if loader:
            if "*" in data:
                return [loader(match) for match in glob.glob(data)]
            else:
                return loader(data)
        return data
    else:
        return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o", default="output")
    args = parser.parse_args()

    env = Environment(loader=FileSystemLoader("."), autoescape=select_autoescape())
    env.filters["markdown"] = markdown_filter
    env.filters["datetime"] = datetime_filter
    env.filters["limit"] = limit_filter

    if os.path.isdir(args.output):
        shutil.rmtree(args.output)
    os.makedirs(args.output, exist_ok=True)

    for rel_output_path, file in files.items():
        sys.stdout.write(rel_output_path + ".. ")
        output_path = os.path.join(args.output, rel_output_path)
        if isinstance(file, Templated):
            data = expand_template_data(file.data)
            make_dirs(output_path)
            with open(output_path, "w") as f:
                f.write(env.get_template(file.template).render(data))
        elif isinstance(file, Copy):
            if os.path.isdir(file.source):
                shutil.copytree(file.source, output_path, dirs_exist_ok=True)
            else:
                make_dirs(output_path)
                shutil.copy2(file.source, output_path)
        else:
            sys.exit("Invalid item class")
        sys.stdout.write("done\n")


if __name__ == "__main__":
    main()
