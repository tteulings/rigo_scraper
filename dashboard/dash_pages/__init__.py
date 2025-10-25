"""Page modules for Dash dashboard"""

from .resultaten_page import create_resultaten_page
from .run_detail_page import create_run_detail_page
from .nieuwe_run_page import create_nieuwe_run_page
from .mapping_page import create_mapping_page
from .instellingen_page import create_instellingen_page
from .login_page import create_login_page
from .error_page import create_404_page, create_error_page

__all__ = [
    "create_resultaten_page",
    "create_run_detail_page",
    "create_nieuwe_run_page",
    "create_mapping_page",
    "create_instellingen_page",
    "create_login_page",
    "create_404_page",
    "create_error_page",
]
