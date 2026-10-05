"""Read-only TH03 adapter using the shared multi-product PC-98 contract."""

from .th04 import Th04RepositoryAdapter


class Th03RepositoryAdapter(Th04RepositoryAdapter):
    id = "th03-pc98-v1"
    game = "th03"
    game_number = 3
    boundary_path = "config/th03_function_boundaries.csv"
    authored_path = "config/th03_main_authored_functions.csv"
    _required = (
        "config/targets.toml",
        "config/toolchain.toml",
        boundary_path,
        authored_path,
        "config/units.csv",
    )
