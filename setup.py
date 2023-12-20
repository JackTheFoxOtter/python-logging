from setuptools import setup

with open('source/jtfo_logging/_metadata.py') as f:
    exec(f.read())

with open('README.md') as f:
    readme = f.read()

setup(
    name=__title__,
    description=__description__,
    author=__author__,
    license=__license__,
    url=__url__,
    version=__version__,
    long_description=readme,
    long_description_content_type='text/markdown',
    install_requires=[],
    extras_require={
        'discord.py': {
            'discord.py'
        }
    },
    python_requires='>=3.8.0',
)