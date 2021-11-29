"""
Pycord
~~~~~~~
Utilitys For The Pycord Discord Library 
"""

__title__ = "Pycord-Utils"
__author__ = "Pycord"
__license__ = "MIT"
__copyright__ = "Copyright 2021 (c) Pycord"


from .cog import *
from .features.baseclass import Feature
from .flags import Flags
from .meta import *

__all__ = (
    'pycord',
    'Feature',
    'Flags',
    'setup'
)
