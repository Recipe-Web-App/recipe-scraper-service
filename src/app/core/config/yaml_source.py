"""Custom YAML settings source with environment-based file merging."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from pydantic_settings import PydanticBaseSettingsSource


if TYPE_CHECKING:
    from pydantic.fields import FieldInfo


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge override into base dict.

    Args:
        base: Base dictionary to merge into.
        override: Dictionary with values to override.

    Returns:
        New dictionary with merged values.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class MultiYamlConfigSettingsSource(PydanticBaseSettingsSource):
    """Load and merge multiple YAML files based on APP_ENV.

    This settings source loads configuration from YAML files in two stages:
    1. Load all base YAML files from config/base/
    2. Deep-merge environment-specific overrides from config/environments/{APP_ENV}/

    The APP_ENV environment variable determines which environment directory to use.
    """

    def __init__(self, settings_cls: type[Any]) -> None:
        """Initialize the YAML settings source.

        Args:
            settings_cls: The settings class to load configuration for.
        """
        super().__init__(settings_cls)
        self._config_dir = self._find_config_dir()
        self._app_env = os.getenv("APP_ENV", "development")
        self._yaml_data: dict[str, Any] = {}
        self._load_yaml_files()

    def _find_config_dir(self) -> Path:
        """Find the config directory relative to the project root.

        Returns:
            Path to the config directory.
        """
        # Start from this file and navigate to project root
        # src/app/core/config/yaml_source.py -> project root
        current = Path(__file__).resolve()
        project_root = current.parent.parent.parent.parent.parent
        return project_root / "config"

    def _load_yaml_files(self) -> None:
        """Load base configs, then merge environment-specific overrides."""
        merged: dict[str, Any] = {}

        # Load all base YAML files
        base_dir = self._config_dir / "base"
        if base_dir.exists():
            for yaml_file in sorted(base_dir.glob("*.yaml")):
                with yaml_file.open(encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    merged = deep_merge(merged, data)

        # Load environment-specific overrides
        env_dir = self._config_dir / "environments" / self._app_env
        if env_dir.exists():
            for yaml_file in sorted(env_dir.glob("*.yaml")):
                with yaml_file.open(encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    merged = deep_merge(merged, data)

        self._yaml_data = merged

    def get_field_value(
        self,
        _field: FieldInfo,
        field_name: str,
    ) -> tuple[Any, str, bool]:
        """Get the value for a specific field from YAML data.

        Args:
            field: The field info from the settings model.
            field_name: The name of the field.

        Returns:
            Tuple of (value, field_name, is_complex).
        """
        value = self._yaml_data.get(field_name)
        return value, field_name, isinstance(value, (dict, list))

    def __call__(self) -> dict[str, Any]:
        """Return all YAML configuration data.

        Returns:
            Dictionary containing all merged YAML configuration.
        """
        return self._yaml_data
