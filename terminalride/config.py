"""Configuration management for TerminalRide."""

import os
from pathlib import Path
from typing import Optional
import json

from pydantic import BaseModel, Field


class UserSettings(BaseModel):
    """User configuration settings."""

    # User profile
    name: str = "Rider"
    age: int = Field(default=30, ge=10, le=100)
    gender: str = Field(default="male", pattern="^(male|female)$")
    mass_kg: float = Field(default=75.0, ge=40.0, le=200.0)
    ftp_w: Optional[int] = Field(default=None, ge=50, le=600)
    max_hr_bpm: Optional[int] = Field(default=None, ge=100, le=230)  # Max heart rate

    # Physics parameters
    cda_m2: float = Field(default=0.33, ge=0.2, le=0.5)
    crr: float = Field(default=0.0045, ge=0.003, le=0.008)

    # UI preferences
    units: str = Field(default="metric", pattern="^(metric|imperial)$")
    refresh_rate_hz: int = Field(default=10, ge=1, le=30)

    # Device preferences
    auto_connect_trainer: bool = True
    auto_connect_hr: bool = False
    reconnect_timeout_s: int = Field(default=30, ge=5, le=300)

    # Training defaults
    default_erg_power_w: int = Field(default=150, ge=100, le=400)
    default_sim_grade_pct: float = Field(default=0.0, ge=-10.0, le=15.0)

    # UI toggles
    show_legend: bool = False

    # Speed computation
    # trainer: use trainer-reported speed if available
    # virtual: always compute from physics
    # auto: prefer trainer; fall back to physics if implausible
    speed_source: str = Field(default="trainer", pattern="^(trainer|virtual|auto)$")


class AppConfig:
    """Application configuration manager."""

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            # Use platform-appropriate config directory
            home = Path.home()
            if os.name == "nt":  # Windows
                config_dir = home / "AppData" / "Local" / "TerminalRide"
            else:  # Unix-like (macOS, Linux)
                config_dir = home / ".config" / "terminalride"

        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "config.json"
        self.log_dir = self.config_dir / "logs"

        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Load or create settings
        self.settings = self._load_settings()
        
        # App-level configuration
        self.log_level = "info"
        self.user_mass_kg = self.settings.mass_kg
        # Default to 250W if FTP not set
        self.user_ftp_w = self.settings.ftp_w if self.settings.ftp_w is not None else 250
        self.connection_timeout_s = self.settings.reconnect_timeout_s

    def _load_settings(self) -> UserSettings:
        """Load settings from config file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                return UserSettings.model_validate(data)
            except Exception as e:
                print(f"Warning: Could not load config file: {e}")
                print("Using default settings...")

        # Return default settings
        return UserSettings()

    def save_settings(self) -> None:
        """Save current settings to config file."""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.settings.model_dump(), f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save config file: {e}")

    def get_log_file_path(self, name: str = "app") -> Path:
        """Get path for a log file."""
        return self.log_dir / f"{name}.log"

    def get_data_dir(self) -> Path:
        """Get data directory path."""
        data_dir = self.config_dir / "data"
        data_dir.mkdir(exist_ok=True)
        return data_dir


# Global config instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


def reload_config() -> AppConfig:
    """Reload configuration from disk."""
    global _config
    _config = AppConfig()
    return _config
