# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
# This template executes inside the Viewer runtime where `request` and `context` are provided.
from html import escape


def dict_to_html_ul(data):
    if not isinstance(data, dict):
        raise TypeError("expects a dict at the top level")

    def render(d):
        items = d.items()
        lis = []
        for k, v in items:
            k_html = escape(str(k))
            if isinstance(v, dict):
                lis.append(f"<li>{k_html}{render(v)}</li>")
            else:
                v_html = "" if v is None else escape(str(v))
                lis.append(f"<li>{k_html}: {v_html}</li>")
        return "<ul>" + "".join(lis) + "</ul>"

    return render(data)

out = {
    'request': request,
    'context': context
}

html = '<html><body>' + dict_to_html_ul(out) + '</body></html>'

return {'output': html}
