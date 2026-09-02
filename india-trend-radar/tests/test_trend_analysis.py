"""Tests for engine/trend_analysis.py share-upload behavior."""

from engine import trend_analysis


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self) -> None:
        return None


def test_upload_public_pdf_returns_public_url(monkeypatch):
    def fake_post(*args, **kwargs):
        assert args[0] == "https://0x0.st"
        assert kwargs["files"]["file"][0].endswith(".pdf")
        assert kwargs["files"]["file"][2] == "application/pdf"
        return _FakeResponse("https://0x0.st/abcd.pdf\n")

    monkeypatch.setattr(trend_analysis.requests, "post", fake_post)

    url = trend_analysis._upload_public_pdf(b"%PDF-1.4 test", "report.pdf")

    assert url == "https://0x0.st/abcd.pdf"


def test_upload_public_pdf_returns_none_on_bad_response(monkeypatch):
    def fake_post(*args, **kwargs):
        return _FakeResponse("not a url")

    monkeypatch.setattr(trend_analysis.requests, "post", fake_post)
    monkeypatch.setattr(trend_analysis.requests, "put", fake_post)

    assert trend_analysis._upload_public_pdf(b"pdf-bytes", "report.pdf") is None
