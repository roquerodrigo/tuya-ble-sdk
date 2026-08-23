"""The logged-in mobile session every account call derives from."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AccountSession:
    """
    The credentials the gateway hands back on a successful login.

    ``sid`` scopes the API calls, ``ecode`` keys the encrypted request bodies
    and ``uid`` names the account.
    """

    sid: str
    ecode: str
    uid: str
