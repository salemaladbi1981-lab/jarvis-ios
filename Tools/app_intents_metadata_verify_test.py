"""Regression tests for compiled AppIntents metadata validation."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("metadata_verify", ROOT / "Tools/app_intents_metadata_verify.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def action():
    return {"isAuthPolExplicit": True, "isDiscoverable": True, "openAppWhenRun": True}


def shortcut(identifier, phrases):
    return {"actionIdentifier": identifier, "phraseTemplates": [{"key": p} for p in phrases]}


VALID = {
    "actions": {name: action() for name in module.EXPECTED_ACTIONS},
    "autoShortcuts": [
        shortcut("JarvisVoiceIntent", ["Start ${applicationName}", "شغل ${applicationName}"]),
        shortcut("JarvisOpenIntent", ["Open ${applicationName}", "افتح ${applicationName}"]),
    ],
}

cases = []
cases.append(("valid compiled contract passes", VALID, []))

bad = deepcopy(VALID); bad["actions"].pop("JarvisVoiceIntent")
cases.append(("missing voice intent fails", bad, ["action:JarvisVoiceIntent"]))

bad = deepcopy(VALID); bad["actions"]["JarvisOpenIntent"]["isAuthPolExplicit"] = False
cases.append(("non-explicit auth policy fails", bad, ["auth_explicit:JarvisOpenIntent"]))

bad = deepcopy(VALID); bad["autoShortcuts"].append(shortcut("JarvisNavigateIntent", ["Navigate ${applicationName}"]))
cases.append(("parameterized navigation is not auto-registered", bad, ["shortcut_action_set", "parameterized_navigation_shortcut"]))

bad = deepcopy(VALID); bad["autoShortcuts"][0]["phraseTemplates"] = [{"key": "Start ${applicationName}"}]
cases.append(("Arabic voice phrase remains compiled", bad, ["phrases:JarvisVoiceIntent"]))

passed = 0
for name, payload, expected in cases:
    got = module.validate_payload(payload)
    ok = all(item in got for item in expected) if expected else got == []
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f" got={got}"))
    passed += int(ok)

print(f"app intents metadata verifier: {passed}/{len(cases)} PASS")
sys.exit(0 if passed == len(cases) else 1)
