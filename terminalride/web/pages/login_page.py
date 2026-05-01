"""Login page for le-tour.

Provides a clean, branded login experience with Google OAuth.
"""

from nicegui import ui

from ..auth import AuthManager
from ..theme import WEB_STYLES

# Login page styles
LOGIN_STYLES = """
<style>
.login-container {
    min-height: 100vh;
    display: grid;
    align-items: center;
    background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.72), rgba(244, 242, 238, 0.92)),
        var(--tr-bg);
    padding: 32px;
}

.login-grid {
    display: grid;
    gap: 16px;
    grid-template-columns: minmax(0, 1fr) minmax(360px, 420px);
    margin: 0 auto;
    width: min(980px, 100%);
}

.login-preview,
.login-card {
    background: rgba(255, 254, 253, 0.92);
    border: 1px solid var(--tr-border);
    border-radius: var(--tr-radius);
    box-shadow: var(--tr-shadow);
    padding: 24px;
}

.login-preview {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 420px;
}

.login-card {
    align-self: center;
}

.login-title {
    color: var(--tr-text);
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: 0;
    line-height: 1;
    margin: 0 0 0.7rem 0;
}

.login-subtitle {
    color: var(--tr-muted);
    font-size: 1rem;
    line-height: 1.5;
    margin: 0 0 1.5rem 0;
}

.google-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    width: 100%;
    padding: 1rem 1.5rem;
    background: var(--tr-accent);
    color: white;
    border: 1px solid var(--tr-accent);
    border-radius: var(--tr-radius);
    font-size: 1rem;
    font-weight: 800;
    font-family: inherit;
    cursor: pointer;
    transition: all 0.2s ease;
}

.google-btn:hover {
    background: var(--tr-accent-dark);
    border-color: var(--tr-accent-dark);
}

.google-btn svg {
    width: 20px;
    height: 20px;
}

.login-features {
    margin-top: 1.5rem;
    padding-top: 1.25rem;
    border-top: 1px solid var(--tr-border);
}

.feature-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    text-align: left;
}

.feature-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--tr-muted);
    font-size: 0.875rem;
    font-weight: 600;
}

.feature-item::before {
    content: "";
    background: var(--tr-green);
    border-radius: 999px;
    height: 7px;
    width: 7px;
    font-weight: bold;
}

.login-footer {
    margin-top: 2rem;
    font-size: 0.75rem;
    color: var(--tr-soft);
}

.login-footer a {
    color: var(--tr-muted);
    text-decoration: underline;
}

.preview-metric {
    border-top: 1px solid var(--tr-border);
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    padding-top: 18px;
}

@media (max-width: 760px) {
    .login-grid {
        grid-template-columns: 1fr;
    }

    .login-preview {
        min-height: auto;
    }
}
</style>
"""

# Google icon SVG
GOOGLE_ICON = """
<svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#ffffff"/>
    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#ffffff"/>
    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#ffffff"/>
    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#ffffff"/>
</svg>
"""


def render_login_page() -> None:
    """Render the login page with Google OAuth button."""

    # Inject styles
    ui.html(WEB_STYLES + LOGIN_STYLES, sanitize=False)

    with ui.element("div").classes("login-container"):
        with ui.element("div").classes("login-grid"):
            with ui.element("div").classes("login-preview"):
                with ui.column().classes("gap-3"):
                    with ui.row().classes("items-center gap-3"):
                        ui.html('<span class="tr-brand-mark">TR</span>', sanitize=False)
                        ui.label("TerminalRide").classes("text-xl font-extrabold")
                    ui.label("Local ride control for FTMS trainers.").classes(
                        "tr-title"
                    )
                    ui.label(
                        "Start a ride, pair hardware, and keep live metrics in one precise console."
                    ).classes("tr-subtitle")
                with ui.element("div").classes("preview-metric"):
                    for value, label in [
                        ("--", "Watts"),
                        ("--", "RPM"),
                        ("--", "BPM"),
                    ]:
                        with ui.column().classes("gap-1"):
                            ui.label(value).classes("tr-metric-value")
                            ui.label(label).classes("tr-metric-label")

            with ui.element("div").classes("login-card"):
                ui.html('<h1 class="login-title">Sign in</h1>', sanitize=False)
                ui.html(
                    '<p class="login-subtitle">Use your account to keep ride data and settings separate.</p>',
                    sanitize=False,
                )

                async def handle_google_login():
                    try:
                        url = AuthManager.get_login_url()
                        await ui.run_javascript(f'window.location.href = "{url}"')
                    except Exception as e:
                        ui.notify(f"Login error: {e}", type="negative")

                with (
                    ui.element("button")
                    .classes("google-btn")
                    .on("click", handle_google_login)
                ):
                    ui.html(GOOGLE_ICON)
                    ui.label("Continue with Google")

                with ui.element("div").classes("login-features"):
                    with ui.element("div").classes("feature-list"):
                        ui.html(
                            '<div class="feature-item">Connect to your FTMS trainer</div>'
                        )
                        ui.html(
                            '<div class="feature-item">Track power, cadence, and heart rate</div>'
                        )
                        ui.html(
                            '<div class="feature-item">Ride Free, ERG, and SIM modes</div>'
                        )
                        ui.html(
                            '<div class="feature-item">Keep history ready for analysis</div>'
                        )

                ui.html("""
                    <p class="login-footer">
                        By continuing, you agree to our
                        <a href="/terms">Terms</a> and
                        <a href="/privacy">Privacy Policy</a>.
                    </p>
                """)
