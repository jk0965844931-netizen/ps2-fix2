from tools.compatibility import (
    load_graphics_fixes,
    load_presets,
    profile_matches,
    record_matches,
    validate_graphics_fixes,
    validate_presets,
)


def test_presets_are_valid():
    data = load_presets()
    assert validate_presets(data) == []


def test_graphics_fixes_are_valid():
    data = load_graphics_fixes()
    assert validate_graphics_fixes(data) == []


def test_profiles_cover_reviewed_upstream_issues():
    data = load_presets()
    covered = {issue for profile in data["profiles"] for issue in profile["issue_refs"]}
    assert {38, 39, 40, 41, 42, 43, 44, 46}.issubset(covered)


def test_graphics_fixes_cover_visual_issues():
    data = load_graphics_fixes()
    covered = {issue for fix in data["fixes"] for issue in fix["issue_refs"]}
    assert {39, 41, 42, 49, 50}.issubset(covered)


def test_god_of_war_fix_enforces_framebuffer_accuracy():
    data = load_graphics_fixes()
    gow = next(fix for fix in data["fixes"] if fix["id"] == "gow-hit-flash-framebuffer-feedback")
    safe_profile = gow["renderer_actions"]["safe_profile"]
    assert safe_profile["accurate_destination_alpha"] is True
    assert safe_profile["texture_barrier_or_framebuffer_fetch"] is True
    assert "framebuffer" in gow["classification"]


def test_search_matches_game_names_and_issue_context():
    data = load_presets()
    profiles = data["profiles"]
    assert any(profile_matches(profile, "Need for Speed") for profile in profiles)
    assert any(profile_matches(profile, "virtual pad") for profile in profiles)


def test_graphics_search_matches_visual_symptoms():
    data = load_graphics_fixes()
    fixes = data["fixes"]
    assert any(record_matches(fix, "God of War") for fix in fixes)
    assert any(record_matches(fix, "black screen") for fix in fixes)
    assert any(record_matches(fix, "scrambled") for fix in fixes)
