"""
API Package - Clean backend API structure
"""

from .server import app
from .routes import router
from .models import *

__all__ = ['app', 'router']
