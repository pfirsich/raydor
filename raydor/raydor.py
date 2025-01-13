import argparse
import glob
import os
import json
import re
import shutil
import sys
from datetime import datetime
from urllib.parse import urlparse
import email.utils
from xml.sax.saxutils import escape as xml_escape_filter

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape
import yaml

md_extensions = [
    "smarty",
]

md_ext_config = {
    "smarty": {"substitutions": {}},
}


def markdown_filter(text):
    return markdown.markdown(
        text, extensions=md_extensions, extension_configs=md_ext_config
    )

def make_dt(arg):
    if isinstance(arg, str):
        arg = datetime.fromisoformat(arg).astimezone() # `date -Iminutes`
    return arg

def datetime_filter(arg, fmt):
    return make_dt(arg).strftime(fmt)


# delim = " " to limit words, "." to limit sentences
def limit_filter(text: str, delim, n):
    pos = 0
    for i in range(n):
        pos = text.find(delim, pos) + 1
        if pos == 0:
            return text
    return text[0:pos] + " ..."

def url_hostname_filter(text: str):
    url = urlparse(text)
    return url.hostname

def to_id_filter(text: str):
    text = text.lower().replace(" ", "-")
    return re.sub("r[^a-zA-Z0-9-_:.]+", '', text)

def rfc822_filter(arg):
    return email.utils.format_datetime(make_dt(arg))

def to_json_filter(text: str):
    return json.dumps(text)

def now_tz_global():
    return datetime.now().astimezone()

def make_dirs(file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)


def load_json(path):
    with open(path) as f:
        return json.load(f)


def load_yaml(path):
    with open(path) as f:
        return yaml.load(f, Loader=yaml.FullLoader)


def load_markdown(path):
    with open(path) as f:
        file = f.read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", file, re.DOTALL)
    data = yaml.load(m.group(1), Loader=yaml.FullLoader)
    data["content"] = markdown.markdown(
        m.group(2), extensions=md_extensions, extension_configs=md_ext_config
    )
    data["filename"] = os.path.basename(path)
    return data


def load(path):
    if path.endswith(".json"):
        return load_json(path)
    elif path.endswith(".yaml") or path.endswith(".yml"):
        return load_yaml(path)
    elif path.endswith(".md"):
        return load_markdown(path)
    else:
        return f"Cannot load '{path}'"


def load_constructor(loader, node):
    return load(loader.construct_scalar(node))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o", default="output")
    parser.add_argument("config")
    args = parser.parse_args()

    yaml.add_constructor("!load", load_constructor)

    with open(args.config) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    md_ext_config["smarty"]["substitutions"].update(
        config.get("markdown_substitutions", {})
    )

    if "codehighlight" in config:
        md_extensions.append("codehilite")
        md_extensions.append("fenced_code")
        if "style" in config["codehighlight"]:
            md_ext_config["codehilite"] = {
                "pygments_style": config["codehighlight"]["style"],
                "css_class": "codehighlight",
                "noclasses": True,
            }

    template_global_vars = config.get("globals", {})

    env = Environment(loader=FileSystemLoader("."), autoescape=select_autoescape())
    env.globals["now_tz"] = now_tz_global
    env.filters["markdown"] = markdown_filter
    env.filters["datetime"] = datetime_filter
    env.filters["limit"] = limit_filter
    env.filters["url_hostname"] = url_hostname_filter
    env.filters["to_id"] = to_id_filter
    env.filters["rfc822"] = rfc822_filter
    env.filters["to_json"] = to_json_filter
    env.filters["xml_escape"] = xml_escape_filter

    if os.path.isdir(args.output):
        shutil.rmtree(args.output)
    os.makedirs(args.output, exist_ok=True)

    for output_name, file in config["files"].items():
        print(output_name)
        output_path = os.path.join(args.output, output_name)

        if isinstance(file, str):
            if os.path.isdir(file):
                shutil.copytree(file, output_path, dirs_exist_ok=True)
            elif os.path.isfile(file):
                make_dirs(output_path)
                shutil.copy2(file, output_path)
            else:
                sys.exit(f"Source '{file}' does not exist")
        elif isinstance(file, dict):
            if "generator" in file:
                file_matches = glob.glob(file["generator"].replace("%", "*"))
                for file_match in file_matches:
                    re_match = re.match(
                        file["generator"].replace("%", "(.*)"), file_match
                    )
                    gen_output_name = output_name.replace("%", re_match.group(1))
                    print("-", gen_output_name)
                    output_path = os.path.join(args.output, gen_output_name)
                    template_vars = load(file_match)
                    template_vars.update(template_global_vars)
                    make_dirs(output_path)
                    with open(output_path, "w") as f:
                        f.write(
                            env.get_template(file["template"]).render(template_vars)
                        )
            else:
                template_vars = file.get("vars", {})
                template_vars.update(template_global_vars)
                make_dirs(output_path)
                with open(output_path, "w") as f:
                    f.write(env.get_template(file["template"]).render(template_vars))
        else:
            sys.exit("Invalid 'files' element type")


if __name__ == "__main__":
    main()
