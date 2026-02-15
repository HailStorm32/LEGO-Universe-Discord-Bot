from __future__ import annotations

import os
from dataclasses import dataclass
import re
from dotenv import load_dotenv

load_dotenv()


def _color(value: str | None, default: int = 0x3498DB) -> int:
    if not value:
        return default
    raw = value.strip()
    # Support #RRGGBB and plain integer/hex values.
    if re.fullmatch(r"#[0-9a-fA-F]{6}", raw):
        return int(raw[1:], 16)
    try:
        return int(raw, 0)
    except ValueError:
        return default


def _ids(value: str | None) -> list[int]:
    if not value:
        return []
    return [int(x) for x in __import__('re').findall(r"\d+", value)]


@dataclass(frozen=True)
class Settings:
    token: str
    sqlite_path: str
    locale_path: str
    explorer_domain: str
    bot_color: int
    log_channel_id: int
    report_channel_id: int
    lu_server_name: str
    lu_server_icon: str
    footer_text: str
    footer_icon: str
    hq_valid_only: bool
    decimal_places: int
    admin_roles: list[int]


settings = Settings(
    token=os.getenv("LUDB_TOKEN", ""),
    sqlite_path=os.getenv("LUDB_SQLITE_PATH", ""),
    locale_path=os.getenv("LUDB_LOCALE_PATH", ""),
    explorer_domain=os.getenv("LUDB_EXPLORER_DOMAIN", "https://explorer.lu"),
    bot_color=_color(os.getenv("LUDB_BOT_COLOR", "3447003")),
    log_channel_id=int(os.getenv("LUDB_LOG_CHANNEL_ID", "0")),
    report_channel_id=int(os.getenv("LUDB_REPORT_CHANNEL_ID", "0")),
    lu_server_name=os.getenv("LUDB_LU_SERVER_NAME", "LEGO Universe"),
    lu_server_icon=os.getenv("LUDB_LU_SERVER_ICON", ""),
    footer_text=os.getenv("LUDB_FOOTER_TEXT", "LEGO Universe Discord Bot"),
    footer_icon=os.getenv("LUDB_FOOTER_ICON", ""),
    hq_valid_only=os.getenv("LUDB_HQ_VALID_ONLY", "false").lower() == "true",
    decimal_places=int(os.getenv("LUDB_DECIMAL_PLACES", "4")),
    admin_roles=_ids(os.getenv("LUDB_ADMIN_ROLES")),
)
