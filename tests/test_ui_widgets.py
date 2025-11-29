"""Tests for UI widgets."""

from rich.console import Console

from terminalride.ui.widgets import DistanceProgressBar


def render_panel(panel) -> str:
    console = Console(record=True, width=80)
    console.print(panel)
    return console.export_text()


class TestDistanceProgressBar:
    """Tests for the DistanceProgressBar widget."""

    def test_progress_calculation_basic(self):
        """Test basic progress calculations."""
        widget = DistanceProgressBar()

        metrics = {"distance_m": 500.0}

        rendered = render_panel(widget.render(metrics))
        assert "KM 1" in rendered
        assert "50%" in rendered
        assert "500 m" in rendered

    def test_progress_calculation_multiple_km(self):
        """Test progress across multiple kilometers."""
        widget = DistanceProgressBar()

        metrics = {"distance_m": 2300.0}

        rendered = render_panel(widget.render(metrics))
        assert "KM 3" in rendered
        assert "30%" in rendered
        assert "300 m" in rendered

    def test_progress_calculation_exact_km(self):
        """Test progress at exact kilometer boundaries."""
        widget = DistanceProgressBar()

        metrics = {"distance_m": 2000.0}

        rendered = render_panel(widget.render(metrics))
        assert "KM 3" in rendered
        assert "0%" in rendered
        assert "0 m" in rendered

    def test_progress_calculation_zero_distance(self):
        """Test progress with zero distance."""
        widget = DistanceProgressBar()

        metrics = {"distance_m": 0.0}

        rendered = render_panel(widget.render(metrics))
        assert "KM 1" in rendered
        assert "0%" in rendered
        assert "0 m" in rendered

    def test_progress_calculation_no_distance(self):
        """Test progress with missing distance metric."""
        widget = DistanceProgressBar()

        metrics = {}

        rendered = render_panel(widget.render(metrics))
        assert "KM 1" in rendered
        assert "0%" in rendered
        assert "0 m" in rendered

    def test_progress_calculation_negative_distance(self):
        """Test progress with negative distance (edge case)."""
        widget = DistanceProgressBar()

        metrics = {"distance_m": -100.0}

        rendered = render_panel(widget.render(metrics))
        assert "KM 1" in rendered
        assert "0%" in rendered
        assert "0 m" in rendered

    def test_progress_bar_rendering(self):
        """Test that progress bar renders correctly."""
        widget = DistanceProgressBar()

        metrics = {"distance_m": 750.0}

        rendered = render_panel(widget.render(metrics))

        assert "KM 1" in rendered
        assert "75%" in rendered
        assert "750 m" in rendered
        assert len(rendered.strip()) > 20
