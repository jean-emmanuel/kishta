"""
Engine class
"""

import os
import yaml
import importlib
import glob

from .utils import *
from .renderer import Renderer

class Engine():

    def __init__(self, src_path, build_path):
        """
        Engine constructor. Reads all source files and builds html files for pages listed in site configuration.

        **Parameters**

        src_path: path to source directory
        build_path: path to build directory
        """

        self.src_path = src_path + '/'
        self.build_path = build_path + '/'

        self.cache_path = build_path + '/cache'
        os.makedirs(self.cache_path, exist_ok=True)


        self.paths = {}
        self.sources = {}
        self.walk(self.src_path)

        self.exec_context = {
            'compiled_pages': {},
            'navigation': []
        }
        self.config = {}
        self.init_exec_context()


        # resolve pages in config.yml
        pages = []
        if 'pages' in self.config:

            template = None
            if 'meta' in self.config and 'template' in self.config['meta']:
                template = self.config['meta']['template']

            for page in self.config['pages']:

                content_path = self.config['pages'][page]


                if '*' in content_path:

                    for p in glob.glob(self.src_path + content_path):

                        os.makedirs(self.build_path + page, exist_ok=True)
                        content_path = p.replace(self.src_path, '')
                        out_path = self.build_path + page + '/' + os.path.basename(p).partition('.')[0]

                        if '.md' in content_path :
                            out_path += '.html'

                        pages.append([page, template, content_path, out_path])
                        self.exec_context['compiled_pages'][content_path] = out_path

                else:
                    out_path = self.build_path + page
                    if '.md' in content_path :
                        out_path += '.html'
                    pages.append([page, template, content_path, out_path])
                    self.exec_context['compiled_pages'][content_path] = out_path


            for page in pages:
                self.render(*page)

    def walk(self, path):
        """
        Read files in folder recursively and store their content
        """

        for (root, dirs, files) in os.walk(path):

            for f in dirs:
                self.walk(f)

            for f in files:

                p = root + '/' + f
                name = p.replace(self.src_path, '')

                if root == self.src_path:
                    # strip leading slash
                    name = name[1:]

                self.paths[name] = p
                if name.rpartition('.')[2] in ['html', 'md', 'css', 'js', 'json', 'yml', 'py', 'txt', 'htaccess']:
                    with open(p) as file:
                        self.sources[name] = file.read()



    def init_exec_context(self):
        """
        Populate template excecution context with data found in source files.
        """

        # load user config
        if 'config.yml' in self.sources:
            self.config = yaml.safe_load(self.sources['config.yml'])
            deep_merge(self.exec_context, self.config, update=True)
        else:
            print(f'ERROR: config.yml not found in {self.src_path}')

    def render(self, name, template, content_path, out_path):
        if '.md' in content_path:
            renderer = Renderer(self, template, current_page=name, content=content_path)
        else:
            renderer = Renderer(self, content_path, current_page=name, content=content_path)

        result = renderer.render(prettify=True)

        with open(out_path, 'w+') as file:
            file.write(result)
