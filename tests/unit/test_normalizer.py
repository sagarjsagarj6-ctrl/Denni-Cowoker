from dynamic_agents.input.envelope import make_envelope
from dynamic_agents.input.normalizer import InputNormalizer


def test_text_and_json_are_normalized(settings, tmp_path) -> None:
    path = tmp_path / "evidence.json"
    path.write_text('{"risk": "thermal"}', encoding="utf-8")
    normalized = InputNormalizer(settings).normalize(make_envelope("analyze", [str(path)]))
    assert normalized.text == "analyze"
    assert normalized.evidence[0].checksum_sha256
    assert '"risk": "thermal"' in normalized.evidence[0].extracted_text
