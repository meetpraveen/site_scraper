from site_scraper.models import SiteConfig


def test_site_config_defaults():
    config = SiteConfig(name="example", url="https://example.com")
    assert config.rebuild_mode == "ask"
    assert "paginate" in config.guardrails.allowed_actions
    assert config.auth.persist_state is False
