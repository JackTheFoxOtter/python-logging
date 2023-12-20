from setuptools import setup, find_namespace_packages
from typing import Union, List

# Load metadata from _metadata.py
__title__ : str
__description__ : str
__author__ : str
__license__ : str
__url__ : str
__version__ : str
with open('source/jtfo/logging/_metadata.py') as f:
    exec(f.read())

# Load README.md
with open('README.md') as f:
    readme = f.read()

# Parse requirements.txt
install_requires = []
extras_require = {}
context_skip : bool = False
context_extras : Union[None, List[str]] = None
with open('requirements.txt') as f:
    for line in f:
        line = line.strip()
        if line.startswith('#!'):
            # Marks beginning of requirements ignored for build
            context_skip = True
            context_extras = None
        
        elif line.startswith('#?'):
            # Marks beginning of requirements for specific extras
            context_skip = False
            context_extras = eval(line[2:])
            extra : str
            for extra in context_extras:
                extras_require.setdefault(extra, [])
        
        elif context_skip or line.startswith('#') or not line:
            # Skip ignored requirements, comments and empty lines
            continue
        
        elif context_extras:
            # Requirements for one or multiple extras
            extra : str
            for extra in context_extras:
                extras_require[extra] += [ line ]
        
        else:
            # Requirements for base package
            install_requires += [ line ]

setup(
    name=__title__,
    description=__description__,
    author=__author__,
    license=__license__,
    url=__url__,
    version=__version__,
    long_description=readme,
    long_description_content_type='text/markdown',
    packages=find_namespace_packages(where='source'),
    package_dir={'': 'source'},
    install_requires=install_requires,
    extras_require=extras_require,
    python_requires='>=3.8.0',
)