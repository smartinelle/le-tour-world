"""Login page for le-tour.

Provides a clean, branded login experience with Google OAuth.
"""

from nicegui import ui

from ..auth import AuthManager


# Login page styles
LOGIN_STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

.login-container {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

.login-card {
    background: white;
    border-radius: 1.5rem;
    padding: 3rem;
    max-width: 420px;
    width: 90%;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.4);
    text-align: center;
    animation: slideUp 0.5s ease-out;
}

@keyframes slideUp {
    from { 
        opacity: 0; 
        transform: translateY(30px); 
    }
    to { 
        opacity: 1; 
        transform: translateY(0); 
    }
}

.login-logo {
    font-size: 4rem;
    margin-bottom: 0.5rem;
    animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.05); }
}

.login-title {
    font-size: 2rem;
    font-weight: 700;
    color: #1a1a1a;
    margin: 0 0 0.5rem 0;
}

.login-subtitle {
    color: #6b7280;
    font-size: 1rem;
    margin: 0 0 2rem 0;
}

.google-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    width: 100%;
    padding: 1rem 1.5rem;
    background: #EA580C;
    color: white;
    border: none;
    border-radius: 0.75rem;
    font-size: 1rem;
    font-weight: 500;
    font-family: inherit;
    cursor: pointer;
    transition: all 0.2s ease;
}

.google-btn:hover {
    background: #C2410C;
    transform: translateY(-2px);
    box-shadow: 0 10px 25px rgba(234, 88, 12, 0.4);
}

.google-btn:active {
    transform: translateY(0);
}

.google-btn svg {
    width: 20px;
    height: 20px;
}

.login-features {
    margin-top: 2rem;
    padding-top: 1.5rem;
    border-top: 1px solid #e5e7eb;
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
    color: #4b5563;
    font-size: 0.875rem;
}

.feature-item::before {
    content: "✓";
    color: #22c55e;
    font-weight: bold;
}

.login-footer {
    margin-top: 2rem;
    font-size: 0.75rem;
    color: #9ca3af;
}

.login-footer a {
    color: #6b7280;
    text-decoration: underline;
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
    ui.html(LOGIN_STYLES)

    with ui.element("div").classes("login-container"):
        with ui.element("div").classes("login-card"):
            # Logo and branding
            ui.html('<div class="login-logo">🚴</div>')
            ui.html('<h1 class="login-title">TerminalRide</h1>')
            ui.html('<p class="login-subtitle">Indoor cycling, elevated.</p>')

            # Google login button
            async def handle_google_login():
                try:
                    url = AuthManager.get_login_url()
                    # Use JavaScript to redirect (NiceGUI navigate might not work for external URLs)
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

            # Feature highlights
            with ui.element("div").classes("login-features"):
                with ui.element("div").classes("feature-list"):
                    ui.html(
                        '<div class="feature-item">Connect to your FTMS trainer</div>'
                    )
                    ui.html(
                        '<div class="feature-item">Track power, cadence & heart rate</div>'
                    )
                    ui.html(
                        '<div class="feature-item">Free, ERG & SIM training modes</div>'
                    )
                    ui.html(
                        '<div class="feature-item">View your training history</div>'
                    )

            # Footer
            ui.html(
                """
                <p class="login-footer">
                    By continuing, you agree to our 
                    <a href="/terms">Terms</a> and 
                    <a href="/privacy">Privacy Policy</a>.
                </p>
            """
            )
