"""Callback modules for Dash dashboard"""
from .auth_callbacks import register_auth_callbacks
from .nieuwe_run_callbacks import register_nieuwe_run_callbacks
from .run_callbacks import register_run_callbacks
from .mapping_callbacks import register_mapping_callbacks

__all__ = [
    "register_auth_callbacks",
    "register_nieuwe_run_callbacks",
    "register_run_callbacks",
    "register_mapping_callbacks",
]
