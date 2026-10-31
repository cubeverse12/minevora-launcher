#!/usr/bin/env python3
"""MINEVORA Microsoft -> Xbox -> Minecraft Java authentication adapter.

User signs in ONLY on Microsoft-owned web pages using OAuth device code.
No localhost callback, embedded web browser, passwords, app secrets or token logs.
Tokens stay in process memory, and this module does not alter the launcher yet.

Developer setup: register a Microsoft public-client application supporting
personal Microsoft accounts. Xbox/Minecraft service access may require separate
approval from Microsoft/Minecraft. This is NOT a bypass for those requirements.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional

AUTHORITY = "https://login.microsoftonline.com/consumers"
SCOPES = ["XboxLive.signin"]
XBOX_USER_ENDPOINT = "https://user.auth.xboxlive.com/user/authenticate"
XSTS_ENDPOINT = "https://xsts.auth.xboxlive.com/xsts/authorize"
MINECRAFT_LOGIN_ENDPOINT = "https://api.minecraftservices.com/authentication/login_with_xbox"
MINECRAFT_ENTITLEMENTS = "https://api.minecraftservices.com/entitlements/mcstore"
MINECRAFT_PROFILE = "https://api.minecraftservices.com/minecraft/profile"
CLIENT_ID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class AuthError(Exception):
    """A public, non-sensitive authentication error."""


@dataclass(frozen=True)
class MinecraftAccount:
    username: str
    uuid: str
    access_token: str
    # Tokens are intentionally not repr-visible.
    def __repr__(self):
        return "MinecraftAccount(username={!r}, uuid={!r}, access_token='<hidden>')".format(self.username, self.uuid)


def public_client_id(value=None) -> str:
    """Configuration, not a secret. Never use somebody else's application ID."""
    value = (value or os.environ.get("MINEVORA_MS_CLIENT_ID") or "").strip()
    if not CLIENT_ID_RE.fullmatch(value):
        raise AuthError("Brak poprawnego MINEVORA_MS_CLIENT_ID. Najpierw zarejestruj własną aplikację Microsoft.")
    return value


def _read_json(url: str, data=None, bearer=None, opener=urllib.request.urlopen):
    """Only fixed, Microsoft-owned HTTPS hosts; never print credentials."""
    from urllib.parse import urlsplit
    host = urlsplit(url).hostname
    if urlsplit(url).scheme != "https" or host not in {
        "user.auth.xboxlive.com", "xsts.auth.xboxlive.com", "api.minecraftservices.com"
    }:
        raise AuthError("Niedozwolony adres usługi uwierzytelniania.")
    if data is not None:
        encoded = json.dumps(data).encode("utf-8")
        method = "POST"
    else:
        encoded = None
        method = "GET"
    headers = {"Accept":"application/json", "User-Agent":"MINEVORA-Launcher/0.1"}
    if encoded is not None:
        headers["Content-Type"] = "application/json"
    if bearer:
        headers["Authorization"] = "Bearer " + bearer
    request = urllib.request.Request(url, data=encoded, headers=headers, method=method)
    try:
        with opener(request, timeout=20) as response:
            raw = response.read(1_000_001)
            if len(raw) > 1_000_000:
                raise AuthError("Zbyt duża odpowiedź usługi uwierzytelniania.")
    except urllib.error.HTTPError as exc:
        # OAuth/XSTS error bodies sometimes contain private information. Don't log them.
        if exc.code in (401, 403):
            raise AuthError("Odmowa dostępu Microsoft/Xbox/Minecraft (HTTP {}). Sprawdź uprawnienia aplikacji i konto.".format(exc.code)) from None
        raise AuthError("Usługa logowania zwróciła błąd HTTP {}.".format(exc.code)) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise AuthError("Nie można połączyć się z usługami Microsoft/Xbox/Minecraft.") from None
    try:
        response = json.loads(raw)
        if not isinstance(response, dict):
            raise ValueError("Wrong response type")
        return response
    except (ValueError, UnicodeDecodeError):
        raise AuthError("Usługa logowania zwróciła nieprawidłową odpowiedź.") from None


def exchange_for_minecraft(ms_access_token: str, opener=urllib.request.urlopen) -> MinecraftAccount:
    """Exchange official Microsoft token for a Minecraft Java account after ownership checks."""
    if not isinstance(ms_access_token, str) or not ms_access_token:
        raise AuthError("Brak tokenu dostępu Microsoft.")
    xbox = _read_json(
        XBOX_USER_ENDPOINT,
        {"Properties":{"AuthMethod":"RPS","SiteName":"user.auth.xboxlive.com","RpsTicket":"d="+ms_access_token},
         "RelyingParty":"http://auth.xboxlive.com","TokenType":"JWT"},
        opener=opener,
    )
    try:
        xbl_token = xbox["Token"]
        xbox_user_hash = xbox["DisplayClaims"]["xui"][0]["uhs"]
        if not all(isinstance(x, str) and x for x in (xbl_token, xbox_user_hash)):
            raise ValueError
    except (KeyError, IndexError, TypeError, ValueError):
        raise AuthError("Nie udało się potwierdzić konta Xbox Live.") from None
    xsts = _read_json(
        XSTS_ENDPOINT,
        {"Properties":{"SandboxId":"RETAIL","UserTokens":[xbl_token]},
         "RelyingParty":"rp://api.minecraftservices.com/","TokenType":"JWT"},
        opener=opener,
    )
    try:
        xsts_token = xsts["Token"]
        xsts_hash = xsts["DisplayClaims"]["xui"][0]["uhs"]
        if not isinstance(xsts_token, str) or not xsts_token or xsts_hash != xbox_user_hash:
            raise ValueError
    except (KeyError, IndexError, TypeError, ValueError):
        raise AuthError("Konto Xbox nie uzyskało uprawnień Minecraft (XSTS).") from None
    minecraft = _read_json(
        MINECRAFT_LOGIN_ENDPOINT,
        {"identityToken":"XBL3.0 x={};{}".format(xbox_user_hash, xsts_token)},
        opener=opener,
    )
    mc_access = minecraft.get("access_token")
    if not isinstance(mc_access, str) or not mc_access:
        raise AuthError("Nie uzyskano tokenu Minecraft Java.")
    entitlements = _read_json(MINECRAFT_ENTITLEMENTS, bearer=mc_access, opener=opener)
    entries = entitlements.get("items")
    if not isinstance(entries, list) or not any(
        isinstance(e, dict) and isinstance(e.get("name"), str) and e["name"]
        for e in entries
    ):
        raise AuthError("Nie potwierdzono uprawnień do Minecraft Java na tym koncie.")
    profile = _read_json(MINECRAFT_PROFILE, bearer=mc_access, opener=opener)
    username, uuid = profile.get("name"), profile.get("id")
    if not isinstance(username, str) or not re.fullmatch(r"[A-Za-z0-9_]{3,16}", username):
        raise AuthError("Nie odnaleziono prawidłowego profilu Minecraft Java.")
    if not isinstance(uuid, str) or not re.fullmatch(r"[a-fA-F0-9]{32}", uuid):
        raise AuthError("Minecraft nie zwrócił prawidłowego identyfikatora konta.")
    return MinecraftAccount(username, uuid, mc_access)


def authenticate_device_code(
    client_id: str,
    on_code: Callable[[str, str, str], None],
    msal_module=None,
    token_exchange=exchange_for_minecraft,
) -> MinecraftAccount:
    """Blocking worker-thread function; on_code(uri, code, message) updates the Qt UI."""
    public_client_id(client_id)
    if msal_module is None:
        try:
            import msal as msal_module
        except ImportError:
            raise AuthError("Brakuje modułu msal. Zainstaluj go w środowisku aplikacji.")
    try:
        app = msal_module.PublicClientApplication(client_id, authority=AUTHORITY)
        flow = app.initiate_device_flow(scopes=SCOPES)
    except Exception:
        raise AuthError("Nie udało się rozpocząć logowania Microsoft (sprawdź rejestrację aplikacji).") from None
    code = flow.get("user_code") if isinstance(flow, dict) else None
    uri = flow.get("verification_uri") if isinstance(flow, dict) else None
    message = flow.get("message") if isinstance(flow, dict) else None
    if not isinstance(code, str) or not code or uri != "https://microsoft.com/devicelogin" and uri != "https://www.microsoft.com/devicelogin":
        raise AuthError("Microsoft nie zwrócił prawidłowego kodu urządzenia.")
    # Only the non-secret user code goes to UI; do not display device_code or access tokens.
    on_code(uri, code, str(message or "Otwórz podany adres Microsoft i wpisz kod."))
    try:
        result = app.acquire_token_by_device_flow(flow)
    except Exception:
        raise AuthError("Nie udało się zakończyć logowania Microsoft.") from None
    if not isinstance(result, dict) or not result.get("access_token"):
        code = result.get("error") if isinstance(result, dict) else ""
        if code in ("authorization_declined", "access_denied"):
            raise AuthError("Logowanie Microsoft zostało anulowane.")
        if code in ("expired_token", "code_expired"):
            raise AuthError("Kod logowania wygasł. Rozpocznij ponownie.")
        raise AuthError("Microsoft nie zakończył logowania. Sprawdź konto, zgodę i uprawnienia aplikacji.")
    return token_exchange(result["access_token"])
