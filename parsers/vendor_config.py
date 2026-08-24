from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

VendorMatchSource = Literal["hint", "sender", "text"] | None

_PROFILE_CACHE: dict[Path, tuple[float, list[VendorProfile]]] = {}


@dataclass(frozen=True)
class VendorClassification:
    vendor_profile: str | None
    match_source: VendorMatchSource = None
    ambiguous: bool = False
    warnings: tuple[str, ...] = ()


@dataclass
class VendorProfile:
    vendor_category: str
    classification: VendorClassificationRules = field(
        default_factory=lambda: VendorClassificationRules()
    )


@dataclass
class VendorClassificationRules:
    text_keywords: list[str] = field(default_factory=list)
    filename_slugs: list[str] = field(default_factory=list)
    require_keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)
    sender_domains: list[str] = field(default_factory=list)


def default_vendors_dir() -> Path:
    return Path(__file__).resolve().parent / "vendors"


def load_vendor_profiles(vendors_dir: Path | None = None) -> list[VendorProfile]:
    root = vendors_dir or default_vendors_dir()
    if not root.is_dir():
        return []

    mtime = max((p.stat().st_mtime for p in root.glob("*.yaml")), default=0.0)
    cached = _PROFILE_CACHE.get(root)
    if cached and cached[0] == mtime:
        return cached[1]

    profiles: list[VendorProfile] = []
    for path in sorted(root.glob("*.yaml")):
        profile = _load_profile_file(path)
        if profile is not None:
            profiles.append(profile)

    _PROFILE_CACHE[root] = (mtime, profiles)
    return profiles


def classify_vendor(
    text: str,
    *,
    filename: str | None = None,
    sender: str | None = None,
    hint: str | None = None,
    vendors_dir: Path | None = None,
) -> VendorClassification:
    profiles = load_vendor_profiles(vendors_dir)

    if hint:
        hint = hint.strip()
        if not hint:
            return VendorClassification(vendor_profile=None, match_source="hint")
        known = {p.vendor_category for p in profiles}
        warnings: tuple[str, ...] = ()
        if hint not in known:
            warnings = ("vendor_profile_unknown",)
        return VendorClassification(
            vendor_profile=hint,
            match_source="hint",
            warnings=warnings,
        )

    by_sender = _classify_by_sender(sender, profiles)
    if by_sender is not None:
        return by_sender

    return _classify_by_content(text, filename, profiles)


def extract_email(from_header: str) -> str:
    raw = str(from_header or "")
    angle = re.search(r"<([^>]+)>", raw)
    candidate = (angle.group(1) if angle else raw).strip().lower()
    match = re.search(r"[^\s<>]+@[^\s<>]+", candidate)
    return match.group(0) if match else candidate


def _load_profile_file(path: Path) -> VendorProfile | None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None

    category = data.get("vendor_category")
    if not category:
        return None

    cls = data.get("classification") or {}
    if not isinstance(cls, dict):
        cls = {}

    rules = VendorClassificationRules(
        text_keywords=_as_str_list(cls.get("text_keywords")),
        filename_slugs=_as_str_list(cls.get("filename_slugs")),
        require_keywords=_as_str_list(cls.get("require_keywords")),
        exclude_keywords=_as_str_list(cls.get("exclude_keywords")),
        sender_domains=_as_str_list(cls.get("sender_domains")),
    )
    return VendorProfile(vendor_category=str(category), classification=rules)


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def _sender_domain_matches(email: str, domain_rule: str) -> bool:
    rule = domain_rule.strip().lower()
    if not rule:
        return False
    if rule.startswith("@"):
        return email.endswith(rule)
    return email == rule


def _classify_by_sender(
    sender: str | None,
    profiles: list[VendorProfile],
) -> VendorClassification | None:
    if not sender:
        return None

    email = extract_email(sender)
    matches = [
        profile.vendor_category
        for profile in profiles
        for domain_rule in profile.classification.sender_domains
        if _sender_domain_matches(email, domain_rule)
    ]

    if not matches:
        return None
    if len(set(matches)) > 1:
        return VendorClassification(vendor_profile=None, match_source="sender", ambiguous=True)
    return VendorClassification(vendor_profile=matches[0], match_source="sender")


def _classify_by_content(
    text: str,
    filename: str | None,
    profiles: list[VendorProfile],
) -> VendorClassification:
    scored: list[tuple[int, str]] = []
    for profile in profiles:
        score = _score_profile(text, filename, profile)
        if score is not None:
            scored.append((score, profile.vendor_category))

    if not scored:
        return VendorClassification(vendor_profile=None)

    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best_category = scored[0]
    if len(scored) > 1 and scored[1][0] == best_score:
        return VendorClassification(vendor_profile=None, match_source="text", ambiguous=True)
    return VendorClassification(vendor_profile=best_category, match_source="text")


def _score_profile(
    text: str,
    filename: str | None,
    profile: VendorProfile,
) -> int | None:
    rules = profile.classification
    haystack = text or ""
    lower = haystack.lower()

    for keyword in rules.exclude_keywords:
        if keyword.lower() in lower:
            return None

    for keyword in rules.require_keywords:
        if keyword.lower() not in lower:
            return None

    score = 0
    text_hit = False
    for keyword in rules.text_keywords:
        if keyword.lower() in lower:
            score += 1
            text_hit = True

    filename_hit = False
    if filename:
        fn_lower = filename.lower()
        for slug in rules.filename_slugs:
            if slug.lower() in fn_lower:
                score += 2
                filename_hit = True
                break

    if not text_hit and not filename_hit:
        return None
    return score
