"""Display identity, independent of financial inputs and authentication.

A future profile editor can replace this session value with another display
name. It is neither an authenticated identity nor a persistent user record.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class UserContext:
    display_name: str = "Carlos"
