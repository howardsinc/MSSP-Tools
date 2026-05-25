"""FortiAIGate scanner-stage builders.

Ports the inputGuard/outputGuard JSON construction from
`api/examples/05-onboard-tenant.sh` (verified shape, dumped from the live
`claude-anthropic-guard` on 2026-05-19).

Each stage has the shape:
    {name: <scanner>, processors: [{name: <scanner>, params: {...}}], selectors: null}

Action values:
    "alert"        log to UI, traffic continues to LLM
    "alert&deny"   log to UI AND block the request at the gateway

A "policy preset" maps to a tuple (action_pi, action_dlp, action_tox) plus
which scanners are enabled. Custom policies pass in explicit per-scanner
toggles.
"""

from typing import Literal

PolicyPreset = Literal["alert", "strict-block", "custom"]


DLP_ENTITY_TYPES = {
    "general": ["DATE_TIME", "IP_ADDRESS"],
    "global_finance": ["URL", "IBAN_CODE"],
    "national_ids": ["US_PASSPORT", "US_ITIN", "US_SSN", "US_BANK_NUMBER"],
    "personal_info": ["EMAIL_ADDRESS", "MEDICAL_LICENSE", "CREDIT_CARD"],
}

DLP_PREAMBLE = (
    "In the following prompt, I am going to remove certain information and "
    "replace each instance with sequentially-numbered placeholders in ALL "
    "CAPS (e.g. [REDACTED_NAME_1]). Please ignore these placeholders and "
    "respond as if you were receiving a normal prompt.\n\nPrompt: "
)


def _resolve_actions(policy: PolicyPreset, custom: dict | None = None) -> dict:
    """Return action values for PI, DLP, TOX based on policy."""
    if policy == "alert":
        return {"pi": "alert", "dlp": "alert", "tox": "alert"}
    if policy == "strict-block":
        return {"pi": "alert&deny", "dlp": "alert&deny", "tox": "alert"}
    if policy == "custom" and custom:
        return {
            "pi": custom.get("action_pi", "alert"),
            "dlp": custom.get("action_dlp", "alert"),
            "tox": custom.get("action_tox", "alert"),
        }
    raise ValueError(f"Unknown policy: {policy}")


def _resolve_enabled(policy: PolicyPreset, custom: dict | None = None) -> dict:
    """Return enabled flags for each optional scanner."""
    base = {
        "promptInjection": True,
        "dataLeak": True,
        "toxicity": True,
        "customRule": False,
        "language": False,
        "code": False,
        "banTopics": False,
        "tokenLimit": False,
        "maliciousURL": False,
    }
    if policy == "custom" and custom and "enabled" in custom:
        base.update(custom["enabled"])
    return base


def build_input_guard(policy: PolicyPreset, custom: dict | None = None) -> list:
    a = _resolve_actions(policy, custom)
    en = _resolve_enabled(policy, custom)

    tox_subs = {
        sub: {"enabled": True, "threshold": 0.85, "action": a["tox"]}
        for sub in ["toxicity", "severeToxicity", "obscene", "threat",
                    "identityAttack", "sexualExplict", "insult"]
    }

    return [
        {"name": "promptInjection", "processors": [{"name": "promptInjection",
            "params": {"enabled": en["promptInjection"], "advancedMode": False,
                       "threshold": 0.85, "action": a["pi"],
                       "assistantScan": False, "systemScan": False}}],
         "selectors": None},
        {"name": "dataLeak", "processors": [{"name": "dataLeak",
            "params": {"enabled": en["dataLeak"], "advancedMode": False,
                       "action": a["dlp"], "threshold": 0.85,
                       "entityTypes": DLP_ENTITY_TYPES,
                       "preamble": DLP_PREAMBLE}}],
         "selectors": None},
        {"name": "toxicity", "processors": [{"name": "toxicity",
            "params": {"enabled": en["toxicity"], "advancedMode": False,
                       **tox_subs,
                       "assistantScan": False, "systemScan": False}}],
         "selectors": None},
        {"name": "customRule", "processors": [{"name": "customRule",
            "params": {"enabled": en["customRule"], "rules": []}}],
         "selectors": None},
        {"name": "language", "processors": [{"name": "language",
            "params": {"enabled": en["language"],
                       "targetLanguages": ["chinese", "japanese"],
                       "mode": "allow", "action": "alert", "threshold": 0.85}}],
         "selectors": None},
        {"name": "code", "processors": [{"name": "code",
            "params": {"enabled": en["code"], "action": "alert", "threshold": 0.85}}],
         "selectors": None},
        {"name": "banTopics", "processors": [{"name": "banTopics",
            "params": {"enabled": en["banTopics"], "topics": [],
                       "action": "alert", "threshold": 0.85}}],
         "selectors": None},
        {"name": "tokenLimit", "processors": [{"name": "tokenLimit",
            "params": {"enabled": en["tokenLimit"], "action": "alert",
                       "promptTokenLimit": 120,
                       "clientRateLimit": {"tokens": 1000, "windowSeconds": 10},
                       "globalRateLimit": {"tokens": 1000, "windowSeconds": 10}}}],
         "selectors": None},
    ]


def build_output_guard(policy: PolicyPreset, custom: dict | None = None) -> list:
    a = _resolve_actions(policy, custom)
    en = _resolve_enabled(policy, custom)

    tox_subs = {
        sub: {"enabled": True, "threshold": 0.85, "action": a["tox"]}
        for sub in ["toxicity", "severeToxicity", "obscene", "threat",
                    "identityAttack", "sexualExplict", "insult"]
    }

    return [
        {"name": "dataLeak", "processors": [{"name": "dataLeak",
            "params": {"enabled": en["dataLeak"], "advancedMode": False,
                       "action": a["dlp"], "threshold": 0.85,
                       "entityTypes": DLP_ENTITY_TYPES}}],
         "selectors": None},
        {"name": "toxicity", "processors": [{"name": "toxicity",
            "params": {"enabled": en["toxicity"], "advancedMode": False, **tox_subs}}],
         "selectors": None},
        {"name": "customRule", "processors": [{"name": "customRule",
            "params": {"enabled": en["customRule"], "rules": []}}],
         "selectors": None},
        {"name": "maliciousURL", "processors": [{"name": "maliciousURL",
            "params": {"enabled": en["maliciousURL"], "action": "alert",
                       "threshold": 0.85,
                       "monitorTypes": {"defacement": True, "malware": True, "phishing": True}}}],
         "selectors": None},
        {"name": "language", "processors": [{"name": "language",
            "params": {"enabled": en["language"],
                       "targetLanguages": ["chinese", "japanese"],
                       "mode": "allow", "action": "alert", "threshold": 0.85}}],
         "selectors": None},
        {"name": "code", "processors": [{"name": "code",
            "params": {"enabled": en["code"], "action": "alert", "threshold": 0.85}}],
         "selectors": None},
        {"name": "tokenLimit", "processors": [{"name": "tokenLimit",
            "params": {"enabled": en["tokenLimit"], "action": "alert",
                       "tokenLimit": 110,
                       "clientRateLimit": {"tokens": 900, "windowSeconds": 1},
                       "globalRateLimit": {"tokens": 900, "windowSeconds": 1}}}],
         "selectors": None},
    ]


SCANNER_INFO = {
    "promptInjection": {
        "label": "Prompt Injection",
        "owasp": "LLM01",
        "description": "Detects jailbreak attempts and instructions that try to override the system prompt.",
    },
    "dataLeak": {
        "label": "Data Leak / DLP",
        "owasp": "LLM02 / LLM06",
        "description": "Detects PII (SSN, credit cards, medical license, passport, emails, IPs, etc.) in prompts and responses.",
    },
    "toxicity": {
        "label": "Toxicity",
        "owasp": "LLM06",
        "description": "Flags toxic, obscene, threatening, or hateful content (7 sub-classifiers).",
    },
    "customRule": {
        "label": "Custom Rules",
        "owasp": "LLM07 / LLM08 / LLM10",
        "description": "Customer-defined allow/deny lists. Regex support targeted for a future release per PM session 2026-05-13.",
    },
    "language": {
        "label": "Language Filter",
        "owasp": "—",
        "description": "Allow/deny prompts by detected language (e.g. block non-English).",
    },
    "code": {
        "label": "Code Detection",
        "owasp": "LLM02",
        "description": "Detects code in prompts/responses (useful when customer policy forbids code generation).",
    },
    "banTopics": {
        "label": "Banned Topics",
        "owasp": "LLM07",
        "description": "Detects whether the prompt is about a banned topic.",
    },
    "tokenLimit": {
        "label": "Token Limit / Rate Limit",
        "owasp": "LLM04",
        "description": "Caps tokens per request and rate-limits per client/global.",
    },
    "maliciousURL": {
        "label": "Malicious URL",
        "owasp": "LLM05",
        "description": "Scans response URLs for defacement, malware, and phishing (output-only).",
    },
}
