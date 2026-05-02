"""Tests for configuration management."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from terminalride.config import (
    UserSettings,
    AppConfig,
    get_config,
    reload_config,
)


class TestUserSettingsDefaults:
    """Test UserSettings default values."""

    def test_default_user_profile(self):
        """Test default user profile settings."""
        settings = UserSettings()

        assert settings.name == "Rider"
        assert settings.age == 30
        assert settings.gender == "male"
        assert settings.mass_kg == 75.0
        assert settings.ftp_w is None
        assert settings.max_hr_bpm is None

    def test_default_physics_params(self):
        """Test default physics parameters."""
        settings = UserSettings()

        assert settings.cda_m2 == 0.33
        assert settings.crr == 0.0045

    def test_default_ui_preferences(self):
        """Test default UI preferences."""
        settings = UserSettings()

        assert settings.units == "metric"
        assert settings.refresh_rate_hz == 10
        assert settings.show_legend is False

    def test_default_device_preferences(self):
        """Test default device preferences."""
        settings = UserSettings()

        assert settings.auto_connect_trainer is True
        assert settings.auto_connect_hr is False
        assert settings.reconnect_timeout_s == 30

    def test_default_training_settings(self):
        """Test default training settings."""
        settings = UserSettings()

        assert settings.default_erg_power_w == 150
        assert settings.default_sim_grade_pct == 0.0
        assert settings.default_sim_route_id == "demo_rolling_route"
        assert settings.speed_source == "trainer"


class TestUserSettingsValidation:
    """Test UserSettings validation constraints."""

    def test_age_bounds(self):
        """Test age field bounds."""
        # Valid bounds
        settings = UserSettings(age=10)
        assert settings.age == 10

        settings = UserSettings(age=100)
        assert settings.age == 100

        # Invalid - too low
        with pytest.raises(ValidationError):
            UserSettings(age=9)

        # Invalid - too high
        with pytest.raises(ValidationError):
            UserSettings(age=101)

    def test_gender_pattern(self):
        """Test gender field pattern validation."""
        settings = UserSettings(gender="male")
        assert settings.gender == "male"

        settings = UserSettings(gender="female")
        assert settings.gender == "female"

        with pytest.raises(ValidationError):
            UserSettings(gender="other")

    def test_mass_bounds(self):
        """Test mass_kg field bounds."""
        settings = UserSettings(mass_kg=40.0)
        assert settings.mass_kg == 40.0

        settings = UserSettings(mass_kg=200.0)
        assert settings.mass_kg == 200.0

        with pytest.raises(ValidationError):
            UserSettings(mass_kg=39.9)

        with pytest.raises(ValidationError):
            UserSettings(mass_kg=200.1)

    def test_ftp_bounds(self):
        """Test FTP field bounds (optional)."""
        settings = UserSettings(ftp_w=50)
        assert settings.ftp_w == 50

        settings = UserSettings(ftp_w=600)
        assert settings.ftp_w == 600

        settings = UserSettings(ftp_w=None)
        assert settings.ftp_w is None

        with pytest.raises(ValidationError):
            UserSettings(ftp_w=49)

        with pytest.raises(ValidationError):
            UserSettings(ftp_w=601)

    def test_max_hr_bounds(self):
        """Test max HR field bounds (optional)."""
        settings = UserSettings(max_hr_bpm=100)
        assert settings.max_hr_bpm == 100

        settings = UserSettings(max_hr_bpm=230)
        assert settings.max_hr_bpm == 230

        with pytest.raises(ValidationError):
            UserSettings(max_hr_bpm=99)

        with pytest.raises(ValidationError):
            UserSettings(max_hr_bpm=231)

    def test_cda_bounds(self):
        """Test CdA field bounds."""
        settings = UserSettings(cda_m2=0.2)
        assert settings.cda_m2 == 0.2

        settings = UserSettings(cda_m2=0.5)
        assert settings.cda_m2 == 0.5

        with pytest.raises(ValidationError):
            UserSettings(cda_m2=0.19)

        with pytest.raises(ValidationError):
            UserSettings(cda_m2=0.51)

    def test_crr_bounds(self):
        """Test Crr field bounds."""
        settings = UserSettings(crr=0.003)
        assert settings.crr == 0.003

        settings = UserSettings(crr=0.008)
        assert settings.crr == 0.008

        with pytest.raises(ValidationError):
            UserSettings(crr=0.0029)

        with pytest.raises(ValidationError):
            UserSettings(crr=0.0081)

    def test_units_pattern(self):
        """Test units field pattern validation."""
        settings = UserSettings(units="metric")
        assert settings.units == "metric"

        settings = UserSettings(units="imperial")
        assert settings.units == "imperial"

        with pytest.raises(ValidationError):
            UserSettings(units="si")

    def test_refresh_rate_bounds(self):
        """Test refresh rate bounds."""
        settings = UserSettings(refresh_rate_hz=1)
        assert settings.refresh_rate_hz == 1

        settings = UserSettings(refresh_rate_hz=30)
        assert settings.refresh_rate_hz == 30

        with pytest.raises(ValidationError):
            UserSettings(refresh_rate_hz=0)

        with pytest.raises(ValidationError):
            UserSettings(refresh_rate_hz=31)

    def test_reconnect_timeout_bounds(self):
        """Test reconnect timeout bounds."""
        settings = UserSettings(reconnect_timeout_s=5)
        assert settings.reconnect_timeout_s == 5

        settings = UserSettings(reconnect_timeout_s=300)
        assert settings.reconnect_timeout_s == 300

        with pytest.raises(ValidationError):
            UserSettings(reconnect_timeout_s=4)

        with pytest.raises(ValidationError):
            UserSettings(reconnect_timeout_s=301)

    def test_erg_power_bounds(self):
        """Test default ERG power bounds."""
        settings = UserSettings(default_erg_power_w=100)
        assert settings.default_erg_power_w == 100

        settings = UserSettings(default_erg_power_w=400)
        assert settings.default_erg_power_w == 400

        with pytest.raises(ValidationError):
            UserSettings(default_erg_power_w=99)

        with pytest.raises(ValidationError):
            UserSettings(default_erg_power_w=401)

    def test_sim_grade_bounds(self):
        """Test default sim grade bounds."""
        settings = UserSettings(default_sim_grade_pct=-10.0)
        assert settings.default_sim_grade_pct == -10.0

        settings = UserSettings(default_sim_grade_pct=15.0)
        assert settings.default_sim_grade_pct == 15.0

        with pytest.raises(ValidationError):
            UserSettings(default_sim_grade_pct=-10.1)

        with pytest.raises(ValidationError):
            UserSettings(default_sim_grade_pct=15.1)

    def test_speed_source_pattern(self):
        """Test speed source pattern validation."""
        for valid in ["trainer", "virtual", "auto"]:
            settings = UserSettings(speed_source=valid)
            assert settings.speed_source == valid

        with pytest.raises(ValidationError):
            UserSettings(speed_source="invalid")


class TestUserSettingsSerialization:
    """Test UserSettings serialization."""

    def test_model_dump(self):
        """Test settings can be dumped to dict."""
        settings = UserSettings(name="Test Rider", mass_kg=80.0)

        data = settings.model_dump()

        assert isinstance(data, dict)
        assert data["name"] == "Test Rider"
        assert data["mass_kg"] == 80.0

    def test_model_validate(self):
        """Test settings can be loaded from dict."""
        data = {
            "name": "Test Rider",
            "age": 35,
            "mass_kg": 80.0,
            "ftp_w": 280,
        }

        settings = UserSettings.model_validate(data)

        assert settings.name == "Test Rider"
        assert settings.age == 35
        assert settings.mass_kg == 80.0
        assert settings.ftp_w == 280


class TestAppConfig:
    """Test AppConfig functionality."""

    def test_init_creates_directories(self, tmp_path):
        """Test initialization creates config directories."""
        config = AppConfig(config_dir=tmp_path / "config")

        assert config.config_dir.exists()
        assert config.log_dir.exists()

    def test_init_with_custom_dir(self, tmp_path):
        """Test initialization with custom config directory."""
        custom_dir = tmp_path / "custom_config"

        config = AppConfig(config_dir=custom_dir)

        assert config.config_dir == custom_dir
        assert custom_dir.exists()

    def test_default_settings_when_no_file(self, tmp_path):
        """Test default settings are used when no config file exists."""
        config = AppConfig(config_dir=tmp_path / "config")

        assert config.settings.name == "Rider"
        assert config.settings.mass_kg == 75.0

    def test_load_settings_from_file(self, tmp_path):
        """Test loading settings from existing config file."""
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.json"

        settings_data = {
            "name": "Custom Rider",
            "age": 40,
            "mass_kg": 85.0,
            "ftp_w": 300,
        }
        config_file.write_text(json.dumps(settings_data))

        config = AppConfig(config_dir=config_dir)

        assert config.settings.name == "Custom Rider"
        assert config.settings.age == 40
        assert config.settings.mass_kg == 85.0
        assert config.settings.ftp_w == 300

    def test_load_settings_handles_invalid_json(self, tmp_path):
        """Test loading settings handles invalid JSON gracefully."""
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.json"
        config_file.write_text("this is not valid json")

        # Should not raise, uses defaults
        config = AppConfig(config_dir=config_dir)

        assert config.settings.name == "Rider"

    def test_load_settings_handles_invalid_values(self, tmp_path):
        """Test loading settings handles invalid values gracefully."""
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.json"

        # Invalid age value
        settings_data = {"age": 5}  # Below minimum
        config_file.write_text(json.dumps(settings_data))

        # Should not raise, uses defaults
        config = AppConfig(config_dir=config_dir)

        assert config.settings.age == 30  # Default value

    def test_save_settings(self, tmp_path):
        """Test saving settings to file."""
        config = AppConfig(config_dir=tmp_path / "config")
        config.settings.name = "Updated Rider"
        config.settings.mass_kg = 90.0

        config.save_settings()

        # Verify file contents
        with open(config.config_file) as f:
            data = json.load(f)

        assert data["name"] == "Updated Rider"
        assert data["mass_kg"] == 90.0

    def test_save_load_roundtrip(self, tmp_path):
        """Test settings survive save/load cycle."""
        config_dir = tmp_path / "config"

        # Create and save
        config1 = AppConfig(config_dir=config_dir)
        config1.settings.name = "Roundtrip Test"
        config1.settings.ftp_w = 275
        config1.save_settings()

        # Load fresh
        config2 = AppConfig(config_dir=config_dir)

        assert config2.settings.name == "Roundtrip Test"
        assert config2.settings.ftp_w == 275

    def test_get_log_file_path(self, tmp_path):
        """Test getting log file path."""
        config = AppConfig(config_dir=tmp_path / "config")

        log_path = config.get_log_file_path("test")

        assert log_path == config.log_dir / "test.log"

    def test_get_log_file_path_default(self, tmp_path):
        """Test getting default log file path."""
        config = AppConfig(config_dir=tmp_path / "config")

        log_path = config.get_log_file_path()

        assert log_path == config.log_dir / "app.log"

    def test_get_data_dir(self, tmp_path):
        """Test getting data directory."""
        config = AppConfig(config_dir=tmp_path / "config")

        data_dir = config.get_data_dir()

        assert data_dir == config.config_dir / "data"
        assert data_dir.exists()

    def test_app_level_config_from_settings(self, tmp_path):
        """Test app-level config is derived from settings."""
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.json"

        settings_data = {
            "mass_kg": 82.0,
            "ftp_w": 290,
            "reconnect_timeout_s": 45,
        }
        config_file.write_text(json.dumps(settings_data))

        config = AppConfig(config_dir=config_dir)

        assert config.user_mass_kg == 82.0
        assert config.user_ftp_w == 290
        assert config.connection_timeout_s == 45

    def test_default_ftp_when_not_set(self, tmp_path):
        """Test default FTP value when not set in settings."""
        config = AppConfig(config_dir=tmp_path / "config")

        # FTP not set in settings
        assert config.settings.ftp_w is None
        # Should default to 250
        assert config.user_ftp_w == 250


class TestConfigSingleton:
    """Test singleton instance management."""

    def test_get_config_returns_instance(self, tmp_path):
        """Test get_config returns an AppConfig instance."""
        import terminalride.config as module

        module._config = None

        with patch.object(Path, "home", return_value=tmp_path):
            config = get_config()

        assert isinstance(config, AppConfig)

    def test_get_config_returns_same_instance(self, tmp_path):
        """Test get_config returns the same instance."""
        import terminalride.config as module

        module._config = None

        with patch.object(Path, "home", return_value=tmp_path):
            config1 = get_config()
            config2 = get_config()

        assert config1 is config2

    def test_reload_config_creates_new_instance(self, tmp_path):
        """Test reload_config creates a new instance."""
        import terminalride.config as module

        module._config = None

        with patch.object(Path, "home", return_value=tmp_path):
            config1 = get_config()
            config2 = reload_config()

        assert config1 is not config2
        assert isinstance(config2, AppConfig)
