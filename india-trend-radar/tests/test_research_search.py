"""Tests for engine/research_search.py's find_official_website helper."""

from engine import research_search


def test_find_official_website_prefers_serper(monkeypatch):
    monkeypatch.setattr(
        research_search, "_serper_request",
        lambda *a, **k: {"organic": [{"link": "https://serper.example.com"}]},
    )
    url = research_search.find_official_website("Acme", "serper-key", "serp-key", "tavily-key")
    assert url == "https://serper.example.com"


def test_find_official_website_falls_back_to_serpapi_when_serper_fails(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("serper down")

    monkeypatch.setattr(research_search, "_serper_request", _boom)
    monkeypatch.setattr(
        research_search, "_serpapi_request",
        lambda *a, **k: {"organic_results": [{"link": "https://serpapi.example.com"}]},
    )
    url = research_search.find_official_website("Acme", "serper-key", "serp-key", None)
    assert url == "https://serpapi.example.com"


def test_find_official_website_falls_back_to_tavily_last(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setattr(research_search, "_serper_request", _boom)
    monkeypatch.setattr(research_search, "_serpapi_request", _boom)
    monkeypatch.setattr(
        research_search, "_tavily_request",
        lambda *a, **k: {"results": [{"url": "https://tavily.example.com"}]},
    )
    url = research_search.find_official_website("Acme", "serper-key", "serp-key", "tavily-key")
    assert url == "https://tavily.example.com"


def test_find_official_website_returns_none_when_all_providers_fail(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setattr(research_search, "_serper_request", _boom)
    monkeypatch.setattr(research_search, "_serpapi_request", _boom)
    monkeypatch.setattr(research_search, "_tavily_request", _boom)
    assert research_search.find_official_website("Acme", "serper-key", "serp-key", "tavily-key") is None


def test_find_official_website_returns_none_without_any_keys():
    assert research_search.find_official_website("Acme", None, None, None) is None


def test_find_official_website_skips_providers_with_no_key(monkeypatch):
    monkeypatch.setattr(
        research_search, "_serpapi_request",
        lambda *a, **k: {"organic_results": [{"link": "https://serpapi.example.com"}]},
    )
    url = research_search.find_official_website("Acme", None, "serp-key", None)
    assert url == "https://serpapi.example.com"


def test_find_official_website_returns_none_on_empty_results(monkeypatch):
    monkeypatch.setattr(research_search, "_serper_request", lambda *a, **k: {"organic": []})
    assert research_search.find_official_website("Acme", "serper-key", None, None) is None


# --- .env loading -----------------------------------------------------------


def _write_env(tmp_path, body):
    env_path = tmp_path / ".env"
    env_path.write_text(body, encoding="utf-8")
    return env_path


def test_load_env_file_sets_values_from_file(tmp_path, monkeypatch):
    env_path = _write_env(tmp_path, "BEACON_TEST_KEY=from-file\n")
    monkeypatch.setattr(research_search, "ENV_FILE_PATHS", (env_path,))
    monkeypatch.setattr(research_search, "_ENV_VALUES_FROM_FILE", {})
    monkeypatch.delenv("BEACON_TEST_KEY", raising=False)

    research_search._load_env_file()
    assert __import__("os").environ["BEACON_TEST_KEY"] == "from-file"


def test_load_env_file_refreshes_a_rotated_value(tmp_path, monkeypatch):
    """Editing .env (rotating a key) must take effect without a process restart."""
    env_path = _write_env(tmp_path, "BEACON_TEST_KEY=old-key\n")
    monkeypatch.setattr(research_search, "ENV_FILE_PATHS", (env_path,))
    monkeypatch.setattr(research_search, "_ENV_VALUES_FROM_FILE", {})
    monkeypatch.delenv("BEACON_TEST_KEY", raising=False)

    research_search._load_env_file()
    env_path.write_text("BEACON_TEST_KEY=new-key\n", encoding="utf-8")
    research_search._load_env_file()

    assert __import__("os").environ["BEACON_TEST_KEY"] == "new-key"


def test_load_env_file_does_not_override_a_shell_exported_value(tmp_path, monkeypatch):
    env_path = _write_env(tmp_path, "BEACON_TEST_KEY=from-file\n")
    monkeypatch.setattr(research_search, "ENV_FILE_PATHS", (env_path,))
    monkeypatch.setattr(research_search, "_ENV_VALUES_FROM_FILE", {})
    monkeypatch.setenv("BEACON_TEST_KEY", "from-shell")

    research_search._load_env_file()
    assert __import__("os").environ["BEACON_TEST_KEY"] == "from-shell"


def test_load_env_file_reads_the_repo_root_env():
    """The repo's .env lives one level above india-trend-radar/."""
    assert research_search.REPO_ROOT_DIR / ".env" in research_search.ENV_FILE_PATHS


# --- official-website result validation -------------------------------------


def test_find_official_website_skips_aggregator_profiles(monkeypatch):
    """The top hit is often a PitchBook/LinkedIn profile -- reading that page yields
    no sector signal, so prefer the company's own site further down the results."""
    monkeypatch.setattr(
        research_search, "_serper_request",
        lambda *a, **k: {"organic": [
            {"link": "https://pitchbook.com/profiles/investor/541193-23"},
            {"link": "https://in.linkedin.com/company/12-flags"},
            {"link": "https://www.12flags.com/"},
        ]},
    )
    url = research_search.find_official_website("12flags", "serper-key", None, None)
    assert url == "https://www.12flags.com/"


def test_find_official_website_prefers_a_domain_matching_the_company_name(monkeypatch):
    monkeypatch.setattr(
        research_search, "_serper_request",
        lambda *a, **k: {"organic": [
            {"link": "https://someblog.com/12flags-review"},
            {"link": "https://www.12flags.com/"},
        ]},
    )
    url = research_search.find_official_website("12flags", "serper-key", None, None)
    assert url == "https://www.12flags.com/"


def test_find_official_website_falls_back_to_next_provider_when_all_hits_are_aggregators(monkeypatch):
    """Serper answering with only aggregator links must not end the search."""
    monkeypatch.setattr(
        research_search, "_serper_request",
        lambda *a, **k: {"organic": [{"link": "https://www.crunchbase.com/organization/acme"}]},
    )
    monkeypatch.setattr(
        research_search, "_serpapi_request",
        lambda *a, **k: {"organic_results": [{"link": "https://acme.com"}]},
    )
    url = research_search.find_official_website("Acme", "serper-key", "serp-key", None)
    assert url == "https://acme.com"


def test_find_official_website_uses_tavily_when_serper_and_serpapi_yield_nothing_usable(monkeypatch):
    monkeypatch.setattr(
        research_search, "_serper_request",
        lambda *a, **k: {"organic": [{"link": "https://www.linkedin.com/company/acme"}]},
    )
    monkeypatch.setattr(research_search, "_serpapi_request", lambda *a, **k: {"organic_results": []})
    monkeypatch.setattr(
        research_search, "_tavily_request",
        lambda *a, **k: {"results": [{"url": "https://acme.com"}]},
    )
    url = research_search.find_official_website("Acme", "serper-key", "serp-key", "tavily-key")
    assert url == "https://acme.com"


def test_find_official_website_returns_none_when_only_aggregators_are_found(monkeypatch):
    """Better to say 'we couldn't find their website' than to read the wrong page."""
    monkeypatch.setattr(
        research_search, "_serper_request",
        lambda *a, **k: {"organic": [{"link": "https://www.linkedin.com/company/acme"}]},
    )
    assert research_search.find_official_website("Acme", "serper-key", None, None) is None


def test_load_env_file_does_not_override_a_value_set_at_runtime(tmp_path, monkeypatch):
    """Once something else assigns the variable, the file stops overwriting it --
    this is what lets tests blank out a key without .env restoring it."""
    env_path = _write_env(tmp_path, "BEACON_TEST_KEY=from-file\n")
    monkeypatch.setattr(research_search, "ENV_FILE_PATHS", (env_path,))
    monkeypatch.setattr(research_search, "_ENV_VALUES_FROM_FILE", {})
    monkeypatch.delenv("BEACON_TEST_KEY", raising=False)

    research_search._load_env_file()
    monkeypatch.setenv("BEACON_TEST_KEY", "")
    research_search._load_env_file()

    assert __import__("os").environ["BEACON_TEST_KEY"] == ""


# --- build_research_context provider chain ----------------------------------


def _chain_stubs(monkeypatch, tmp_path, serper, serpapi, tavily):
    """Installs provider stubs that record their calls. Each stub is (called_list, fn)."""
    calls = []

    def _make(name, behaviour):
        def _stub(*a, **k):
            calls.append(name)
            if isinstance(behaviour, Exception):
                raise behaviour
            return behaviour
        return _stub

    monkeypatch.setattr(research_search, "_serper_request", _make("serper", serper))
    monkeypatch.setattr(research_search, "_serpapi_request", _make("serpapi", serpapi))
    monkeypatch.setattr(research_search, "_tavily_request", _make("tavily", tavily))
    monkeypatch.setattr(research_search, "DEFAULT_OUTPUT_DIR", tmp_path / "research")
    monkeypatch.setattr(research_search, "ROOT_DIR", tmp_path)  # keeps output_path.relative_to happy
    return calls


_HIT = {"organic": [{"title": "T", "link": "https://example.com", "snippet": "s"}]}
_HIT_SERPAPI = {"organic_results": [{"title": "T", "link": "https://example.com", "snippet": "s"}]}
_HIT_TAVILY = {"results": [{"title": "T", "url": "https://example.com", "content": "s"}]}
_DOWN = RuntimeError("provider down")


def test_research_context_falls_back_to_tavily_when_serper_and_serpapi_fail(tmp_path, monkeypatch):
    calls = _chain_stubs(monkeypatch, tmp_path, _DOWN, _DOWN, _HIT_TAVILY)
    ctx = research_search.build_research_context(
        "Apparel", "United States", "Past 1 week",
        serper_api_key="a", serp_api_key="b", tavily_api_key="c", report_dir=tmp_path / "reports",
    )
    assert calls == ["serper", "serpapi", "tavily"]
    assert ctx.providers_used == ["tavily"]
    assert ctx.hits


def test_research_context_does_not_call_tavily_when_serpapi_succeeds(tmp_path, monkeypatch):
    """Tavily is priority 3 -- burning its quota after SerpApi already answered is waste."""
    calls = _chain_stubs(monkeypatch, tmp_path, _DOWN, _HIT_SERPAPI, _HIT_TAVILY)
    ctx = research_search.build_research_context(
        "Apparel", "United States", "Past 1 week",
        serper_api_key="a", serp_api_key="b", tavily_api_key="c", report_dir=tmp_path / "reports",
    )
    assert calls == ["serper", "serpapi"]
    assert ctx.providers_used == ["serpapi"]


def test_research_context_stops_at_serper_when_it_succeeds(tmp_path, monkeypatch):
    calls = _chain_stubs(monkeypatch, tmp_path, _HIT, _HIT_SERPAPI, _HIT_TAVILY)
    research_search.build_research_context(
        "Apparel", "United States", "Past 1 week",
        serper_api_key="a", serp_api_key="b", tavily_api_key="c", report_dir=tmp_path / "reports",
    )
    assert calls == ["serper"]


def test_research_context_china_falls_back_serper_then_tavily(tmp_path, monkeypatch):
    calls = _chain_stubs(monkeypatch, tmp_path, _DOWN, _DOWN, _HIT_TAVILY)
    monkeypatch.setattr(research_search, "_serpapi_knowledge_graph_request", lambda *a, **k: {})
    monkeypatch.setattr(research_search, "_serpapi_baidu_request", lambda *a, **k: (_ for _ in ()).throw(_DOWN))
    ctx = research_search.build_research_context(
        "Apparel", "China", "Past 1 week",
        serper_api_key="a", serp_api_key="b", tavily_api_key="c", report_dir=tmp_path / "reports",
    )
    assert calls[-1] == "tavily"
    assert ctx.providers_used == ["tavily"]
