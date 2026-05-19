#!/usr/bin/env python3
"""Query and validate iPSX2 compatibility presets."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PRESETS_PATH = ROOT / "compatibility" / "presets.json"
GRAPHICS_FIXES_PATH = ROOT / "compatibility" / "graphics_fixes.json"

REQUIRED_PROFILE_FIELDS = {
    "id",
    "title",
    "issue_refs",
    "affected_games",
    "symptoms",
    "status",
    "settings",
    "implementation_notes",
    "user_steps",
}

REQUIRED_GRAPHICS_FIX_FIELDS = {
    "id",
    "title",
    "issue_refs",
    "games",
    "symptoms",
    "classification",
    "priority",
    "renderer_actions",
    "implementation_patch_plan",
    "user_steps",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_presets(path: Path = PRESETS_PATH) -> dict[str, Any]:
    return load_json(path)


def load_graphics_fixes(path: Path = GRAPHICS_FIXES_PATH) -> dict[str, Any]:
    return load_json(path)


def validate_presets(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("version") != 1:
        errors.append("version must be 1")
    profiles = data.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        errors.append("profiles must be a non-empty list")
        return errors

    seen_ids: set[str] = set()
    for index, profile in enumerate(profiles):
        if not isinstance(profile, dict):
            errors.append(f"profiles[{index}] must be an object")
            continue

        missing = sorted(REQUIRED_PROFILE_FIELDS - profile.keys())
        if missing:
            errors.append(f"{profile.get('id', f'profiles[{index}]')} missing fields: {', '.join(missing)}")

        profile_id = profile.get("id")
        if not isinstance(profile_id, str) or not profile_id.strip():
            errors.append(f"profiles[{index}] has an invalid id")
        elif profile_id in seen_ids:
            errors.append(f"duplicate profile id: {profile_id}")
        else:
            seen_ids.add(profile_id)

        for field in ("issue_refs", "affected_games", "symptoms", "implementation_notes", "user_steps"):
            if field in profile and (not isinstance(profile[field], list) or not profile[field]):
                errors.append(f"{profile_id}.{field} must be a non-empty list")

        if "issue_refs" in profile and not all(isinstance(issue, int) for issue in profile["issue_refs"]):
            errors.append(f"{profile_id}.issue_refs must contain integers")
        if "settings" in profile and not isinstance(profile["settings"], dict):
            errors.append(f"{profile_id}.settings must be an object")

    return errors


def validate_graphics_fixes(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("version") != 1:
        errors.append("graphics fixes version must be 1")
    fixes = data.get("fixes")
    if not isinstance(fixes, list) or not fixes:
        errors.append("fixes must be a non-empty list")
        return errors

    seen_ids: set[str] = set()
    for index, fix in enumerate(fixes):
        if not isinstance(fix, dict):
            errors.append(f"fixes[{index}] must be an object")
            continue

        missing = sorted(REQUIRED_GRAPHICS_FIX_FIELDS - fix.keys())
        if missing:
            errors.append(f"{fix.get('id', f'fixes[{index}]')} missing fields: {', '.join(missing)}")

        fix_id = fix.get("id")
        if not isinstance(fix_id, str) or not fix_id.strip():
            errors.append(f"fixes[{index}] has an invalid id")
        elif fix_id in seen_ids:
            errors.append(f"duplicate graphics fix id: {fix_id}")
        else:
            seen_ids.add(fix_id)

        for field in ("issue_refs", "games", "symptoms", "implementation_patch_plan", "user_steps"):
            if field in fix and (not isinstance(fix[field], list) or not fix[field]):
                errors.append(f"{fix_id}.{field} must be a non-empty list")

        if "issue_refs" in fix and not all(isinstance(issue, int) for issue in fix["issue_refs"]):
            errors.append(f"{fix_id}.issue_refs must contain integers")
        if "renderer_actions" in fix and not isinstance(fix["renderer_actions"], dict):
            errors.append(f"{fix_id}.renderer_actions must be an object")
        if "priority" in fix and fix["priority"] not in {"low", "medium", "high"}:
            errors.append(f"{fix_id}.priority must be low, medium, or high")

    return errors


def normalize(value: Any) -> str:
    return str(value).casefold()


def profile_matches(profile: dict[str, Any], query: str) -> bool:
    return record_matches(profile, query)


def record_matches(record: dict[str, Any], query: str) -> bool:
    haystack = json.dumps(record, ensure_ascii=False).casefold()
    return query.casefold() in haystack


def render_graphics_fix(fix: dict[str, Any]) -> str:
    lines = [
        f"# {fix['title']}",
        f"ID: {fix['id']}",
        f"Priority: {fix['priority']}",
        f"Classification: {fix['classification']}",
        "Issues: " + ", ".join(f"#{issue}" for issue in fix["issue_refs"]),
        "Games: " + ", ".join(fix["games"]),
        "",
        "Symptoms:",
    ]
    lines.extend(f"- {symptom}" for symptom in fix["symptoms"])
    lines.extend(["", "Renderer / accuracy actions:", json.dumps(fix["renderer_actions"], ensure_ascii=False, indent=2, sort_keys=True)])
    lines.extend(["", "Implementation patch plan:"])
    lines.extend(f"{number}. {step}" for number, step in enumerate(fix["implementation_patch_plan"], start=1))
    lines.extend(["", "User steps:"])
    lines.extend(f"{number}. {step}" for number, step in enumerate(fix["user_steps"], start=1))
    return "\n".join(lines)


def render_profile(profile: dict[str, Any]) -> str:
    lines = [
        f"# {profile['title']}",
        f"ID: {profile['id']}",
        f"Status: {profile['status']}",
        "Issues: " + ", ".join(f"#{issue}" for issue in profile["issue_refs"]),
        "Games: " + ", ".join(profile["affected_games"]),
        "",
        "Symptoms:",
    ]
    lines.extend(f"- {symptom}" for symptom in profile["symptoms"])
    lines.extend(["", "Recommended user steps:"])
    lines.extend(f"{number}. {step}" for number, step in enumerate(profile["user_steps"], start=1))
    lines.extend(["", "Settings:", json.dumps(profile["settings"], ensure_ascii=False, indent=2, sort_keys=True)])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("validate", help="validate compatibility/presets.json and compatibility/graphics_fixes.json")

    list_parser = subcommands.add_parser("list", help="list all profile IDs and titles")
    list_parser.add_argument("--issue", type=int, help="filter by upstream issue number")

    show_parser = subcommands.add_parser("show", help="show the profile matching an ID")
    show_parser.add_argument("profile_id")

    search_parser = subcommands.add_parser("search", help="search profiles by game, symptom, or setting text")
    search_parser.add_argument("query")

    graphics_list_parser = subcommands.add_parser("graphics-list", help="list graphics fixes")
    graphics_list_parser.add_argument("--issue", type=int, help="filter by upstream issue number")

    graphics_show_parser = subcommands.add_parser("graphics-show", help="show a graphics fix by ID")
    graphics_show_parser.add_argument("fix_id")

    graphics_search_parser = subcommands.add_parser("graphics-search", help="search graphics fixes")
    graphics_search_parser.add_argument("query")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    data = load_presets()
    graphics_data = load_graphics_fixes()
    errors = validate_presets(data) + validate_graphics_fixes(graphics_data)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    profiles: list[dict[str, Any]] = data["profiles"]
    graphics_fixes: list[dict[str, Any]] = graphics_data["fixes"]
    if args.command == "validate":
        print(f"OK: {len(profiles)} compatibility profiles and {len(graphics_fixes)} graphics fixes validated")
        return 0

    if args.command == "list":
        for profile in profiles:
            if args.issue is not None and args.issue not in profile["issue_refs"]:
                continue
            print(f"{profile['id']} - {profile['title']}")
        return 0

    if args.command == "show":
        for profile in profiles:
            if profile["id"] == args.profile_id:
                print(render_profile(profile))
                return 0
        print(f"error: no profile found for id {args.profile_id!r}", file=sys.stderr)
        return 2

    if args.command == "search":
        matches = [profile for profile in profiles if profile_matches(profile, args.query)]
        if not matches:
            print(f"No profiles matched {args.query!r}")
            return 1
        for profile in matches:
            print(f"{profile['id']} - {profile['title']}")
        return 0

    if args.command == "graphics-list":
        for fix in graphics_fixes:
            if args.issue is not None and args.issue not in fix["issue_refs"]:
                continue
            print(f"{fix['id']} - {fix['title']}")
        return 0

    if args.command == "graphics-show":
        for fix in graphics_fixes:
            if fix["id"] == args.fix_id:
                print(render_graphics_fix(fix))
                return 0
        print(f"error: no graphics fix found for id {args.fix_id!r}", file=sys.stderr)
        return 2

    if args.command == "graphics-search":
        matches = [fix for fix in graphics_fixes if record_matches(fix, args.query)]
        if not matches:
            print(f"No graphics fixes matched {args.query!r}")
            return 1
        for fix in matches:
            print(f"{fix['id']} - {fix['title']}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
