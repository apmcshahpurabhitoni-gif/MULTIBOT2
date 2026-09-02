from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "dashboard.html").read_text(encoding="utf-8")
CSS = (ROOT / "styles.css").read_text(encoding="utf-8")


def test_dashboard_keeps_approved_theme_and_mobile_contract():
    assert 'data-theme="light"' in HTML
    assert 'data-style="modern"' in HTML
    assert 'data-theme="light"' in CSS
    assert 'data-theme="dark"' in CSS
    assert 'data-style="neo"' in CSS
    assert 'prefers-reduced-motion: reduce' in CSS
    assert 'position: fixed' in CSS
    assert 'bottom: 7px' in CSS


def test_dashboard_keeps_trading_presentation_layers_separate():
    assert '/api/dashboard' in HTML or '/api/dashboard' in (ROOT / "app.js").read_text(encoding="utf-8")
    assert 'signal-card' in CSS
    assert 'trade-card' in CSS
    assert 'news-item' in CSS
    assert 'backtest-chart' in CSS
    assert 'No FVG' not in HTML


def test_dashboard_has_clear_visual_hierarchy_tokens():
    for token in (
        '--surface',
        '--surface-2',
        '--accent',
        '--positive',
        '--negative',
        '--warning',
        '--shadow',
        '--radius',
    ):
        assert token in CSS

    for selector in (
        '.topbar',
        '.desktop-nav',
        '.page-heading',
        '.hero',
        '.box',
        '.signal-card',
        '.trade-card',
        '.news-item',
    ):
        assert selector in CSS
