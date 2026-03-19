# TTS-specifc add ons
from pathlib import Path
from datetime import datetime
from setuptools_scm import get_version
import toml

# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#

import os
import sys
import importlib.metadata
sys.path.insert(0, os.path.abspath('..'))

# -- Project information -----------------------------------------------------

pyproject = toml.load(Path(__file__).parent.parent.joinpath("pyproject.toml"))
project = pyproject["project"]["name"]
release = get_version(root='..', relative_to=__file__)
version = '.'.join(release.split('.')[:2])

copyright = f'{datetime.now().strftime('%Y')} JPL'
author = 'JPL Teamtools Studio'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The master toctree document.
master_doc = 'index'

pygments_style = 'sphinx'
# html_theme = 'nature'
# html_theme = 'sphinx_material'
html_theme = 'pydata_sphinx_theme'

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static', 'validation_reports']
html_extra_path = ['validation_reports']
html_css_files = ['bugfix.css']
html_copy_source = False
html_show_sourcelink = False


# -- Make Validation Reports -------------------------------------------------

import os
import sys
import importlib
import inspect
from pathlib import Path
from tts_html_utils.core.compiler import HtmlCompiler
from tts_html_utils.core.components.text import H1, P

def setup(app):
    app.connect("builder-inited", generate_all_validation_docs)

def generate_all_validation_docs(app):
    # 1. Setup Paths
    docs_root = Path(app.srcdir)
    # Adjust 'src' to wherever your library code actually lives
    lib_root = docs_root.parent / "src" / "my_lib" 
    output_base = docs_root / "validation_reports"
    
    # Add lib_root to sys.path so we can import the modules
    if str(lib_root.parent) not in sys.path:
        sys.path.insert(0, str(lib_root.parent))

    # Clean/Prep output directory
    if output_base.exists():
        import shutil
        shutil.rmtree(output_base)
    output_base.mkdir(parents=True, exist_ok=True)

    # 2. Walk the Tree
    for py_file in lib_root.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        # Convert file path to module path (e.g., my_lib.aligner.core)
        rel_path = py_file.relative_to(lib_root.parent)
        module_name = ".".join(rel_path.with_suffix("").parts)
        
        # Determine target HTML path
        rel_output_path = py_file.relative_to(lib_root).with_suffix(".html")
        target_html = output_base / rel_output_path
        target_html.parent.mkdir(parents=True, exist_ok=True)

        try:
            # 3. Dynamically Import and Check for Method
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "generate_validation_report"):
                print(f"✅ Generating report for: {module_name}")
                # Call the method. It should return an HtmlCompiler object 
                # or save the file itself. 
                # Assuming it returns a component/compiler as per our previous work:
                report_compiler = module.generate_validation_report()
                report_compiler.render_to_file(str(target_html))
            else:
                generate_fallback_page(module_name, target_html)

        except Exception as e:
            print(f"❌ Failed to process {module_name}: {e}")
            generate_fallback_page(module_name, target_html, error=str(e))

def generate_fallback_page(module_name, target_path, error=None):
    """Creates a simple placeholder HTML for modules without reports."""
    compiler = HtmlCompiler(title=f"No Report: {module_name}")
    compiler.add_body_component(H1(f"Validation Status: {module_name}"))
    if error:
        compiler.add_body_component(P(f"An error occurred while loading this module: {error}"))
    else:
        compiler.add_body_component(P(f"No custom validation report defined for this module."))
    compiler.render_to_file(str(target_path))
