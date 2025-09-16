# -*- coding: utf-8 -*-

import setuptools
import importlib
import os

module_path = os.path.join(os.path.dirname(__file__), "inventree_dymo", "__init__.py")
spec = importlib.util.spec_from_file_location("inventree_dymo", module_path)
inventree_dymo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventree_dymo)


with open('README.md', encoding='utf-8') as f:
    long_description = f.read()


setuptools.setup(
    name="inventree-dymo-plugin",

    version=inventree_dymo.PLUGIN_VERSION,

    author="wolflu05",

    author_email="76838159+wolflu05@users.noreply.github.com",

    description="Dymo Label printer driver plugin for InvenTree.",

    long_description=long_description,

    long_description_content_type='text/markdown',

    keywords="inventree dymo",

    url="https://github.com/wolflu05/inventree-dymo-plugin",

    license="GPL3+",

    packages=setuptools.find_packages(),

    install_requires=[],

    setup_requires=[
        "wheel",
        "twine",
    ],

    python_requires=">=3.9",

    entry_points={
        "inventree_plugins": [
            "InvenTreeDymoPlugin = inventree_dymo.InvenTreeDymoPlugin:InvenTreeDymoPlugin"
        ]
    },

    include_package_data=True,
)
