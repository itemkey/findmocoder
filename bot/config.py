from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: set[int]
    required_channel_username: str
    required_channel_url: str
    promo_text: str
    database_path: Path
    telegram_request_timeout: float
    polling_retry_delay: float
    telegram_proxy_url: str | None
    telegram_force_ipv4: bool


def _parse_positive_float(name: str, default: float) -> float:
    raw_value = os.getenv(name, str(default)).strip()

    try:
        value = float(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number, got {raw_value!r}") from exc

    if value <= 0:
        raise RuntimeError(f"{name} must be greater than 0")

    return value


def _parse_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name, str(default)).strip().lower()

    if raw_value in {"1", "true", "yes", "on"}:
        return True

    if raw_value in {"0", "false", "no", "off"}:
        return False

    raise RuntimeError(f"{name} must be true or false, got {raw_value!r}")


def _parse_admin_ids(raw_value: str) -> set[int]:
    admin_ids: set[int] = set()

    for value in raw_value.replace(" ", "").split(","):
        if not value:
            continue

        try:
            admin_ids.add(int(value))
        except ValueError as exc:
            raise ValueError(
                f"ADMIN_IDS must contain only Telegram user IDs, got {value!r}"
            ) from exc

    return admin_ids


def load_config() -> Config:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    required_channel_username = os.getenv("REQUIRED_CHANNEL_USERNAME", "").strip()
    required_channel_url = os.getenv("REQUIRED_CHANNEL_URL", "").strip()
    promo_text = os.getenv("PROMO_TEXT", "").strip()
    database_path = Path(os.getenv("DATABASE_PATH", "data/bot.sqlite3")).resolve()
    telegram_request_timeout = _parse_positive_float("TELEGRAM_REQUEST_TIMEOUT", 90.0)
    polling_retry_delay = _parse_positive_float("POLLING_RETRY_DELAY", 15.0)
    telegram_proxy_url = os.getenv("TELEGRAM_PROXY_URL", "").strip() or None
    telegram_force_ipv4 = _parse_bool("TELEGRAM_FORCE_IPV4", False)

    missing = [
        name
        for name, value in {
            "BOT_TOKEN": bot_token,
            "REQUIRED_CHANNEL_USERNAME": required_channel_username,
            "REQUIRED_CHANNEL_URL": required_channel_url,
            "PROMO_TEXT": promo_text,
        }.items()
        if not value
    ]

    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    if not required_channel_username.startswith("@"):
        raise RuntimeError("REQUIRED_CHANNEL_USERNAME must start with @, for example @my_channel")

    if not required_channel_url.startswith(("https://", "http://")):
        raise RuntimeError(
            "REQUIRED_CHANNEL_URL must start with https://, for example https://t.me/my_channel"
        )

    admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))
    if not admin_ids:
        raise RuntimeError("ADMIN_IDS must contain at least one Telegram user ID")

    return Config(
        bot_token=bot_token,
        admin_ids=admin_ids,
        required_channel_username=required_channel_username,
        required_channel_url=required_channel_url,
        promo_text=promo_text,
        database_path=database_path,
        telegram_request_timeout=telegram_request_timeout,
        polling_retry_delay=polling_retry_delay,
        telegram_proxy_url=telegram_proxy_url,
        telegram_force_ipv4=telegram_force_ipv4,
    )
