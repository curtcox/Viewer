# ruff: noqa: F821, F706
# This template executes inside the Viewer runtime where `request` and `context` are provided.
import json
import urllib.request

from jinja2 import Environment, FunctionLoader


def load_from_url(name):
    with urllib.request.urlopen(name) as r:
        return r.read().decode("utf-8")

env = Environment(loader=FunctionLoader(load_from_url))
template = request.get('form_data').get('template')
tpl = env.get_template(template)

values = request.get('form_data').get('values')
with urllib.request.urlopen(values) as r:
    data = json.loads(r.read().decode("utf-8"))

return {'output': tpl.render(data)}