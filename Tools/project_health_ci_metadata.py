#!/usr/bin/env python3
"""Generate fail-closed Project Health metadata from completed CI job results."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN_PATH = ROOT / "Docs" / "PROJECT-HEALTH-PLAN.json"
_FAILURE_RESULTS = {"failure", "cancelled", "timed_out", "action_required"}
_OWNER_ACTION_FIELDS = ("type", "action", "agent", "task_id")
_RESERVED_OWNER_ACTION_TYPES = frozenset({"approval"})
_MAX_OWNER_ACTIONS = 20
_MAX_OWNER_ACTION_FIELD_LENGTH = 240
_MAX_PLANNING_FIELD_LENGTH = 240
_MAX_BRANCH_LENGTH = 200
_MAX_CI_ID_LENGTH = 32
_MAX_REPOSITORY_LENGTH = 200
_PLAN_SCHEMA_VERSION = 4
_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
_DIGITS_RE = re.compile(r"^[0-9]+$")
_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def _value(env, key, default="unknown"):
    value = (env.get(key) or "").strip()
    return value or default


def _safe_planning_text(value):
    """Return a bounded single-line planning label or an empty string.

    Planning values are later serialized to a line-oriented env handoff. Rejecting
    embedded newlines here prevents repository variables or plan text from
    injecting additional Project Health environment keys and corrupting CI truth.
    """
    text = str(value or "").strip()
    if not text or "\n" in text or "\r" in text or len(text) > _MAX_PLANNING_FIELD_LENGTH:
        return ""
    return text


def _safe_single_line(value, *, max_length):
    """Return bounded single-line CI identity text, failing closed when malformed."""
    text = str(value or "").strip()
    if not text or "\n" in text or "\r" in text or len(text) > max_length:
        return ""
    return text


def _safe_build_sha(value):
    text = _safe_single_line(value, max_length=40)
    return text if _SHA_RE.fullmatch(text) else ""


def _safe_ci_digits(value):
    text = _safe_single_line(value, max_length=_MAX_CI_ID_LENGTH)
    return text if _DIGITS_RE.fullmatch(text) else ""


def _safe_branch(value):
    return _safe_single_line(value, max_length=_MAX_BRANCH_LENGTH)


def _safe_repository(value):
    text = _safe_single_line(value, max_length=_MAX_REPOSITORY_LENGTH)
    return text if _REPOSITORY_RE.fullmatch(text) else ""


def _result(env, key):
    """Normalize GitHub job/step results to the runtime Project Health status contract."""
    value = _value(env, key).lower()
    if value == "success":
        return "success"
    if value in _FAILURE_RESULTS:
        return "failure"
    return "unknown"


def _result_with_fallback(env, key, fallback_key):
    """Prefer exact step outcome; older workflows conservatively fall back to job result.

    A successful containing job proves its required build/test step completed. A failed
    containing job may be caused by a later screenshot/artifact step, so the fallback can
    be pessimistic but never invents a green result.
    """
    if str(env.get(key) or "").strip():
        return _result(env, key)
    return _result(env, fallback_key)


def _aggregate(results):
    values = list(results)
    if values and all(value == "success" for value in values):
        return "success"
    if any(value == "failure" for value in values):
        return "failure"
    return "unknown"


def _safe_owner_actions(value):
    """Return bounded owner-visible actions only; malformed entries are ignored."""
    if not isinstance(value, list):
        return []
    actions = []
    for raw in value[:_MAX_OWNER_ACTIONS]:
        if not isinstance(raw, dict):
            continue
        item = {}
        for key in _OWNER_ACTION_FIELDS:
            raw_value = raw.get(key)
            if not isinstance(raw_value, str):
                continue
            text = raw_value.strip()
            if not text or "\n" in text or "\r" in text or len(text) > _MAX_OWNER_ACTION_FIELD_LENGTH:
                continue
            item[key] = text
        if item.get("action"):
            item.setdefault("type", "project_action")
            if item.get("type", "").lower() in _RESERVED_OWNER_ACTION_TYPES:
                item["type"] = "project_action"
            actions.append(item)
    return actions


def _load_plan(path=DEFAULT_PLAN_PATH):
    """Load version-controlled planning facts; malformed/missing plans fail closed."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        # Planning facts are deployment evidence, not arbitrary repository text.
        # Accept only the currently reviewed schema so an older/future plan shape
        # cannot be mislabeled as trusted `version_controlled_plan` provenance.
        if data.get("schema_version") != _PLAN_SCHEMA_VERSION:
            return {}
        allowed = ("phase", "current_milestone", "next_milestone")
        plan = {}
        for key in allowed:
            value = _safe_planning_text(data.get(key, ""))
            if value:
                plan[key] = value
        owner_actions = _safe_owner_actions(data.get("owner_actions"))
        if owner_actions:
            plan["owner_actions"] = owner_actions
        return plan
    except (OSError, ValueError, TypeError):
        return {}


def _planning_value(env, env_key, plan, plan_key):
    explicit = _safe_planning_text(env.get(env_key, ""))
    if explicit:
        return explicit, "github_repository_variables"
    fallback = _safe_planning_text(plan.get(plan_key, ""))
    if fallback:
        return fallback, "version_controlled_plan"
    return "unknown", "unknown"


def _run_url(env, run_id=""):
    """Build only the canonical public GitHub Actions URL consumed by runtime validation."""
    server = _safe_single_line(env.get("GITHUB_SERVER_URL", ""), max_length=64)
    repository = _safe_repository(env.get("GITHUB_REPOSITORY", ""))
    run_id = _safe_ci_digits(run_id or env.get("GITHUB_RUN_ID", ""))
    if server == "https://github.com" and repository and run_id:
        return f"{server}/{repository}/actions/runs/{run_id}"
    return ""


def build_metadata(env=None, plan_path=DEFAULT_PLAN_PATH, generated_at=None):
    """Return truthful CI metadata; absent evidence stays unknown.

    Overall CI stays tied to whole-job outcomes. Build and test truth are recorded
    separately from the exact xcodebuild/test step outcomes when the current workflow
    supplies them, so a later screenshot failure cannot falsely report a build or test
    failure. Older workflows fall back conservatively to their containing job result.
    """
    env = os.environ if env is None else env
    jobs = {
        "backend_tests": _result(env, "JARVIS_BACKEND_TEST_RESULT"),
        "ios": _result(env, "JARVIS_IOS_RESULT"),
        "mac": _result(env, "JARVIS_MAC_RESULT"),
    }
    build_jobs = {
        "ios": _result_with_fallback(env, "JARVIS_IOS_BUILD_RESULT", "JARVIS_IOS_RESULT"),
        "mac": _result_with_fallback(env, "JARVIS_MAC_BUILD_RESULT", "JARVIS_MAC_RESULT"),
    }
    test_jobs = {
        "backend_tests": jobs["backend_tests"],
        "mac": _result_with_fallback(env, "JARVIS_MAC_TEST_RESULT", "JARVIS_MAC_RESULT"),
    }
    build_status = _aggregate(build_jobs.values())
    tests_status = _aggregate(test_jobs.values())
    build_sha = _safe_build_sha(env.get("GITHUB_SHA", ""))
    plan = _load_plan(plan_path)
    phase, phase_source = _planning_value(env, "JARVIS_CURRENT_PHASE", plan, "phase")
    current_milestone, current_source = _planning_value(
        env, "JARVIS_CURRENT_MILESTONE", plan, "current_milestone"
    )
    next_milestone, next_source = _planning_value(
        env, "JARVIS_NEXT_MILESTONE", plan, "next_milestone"
    )
    owner_actions = list(plan.get("owner_actions") or [])
    planning_sources = {phase_source, current_source, next_source}
    if planning_sources == {"github_repository_variables"}:
        milestone_source = "github_repository_variables"
    elif planning_sources == {"version_controlled_plan"}:
        milestone_source = "version_controlled_plan"
    elif "unknown" in planning_sources and len(planning_sources) == 1:
        milestone_source = "unknown"
    else:
        milestone_source = "mixed"

    generated_at = generated_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    run_id = _safe_ci_digits(env.get("GITHUB_RUN_ID", ""))
    run_number = _safe_ci_digits(env.get("GITHUB_RUN_NUMBER", ""))
    branch = _safe_branch(env.get("GITHUB_REF_NAME", ""))
    repository = _safe_repository(env.get("GITHUB_REPOSITORY", ""))
    precise_build_steps = all(str(env.get(key) or "").strip() for key in ("JARVIS_IOS_BUILD_RESULT", "JARVIS_MAC_BUILD_RESULT"))
    precise_mac_test = bool(str(env.get("JARVIS_MAC_TEST_RESULT") or "").strip())

    return {
        "build_sha": build_sha,
        "build_status": build_status,
        "ci_status": _aggregate(jobs.values()),
        "tests_status": tests_status,
        "phase": phase,
        "current_milestone": current_milestone,
        "next_milestone": next_milestone,
        "owner_actions": owner_actions,
        "ci_run_id": run_id,
        "ci_run_number": run_number,
        "ci_run_url": _run_url(env, run_id=run_id),
        "ci_branch": branch,
        "ci_repository": repository,
        "metadata_generated_at": generated_at,
        "jobs": jobs,
        "build_jobs": build_jobs"À¢'FW7Eö¦ö'2#¢FW7Eö¦ö'2À¢&Wf–FVæ6R#¢°¢&'V–ÆB#¢&v—F‡V%ö7F–öç2"–b'V–ÆE÷6†VÇ6R'Væ¶æ÷vâ"À¢&'V–ÆE÷7FGW2#¢&v—F‡V%ö7F–öç5÷7FW2"–b&V6—6Uö'V–ÆE÷7FW2VÇ6R&v—F‡V%ö7F–öç5ö¦ö'5öfÆÆ&6²"À¢&6’#¢&v—F‡V%ö7F–öç2"À¢'FW7G2#¢&v—F‡V%ö7F–öç5÷7FW2"–b&V6—6UöÖ5÷FW7BVÇ6R&v—F‡V%ö7F–öç5ö¦ö'5öfÆÆ&6²"À¢&Ö–ÆW7FöæW2#¢Ö–ÆW7FöæU÷6÷W&6RÀ¢&÷væW%ö7F–öç2#¢'fW'6–öåö6öçG&öÆÆVE÷Æâ"–b÷væW%ö7F–öç2VÇ6R'Væ¶æ÷vâ"À¢''Vâ#¢&v—F‡V%ö7F–öç2"–b'Våö–BæB&W÷6—F÷'’æB÷'Vå÷W&Â†VçbÂ'Våö–C×'Våö–B’VÇ6R'Væ¶æ÷vâ"À¢ÒÀ¢Ğ  ¦FVb÷w&—FUöVçb‡F‚ÂÖWFFF“ ¢""%w&—FRF†RW†7B6V7&WBÖg&VRVçf—&öæÖVçB¶W—26öç7VÖVB'’tUB÷&ö¦V7Bö†VÇF‚â"" ¢¦ö'2ÒÖWFFFævWB‚&¦ö'2"’÷"·Ğ¢'V–ÆEö¦ö'2ÒÖWFFFævWB‚&'V–ÆEö¦ö'2"’÷"·Ğ¢FW7Eö¦ö'2ÒÖWFFFævWB‚'FW7Eö¦ö'2"’÷"·Ğ¢÷væW%ö7F–öç5ö§6öâÒ§6öâæGV×2†ÖWFFFævWB‚&÷væW%ö7F–öç2"’÷"µÒÂVç7W&Uö66–“ÔfÇ6RÂ6W&F÷'3Ò‚"Â"Â#¢"’¢Wf–FVæ6RÒÖWFFFævWB‚&Wf–FVæ6R"’÷"·Ğ¢Æ–æW2Ò°¢b$¤%d•5ô%T”ÄEõ4„×¶ÖWFFF²v'V–ÆE÷6†u×Ò"À¢b$¤%d•5ô%T”ÄEõ5DEU3×¶ÖWFFFævWB‚v'V–ÆE÷7FGW2rÂwVæ¶æ÷vâr—Ò"À¢b$¤%d•5ô4•õ5DEU3×¶ÖWFFF²v6•÷7FGW2u×Ò"À¢b$¤%d•5õDU5E5õ5DEU3×¶ÖWFFF²wFW7G5÷7FGW2u×Ò"À¢b$¤%d•5ô5U%$TåEõ„4S×¶ÖWFFF²w†6Ru×Ò"À¢b$¤%d•5ô5U%$TåEôÔ”ÄU5DôäS×¶ÖWFFF²v7W'&VçEöÖ–ÆW7FöæRu×Ò"À¢b$¤%d•5ôäU…EôÔ”ÄU5DôäS×¶ÖWFFF²væW‡EöÖ–ÆW7FöæRu×Ò"À¢b$¤%d•5ôõtäU%ô5D”ôå5ô¥4ôã×¶÷væW%ö7F–öç5ö§6öçÒ"À¢b$¤%d•5ôÔ”ÄU5DôäUõ4õU$4S×¶Wf–FVæ6RævWBµ¥±•ÍÑ½¹•Ìœ°€Õ¹­¹½İ¸œ¥ôˆ°(€€€€€€€˜‰)IY%M}=]9I}Q%=9M}M=UIõí•Ù¥‘•¹”¹•Ğ ½İ¹•É}…Ñ¥½¹Ìœ°€Õ¹­¹½İ¸œ¥ôˆ°(€€€€€€€˜‰)IY%M}%}IU9}%õíµ•Ñ…‘…Ñ„¹•Ğ ¥}ÉÕ¹}¥œ°€œœ¥ôˆ°(€€€€€€€˜‰)IY%M}%}IU9}9U5	Hõíµ•Ñ…‘…Ñ„¹•Ğ ¥}ÉÕ¹}¹Õµ‰•Èœ°€œœ¥ôˆ°(€€€€€€€˜‰)IY%M}%}IU9}UI0õíµ•Ñ…‘…Ñ„¹•Ğ ¥}ÉÕ¹}ÕÉ°œ°€œœ¥ôˆ°(€€€€€€€˜‰)IY%M}%}	I9 õíµ•Ñ…‘…Ñ„¹•Ğ ¥}‰É…¹ œ°€œœ¥ôˆ°(€€€€€€€˜‰)IY%M}%}IA=M%Q=Idõíµ•Ñ…‘…Ñ„¹•Ğ ¥}É•Á½Í¥Ñ½Éäœ°€œœ¥ôˆ°(€€€€€€€˜‰)IY%M}%}5QQ}9IQ}Põíµ•Ñ…‘…Ñ„¹•Ğ µ•Ñ…‘…Ñ…}•¹•É…Ñ•‘}…Ğœ°€œœ¥ôˆ°(€€€€€€€˜‰)IY%M}%}	-9}MQQULõí©½‰Ì¹•Ğ ‰…­•¹‘}Ñ•ÍÑÌœ°€Õ¹­¹½İ¸œ¥ôˆ°(€€€€€€€˜‰)IY%M}%}%=M}MQQULõí©½‰Ì¹•Ğ ¥½Ìœ°€Õ¹­¹½İ¸œ¥ôˆ°(€€€€€€€˜‰)IY%M}%}5}MQQULõí©½‰Ì¹•Ğ µ…Œœ°€Õ¹­¹½İ¸œ¥ôˆ°(€€€€€€€˜‰)IY%M}%=M}	U%1}MQQULõí‰Õ¥±‘}©½‰Ì¹•Ğ ¥½Ìœ°€Õ¹­¹½İ¸œ¥ôˆ°(€€€€€€€˜‰)IY%M}5}	U%1}MQQULõí‰Õ¥±‘}©½‰Ì¹•Ğ µ…Œœ°€Õ¹­¹½İ¸œ¥ôˆ°(€€€€€€€˜‰)IY%M}	-9}QMQ}MQQULõíÑ•ÍÑ}©½‰Ì¹•Ğ ‰…­•¹‘}Ñ•ÍÑÌœ°€Õ¹­¹½İ¸œ¥ôˆ°(€€€€€€€˜‰)IY%M}5}QMQ}MQQULõíÑ•ÍÑ}©½‰Ì¹•Ğ µ…Œœ°€Õ¹­¹½İ¸œ¥ôˆ°(€€€t(€€€A…Ñ ¡Á…Ñ ¤¹İÉ¥Ñ•}Ñ•áĞ ‰q¸ˆ¹©½¥¸¡±¥¹•Ì¤€¬€‰q¸ˆ°•¹½‘¥¹œô‰ÕÑ˜´àˆ¤(()‘•˜µ…¥¸ ¤è(€€€Á…ÉÍ•È€ô…ÉÁ…ÉÍ”¹ÉÕµ•¹ÑA…ÉÍ•È ¤(€€€Á…ÉÍ•È¹…‘‘}…ÉÕµ•¹Ğ ˆ´µ½ÕÑÁÕĞˆ°‘•™…Õ±Ğô‰ÁÉ½©•Ğµ¡•…±Ñ µ¤¹©Í½¸ˆ¤(€€€Á…ÉÍ•È¹…‘‘}…ÉÕµ•¹Ğ ˆ´µ•¹Øµ½ÕÑÁÕĞˆ°‘•™…Õ±Ğôˆˆ¤(€€€Á…ÉÍ•È¹…‘‘}…ÉÕµ•¹Ğ ˆ´µÁ±…¸ˆ°‘•™…Õ±ĞõÍÑÈ¡U1Q}A19}AQ ¤¤(€€€…ÉÌ€ôÁ…ÉÍ•È¹Á…ÉÍ•}…ÉÌ ¤((€€€µ•Ñ…‘…Ñ„€ô‰Õ¥±‘}µ•Ñ…‘…Ñ„¡Á±…¹}Á…Ñ õ…ÉÌ¹Á±…¸¤(€€€A…Ñ ¡…ÉÌ¹½ÕÑÁÕĞ¤¹İÉ¥Ñ•}Ñ•áĞ (€€€€€€€©Í½¸¹‘ÕµÁÌ¡µ•Ñ…‘…Ñ„°•¹ÍÕÉ•}…Í¥¤õ…±Í”°¥¹‘•¹ĞôÈ¤€¬€‰q¸ˆ°(€€€€€€€•¹½‘¥¹œô‰ÕÑ˜´àˆ°(€€€€¤(€€€¥˜…ÉÌ¹•¹Ù}½ÕÑÁÕĞè(€€€€€€€}İÉ¥Ñ•}•¹Ø¡…ÉÌ¹•¹Ù}½ÕÑÁÕĞ°µ•Ñ…‘…Ñ„¤(()¥˜}}¹…µ•}|€ôô€‰}}µ…¥¹}|ˆè(€€€µ…¥¸ ¤(