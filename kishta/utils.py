"""
Utilities
"""

from copy import deepcopy
from functools import reduce
from collections import defaultdict
from inspect import ismodule

def deep_merge(*dicts, update=False):
    """
    https://gist.github.com/yatsu/68660bea18edfe7e023656c250661086
    Merges dicts deeply.
    Parameters
    ----------
    dicts : list[dict]
        List of dicts.
    update : bool
        Whether to update the first dict or create a new dict.
    Returns
    -------
    merged : dict
        Merged dict.
    """
    def merge_into(d1, d2):
        for key in d2:
            if key not in d1 or not isinstance(d1[key], dict):
                if not ismodule(d2[key]):
                    d1[key] = deepcopy(d2[key])
            else:
                d1[key] = merge_into(d1[key], d2[key])
        return d1

    if update:
        return reduce(merge_into, dicts[1:], dicts[0])
    else:
        return reduce(merge_into, dicts, {})

def defaultify(d):
    return d
    if not isinstance(d, dict):
        return d
    return defaultdict(lambda: None, {k: defaultify(v) for k, v in d.items()})

fallback_template = """
<nav>
    <ul>
{%%
pages = get('pages', False)
if not pages:
    print('"Error: pages not defined in config.yml"')
else:
    for page in pages:
        if '.' not in page:
            print(\"""
                <li><a href="%s.html">%s</a></li>
            \""" % (page, page))
%%}
    </ul>
</nav>

<main>
{% include(content) %}
</main>
"""
