"""
CLI arguments parsing
"""

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from sys import argv
from . import __version__

parser = ArgumentParser(prog='python3 -m marxdown', formatter_class=ArgumentDefaultsHelpFormatter)

parser.add_argument('--src', help='site sources directory', default='./src')
parser.add_argument('--out', help='site build output directory', default='./build')
parser.add_argument('--watch',  help='watch for changes in sources and rebuild automatically', default=False, action='store_true')
parser.add_argument('--version', action='version', version=__version__)

config = parser.parse_args()
