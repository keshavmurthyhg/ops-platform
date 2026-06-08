"""
path_helper.py
--------------
Call `setup_paths()` at the top of any standalone module app.py so that
both the project root and the common/ folder are on sys.path.

Usage (in a module's app.py):
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from common.path_helper import setup_paths
    setup_paths(__file__)
"""

import sys
import os


def setup_paths(caller_file: str) -> str:
    """
    Add the project root to sys.path so that ``common.*`` and all
    sibling module packages are importable.

    Parameters
    ----------
    caller_file : str
        Pass ``__file__`` from the calling script.

    Returns
    -------
    str
        Absolute path of the project root.
    """
    # e.g.  /project/operations_center/app.py  -> /project
    module_dir = os.path.dirname(os.path.abspath(caller_file))
    project_root = os.path.dirname(module_dir)

    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    return project_root
