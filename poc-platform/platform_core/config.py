"""Platform-level configuration (`platform.yaml`) and well-known paths."""

import os
from typing import Union

import yaml
from pydantic import BaseModel, Field

PLATFORM_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILENAME = "platform.yaml"

#: Runtime state the platform owns: per-app databases and process logs. Wiped by
#: `./reset.sh`; never committed.
STATE_DIR = os.path.join(PLATFORM_DIR, ".data")
LOG_DIR = os.path.join(STATE_DIR, "logs")


class GatewaySpec(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8080
    proxy_timeout_seconds: float = 60.0
    #: "none", "all", or an explicit list of app ids.
    autostart: Union[str, list[str]] = "none"

    def autostart_ids(self, known_ids: list[str]) -> list[str]:
        """Resolve the `autostart` setting against the registered apps."""
        if isinstance(self.autostart, list):
            return [app_id for app_id in self.autostart if app_id in known_ids]
        if self.autostart == "all":
            return list(known_ids)
        return []


class Principal(BaseModel):
    """A mocked person. Roles are per app, because each app names them itself."""

    email: str
    display_name: str
    title: str = ""
    platform_role: str = "reviewer"
    app_roles: dict[str, str] = Field(default_factory=dict)


class PlatformConfig(BaseModel):
    gateway: GatewaySpec = Field(default_factory=GatewaySpec)
    apps_root: str = ".."
    default_principal: str
    principals: list[Principal] = Field(min_length=1)

    def resolved_apps_root(self, platform_dir: str = PLATFORM_DIR) -> str:
        return os.path.normpath(os.path.join(platform_dir, self.apps_root))


def load_config(path: str) -> PlatformConfig:
    with open(path, "r", encoding="utf-8") as handle:
        return PlatformConfig.model_validate(yaml.safe_load(handle))


def default_config_path(platform_dir: str = PLATFORM_DIR) -> str:
    return os.path.join(platform_dir, CONFIG_FILENAME)
