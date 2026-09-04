from app.agent.agent import detect_intent


def test_default_routes_to_qa():
    assert detect_intent("What did the pricing episode say about packaging?", "auto") == "qa"


def test_ship30_keyword_routes_to_ship30():
    assert detect_intent("Can you write a ship 30 for 30 essay about activation?", "auto") == "ship30"


def test_artifact_keyword_routes_to_artifact():
    assert detect_intent("Please generate a markdown doc summarizing this", "auto") == "artifact"


def test_explicit_skill_overrides_keyword_detection():
    assert detect_intent("write a ship 30 essay", "qa") == "qa"


def test_html_artifact_request_detected_by_agent_handler_kind_logic():
    # kind selection happens in agent.handle_turn; this locks the keyword contract
    from app.agent.agent import ARTIFACT_KEYWORDS

    assert any("artifact" in k for k in ARTIFACT_KEYWORDS)
