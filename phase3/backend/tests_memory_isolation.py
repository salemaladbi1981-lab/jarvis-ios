"""UPG-2 memory isolation + evidence — تخزين فعلي معزول لكل مساحة + دليل مصدر."""
import sys, os, shutil

os.environ["JARVIS_MEMORY_ROOT"] = "/tmp/jarvis-mem-test"
shutil.rmtree("/tmp/jarvis-mem-test", ignore_errors=True)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import memory_store, memory_bridge, identity

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

# A) كل memory item يحمل metadata كاملة
r = memory_store.store("PERSONAL", "أفضل مطعم في الدوحة هو Nobu", type="preference", source="user_stated", verification="verified")
check("store returns item", r["ok"])
item = r["item"]
for k in ["workspace_id", "memory_id", "type", "source", "created_at", "verification"]:
    check(f"item carries {k}", k in item)
check("item workspace_id == PERSONAL", item["workspace_id"] == "PERSONAL")

# B) عزل تخزين فعلي (مجلدات منفصلة)
check("PERSONAL dir exists", os.path.isdir(os.path.join("/tmp/jarvis-mem-test", "PERSONAL")))
memory_store.store("VENTURES", "شريك في مشروع X", type="fact", source="user_stated")
check("VENTURES dir exists", os.path.isdir(os.path.join("/tmp/jarvis-mem-test", "VENTURES")))
check("separate index files", os.path.exists("/tmp/jarvis-mem-test/PERSONAL/index.json") and os.path.exists("/tmp/jarvis-mem-test/VENTURES/index.json"))

# C) retrieval scoped — لا cross-workspace
check("retrieve PERSONAL finds its item", len(memory_store.retrieve("PERSONAL", "Nobu")) == 1)
check("retrieve VENTURES excludes PERSONAL item", len(memory_store.retrieve("VENTURES", "Nobu")) == 0)
check("list PERSONAL only", all(it["workspace_id"] == "PERSONAL" for it in memory_store.list_items("PERSONAL")))

# D) QREC_LOCKED عزل كامل
memory_store.store("QREC_LOCKED", "تفاصيل حملة QREC سرية", type="secret", source="user_stated", verification="unverified")
check("QREC_LOCKED dir separate", os.path.isdir(os.path.join("/tmp/jarvis-mem-test", "QREC_LOCKED")))
check("PERSONAL retrieve excludes QREC_LOCKED", len(memory_store.retrieve("PERSONAL", "QREC")) == 0)
check("QREC_LOCKED retrieve finds secret", len(memory_store.retrieve("QREC_LOCKED", "QREC")) == 1)
check("PERSONAL list excludes QREC_LOCKED", all(it["workspace_id"] != "QREC_LOCKED" for it in memory_store.list_items("PERSONAL")))

# E) memory_bridge.recall scoped عبر الهوية (كل المسارات)
ident_personal = identity.from_args({"user_id": "salem-aladbi", "workspace_id": "PERSONAL"}).to_dict()
ident_ventures = identity.from_args({"user_id": "salem-aladbi", "workspace_id": "VENTURES"}).to_dict()
r = memory_bridge.recall("Nobu", ident_personal)
check("recall(PERSONAL) finds Nobu", r["found"] and any(e.get("source") == "memory_store" for e in r["evidence"]))
r2 = memory_bridge.recall("Nobu", ident_ventures)
check("recall(VENTURES) does NOT find PERSONAL Nobu", not any(e.get("source") == "memory_store" for e in r2["evidence"]))
r3 = memory_bridge.recall("QREC", ident_personal)
check("recall(PERSONAL) does NOT find QREC secret", not any(e.get("source") == "memory_store" for e in r3["evidence"]))

# F) get scoped
check("get cross-workspace denied", memory_store.get("VENTURES", item["memory_id"]) is None)
check("get same-workspace ok", memory_store.get("PERSONAL", item["memory_id"]) is not None)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(0 if FAIL == 0 else 1)
