"""
Renderer class
"""

import yaml
import markdown
import bs4
import re
import importlib
import os
import requests
import tempfile
import traceback
import sys


from urllib.parse import urlparse
from PIL import Image, ImageSequence

from .utils import *

MD_EXT = [
    'nl2br',
    'toc',
    'footnotes',
    'meta',
    # 'fenced_code',
    'codehilite',
    'admonition',
    'pymdownx.inlinehilite',
    'pymdownx.superfences',
    'pymdownx.blocks.tab'
]
MD_EXT_CONF = {
    'footnotes': {
        'UNIQUE_IDS': True
    }
}

class Renderer():

    def __init__(self, engine, path, **page_context):
        """
        Renderer constructor.

        **Parameters**

        engine: Engine instance
        path: path to template file
        **page_context: keyword arguments to include in the excecution context for embed python code blocks
        """

        self.engine = engine
        self.path = path

        self.markdown = markdown.Markdown(output_format='html5', extensions=MD_EXT, extension_configs=MD_EXT_CONF)

        self.exec_context = deep_merge(
            self.engine.exec_context,
            page_context,
            {
                'toc': '',
                'include': lambda *a, **k: self.include(*a, **k),
                'get': lambda *a, **k: self.get(*a, **k),
                'get_meta': lambda *a: self.get_meta(*a),
                'image_cache': lambda *a, **k: self.image_cache(*a, **k),
            }
        )
        self.globals = {}
        self.locals = {}

        self.exec_context = deep_merge(self.exec_context, {
        }, update=True)


        self.pending_include = []

        self.prerendering = True
        self.prerender()
        self.prerendering = False



    def render(self, prettify=False):
        """
        Generate html document from source template.
        """

        html = self.include(self.path, **self.exec_context)

        if prettify:
            dom = bs4.BeautifulSoup(html, 'html.parser')
            html = str(dom)

        return html

    def prerender(self):
        """
        Prerender page to compute table of content, meta informations...
        """
        html = self.render()


        """
        Generate table of content from pre-rendered html.
        Takes the first encountered header (starting with h2) as base level.
        """
        toc = ''
        dom = bs4.BeautifulSoup(html, 'html.parser')
        headers = dom.find_all(re.compile('^h[1-6]$'))
        if headers:

            toc += '<ul>'
            length = len(headers)
            sublevel_opened = 1
            for i in range(length):

                h = headers[i]

                link = '<a href="#%s">%s</a>'  % (h.attrs.get('id'), h.text)
                level = int(h.name[1])
                if level == 1:
                    level = 2

                next = level - 1
                if i < length - 1:
                    next = int(headers[i+1].name[1])

                if next > level:
                    toc += '<li>%s<ul>' % link
                    sublevel_opened += 1
                elif next < level:
                    toc += '<li>%s</li></ul>' % link
                    sublevel_opened -= 1
                    if i < length - 1:
                        toc += '</li>'
                else:
                    toc += '<li>%s</li>' % link

            toc += '</ul>' * sublevel_opened

        """
        Extract meta from markdown headers
        """
        meta = {}
        for k in self.markdown.Meta:
            meta[k] = '\n'.join(self.markdown.Meta[k])

        if 'template' in meta:
            self.path = meta['template']

        """
        Insert toc and meta in exec context for final render
        """
        self.exec_context = deep_merge(self.exec_context, {
            'meta': meta,
            'toc': toc
        }, update=True)

    def resolve_code_blocks(self, content_string, **context):
        """
        Search for python code block patterns and replace them with their result.

        {%%
        # multiline python script
        # stdout output will be captured
        %%}

        {%
        # singleline python script, returned value will be captured
        %}

        **Parameters**

        content_string: string
        **context: keyword arguments to include in the excecution context for embed python code blocks

        **Returns**

        A string
        """
        self.globals = deep_merge(self.exec_context, context)
        locals = deep_merge(self.locals)

        if 'functions.py' in self.engine.sources:
            exec(self.engine.sources['functions.py' ], self.globals, None)

        def exec_repl(m):

            def _print(*args):
                _print._output += '\n'.join([str(a).strip() for a in args]) + '\n'
            _print._output = ''
            command = m.group(1)
            if command[0] == '\n' and command[1] == ' ':
                command = 'if True:\n' + command # indent fixer
            try:
                exec(command, deep_merge(self.globals, {'print': _print}), locals)
            except Exception as e:
                if not self.prerendering:
                    self.error(e, command)
            return _print._output

        content_string = re.sub(r'{%%(.*?)%%}\n?', exec_repl, content_string, flags=re.DOTALL)

        def eval_repl(m):
            command = m.group(1)
            try:
                content = eval(command.strip(), self.globals, locals)
                content = str(content)
                return content
            except Exception as e:
                if not self.prerendering:
                    self.error(e, command.strip())


        content_string = re.sub(r'{%([^%].*?)%}', eval_repl, content_string, flags=re.DOTALL)

        # purge locals to avoid variable leak
        self.locals = {}

        return content_string

    def include(self, path, parse_yaml=True, **context):
        """
        Compile resource and return it.

        **Parameters**

        path: path to resource
        **context: keyword arguments to include in the excecution context for embed python code blocks

        **Returns**

        A dict if requested resource is a YAML file, string otherwise.
        """
        if path == None:
            content = fallback_template
        elif path not in self.engine.sources:
            return 'ERROR: %s not found' % path
        else:
            content = self.engine.sources[path]

        self.pending_include.append(path)
        content = self.resolve_code_blocks(content, **context)
        self.pending_include.pop(-1)

        if path != None and '.yml' in path and parse_yaml:
            content = yaml.safe_load(content)
        if path == None or '.md' in path:
            content = self.markdown.convert(content)
            # reset parser to prevent duplicated footnotes
            # while keeping metadatas...
            meta = self.markdown.Meta
            self.markdown.reset()
            self.markdown.Meta = meta

        return content

    def get_meta(self, path):
        """
        Get meta data of markdown resource
        """
        if path in self.engine.sources and '.md' in path:
            self.markdown.convert(self.engine.sources[path])
            # reset parser to prevent duplicated footnotes
            # while keeping metadatas...
            meta = {}
            for k in self.markdown.Meta:
                meta[k] = '\n'.join(self.markdown.Meta[k])
            # self.markdown.reset()
            self.markdown.Meta = meta
            return meta
        else:
            return {}

    def error(self, exception, code):

        exc_type, exc_value, exc_traceback = sys.exc_info()
        frame = traceback.extract_tb(exc_traceback)[-1]
        offendingcode = code.split('\n')[frame.lineno - 1]

        if not len(self.pending_include):
            print(f'\nError during compilation of {self.path} at line {frame.lineno}:')
        else:
            print(f'\nError during compilation of {self.pending_include[-1]} (template; {self.path}) at line {frame.lineno}:')

        print(f'>    {offendingcode}')
        print(f'{str(exception.__class__.__name__)}: {exception}\n')

    def get(self, name, default=''):
        """
        Get variable by name from global context with a fallback default value

        **Parameters**

        name: variable name
        default: fallback value if variable is not defined in execution context

        **Returns**

        Variable or fallback value.
        """
        return self.globals[name] if name in self.globals else default


    def image_cache(self, path, resize=200, quality=70):

        distant_src = 'http://' in path or 'https://' in path

        if not distant_src and not path in self.engine.paths:
            return 'ERROR: %s not found' % path

        width = resize

        cache_path = self.engine.cache_path + '/'

        if distant_src:
            url = urlparse(path)
            cache_path += url.hostname + '-'
            cache_path += url.path.rpartition('/')[2]
        else:
            cache_path += path.partition('.')[0].replace('/', '_')

        gif = False
        cache_path += '-R'
        cache_path += 'auto' if width == None else str(resize)

        if path.rpartition('.')[-1] == 'gif':
            cache_path += '.gif'
            gif = True
        else:
            cache_path += '.jpg'

        if not os.path.exists(cache_path):

            if distant_src:
                print('Downloading distant image: %s' % path)
                tmp = tempfile.TemporaryFile()
                req = requests.get(path, allow_redirects=True)
                tmp.write(req.content)
                src_img = Image.open(tmp)
                src_img.load()
                tmp.close()
            else:
                src_img = Image.open(self.engine.paths[path])

            aspect_ratio = src_img.height / src_img.width
            height = int(resize * aspect_ratio)

            print('Caching resized (%sx%s) image: %s' % (resize, height, cache_path))
            if not gif:
                resized_image = src_img.convert('RGB')
                resized_image = resized_image.resize((resize, height), Image.LANCZOS)
                resized_image.save(cache_path, optimize=True,quality=quality)
            else:
                # https://gist.github.com/brvoisin/1ece9083b661bb67bb9d235546b1960a
                def _thumbnail_frames(image):
                    for frame in ImageSequence.Iterator(image):
                        new_frame = frame.copy()
                        new_frame.thumbnail((resize, height), Image.Resampling.LANCZOS)
                        yield new_frame
                frames = list(_thumbnail_frames(src_img))
                resized_image = frames[0]
                resized_image.save(
                    cache_path,
                    save_all=True,
                    append_images=frames[1:],
                    disposal=src_img.disposal_method,
                    **src_img.info,
                )


        return_path = cache_path.replace(self.engine.build_path, '')
        if return_path[0] == '/':
            return_path = return_path[1:]

        return return_path
