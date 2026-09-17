"""V1.1 Memory Architecture — regression (source-level + logic mirror).
يتحقق: retrieval ذو صلة ومحدود، historical لا يصبح current،
القرار الأحدث الصريح يلغي الأقدم، الأسرار تُرفض، فشل الذاكرة لا يكسر Live Voice."""
import sys, os, re
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {name}")
    else: FAIL += 1; print(f"  FAIL  {name}")

def read(p): return open(os.path.join(ROOT, p), encoding='utf-8').read()

mi = read('Memory/MemoryItem.swift')
ms = read('Memory/MemoryStore.swift')
mr = read('Memory/MemoryRetrieval.swift')
seed = read('Memory/MemorySeed.swift')
vm = read('Home/HomeViewModel.swift')
gp = read('../generate_project.py')

# A. Schema — الفئات الست + مصادر الأربعة
for c in ['durableFact', 'preference', 'activeProject', 'decision', 'historical', 'session']:
    check(f"category {c}", c in mi)
for p in ['ownerProvided', 'importedSeed', 'explicitDecision', 'runtimeState']:
    check(f"provenance {p}", p in mi)

# B. Retrieval — لا حقن كامل، scope، حدّ حجم
check("retrieve has limit + charBudget", 'limit' in mr and 'charBudget' in mr)
check("retrieve filters isActive", 'isActive' in mr)
check("scope current excludes historical+session", "c != .historical && c != .session" in mr)
check("score uses keywords+category+priority", 'keywords' in mr and 'priority' in mr)

# C. Conflict — القرار الأحدث الصريح يلغي الأقدم
check("upsert deactivates conflicting older", 'isActive = false' in ms)
check("authority ranking (explicitDecision > ownerProvided > importedSeed > runtimeState)", 'explicitDecision' in ms and 'authority' in ms)
check("conflict requires explicit provenance", 'explicitDecision' in ms and 'ownerProvided' in ms)

# D. Privacy — أسرار
check("containsSecret rejects sk-/ghp_/password/api_key", 'sk-' in ms and 'ghp_' in ms and 'password' in ms and 'api' in ms)

# E. Owner control
check("disable(id) present", 'disable(id' in ms)
check("remove(id) present", 'remove(id' in ms)
check("allItems(activeOnly) present", 'allItems' in ms)

# F. Failure mode — فشل الذاكرة لا يمس Live Voice
check("memory is lazy optional (fail-safe)", 'private var memory: MemoryStore?' in vm)
check("ensureMemory lazy init", 'ensureMemory' in vm)
check("memoryAnswer returns String? (nil => no voice action)", 'func memoryAnswer(for' in vm and '-> String?' in vm)
check("speak only on non-nil answer", 'if let answer = memoryAnswer' in vm)

# G. Seed — بذور مفهرسة بكلمات
check("seed has identity facts", 'الاسم' in seed or 'اسم' in seed)
check("seed has frozen decision", 'مجمّد' in seed or 'مجمّد' in seed)
check("seed provenance importedSeed", 'importedSeed' in seed)
check("seed decision provenance explicitDecision", 'explicitDecision' in seed)

# H. Project wiring
check("Memory files in APP_SOURCES", all(x in gp for x in ['Memory/MemoryItem.swift','Memory/MemoryStore.swift','Memory/MemoryRetrieval.swift','Memory/MemorySeed.swift']))
check("MemoryTests in TEST_SOURCES", 'JARVISTests/MemoryTests.swift' in gp)
check("JARVIS.xcscheme regenerated from app_target", 'JARVIS.xcscheme' in gp and 'app_target' in gp)

# I. Logic mirror — نفس سيناريوهات اختبارات Swift
CATEGORY = {'durableFact','preference','activeProject','decision','historical','session'}
def tokenize(s):
    return {w for w in re.split(r'[^0-9A-Za-z\u0600-\u06FF]+', s.lower()) if len(w) >= 2}

def scope_allows(cat, scope):
    if scope == 'current': return cat not in ('historical','session')
    if scope == 'historical': return cat != 'session'
    return True

def retrieve(items, query, scope='current', limit=5, budget=1200):
    qt = tokenize(query)
    scored = []
    for it in items:
        if not it['active']: continue
        kw = {k.lower() for k in it['keywords']}
        body = tokenize(it['content'])
        s = 0.0
        for t in qt:
            if t in kw: s += 3
            elif t in body: s += 1
        if it['category'] in ('durableFact','decision'): s += 2
        elif it['category'] in ('preference','activeProject'): s += 1.5
        elif it['category'] == 'historical' and scope == 'historical': s += 1
        elif it['category'] == 'session' and scope == 'all': s += 0.5
        s += it['priority'] * 0.1
        if s > 0: scored.append((it, s))
    scored.sort(key=lambda x: -x[1])
    out, used = [], 0
    for it, _ in scored:
        if not scope_allows(it['category'], scope): continue
        if len(out) >= limit: break
        if used + len(it['content']) > budget: continue
        out.append(it); used += len(it['content'])
    return out

items = [
    {'id':'name','category':'durableFact','active':True,'keywords':['اسم','هوية'],'content':'الاسم: سالم','priority':10},
    {'id':'meridian','category':'activeProject','active':True,'keywords':['مشروع','مريديان'],'content':'مشروع MERIDIAN','priority':8},
    {'id':'old','category':'historical','active':True,'keywords':['تاريخ'],'content':'سياق قديم','priority':3},
]
r = retrieve(items, 'وش اسمي')
check("mirror: identity query returns name first", r and r[0]['id'] == 'name')
check("mirror: historical excluded from current", all(x['id'] != 'old' for x in r))
h = retrieve(items, 'قديم تاريخ', scope='historical')
check("mirror: historical scope includes old", any(x['id'] == 'old' for x in h))

# conflict mirror
store = []
def upsert(it):
    for i in store:
        if i['id'] == it['id']: return True
    is_explicit = it['prov'] in ('explicitDecision','ownerProvided')
    for idx in range(len(store)):
        old = store[idx]
        if old['active'] and old['category'] == it['category'] and old['id'] != it['id']:
            if set(old['keywords']) & set(it['keywords']) and it['updated'] >= old['updated'] and is_explicit:
                store[idx]['active'] = False
    store.append(it)
    return True

upsert({'id':'d1','category':'decision','prov':'explicitDecision','keywords':['نسخة'],'content':'V1.0','updated':100,'active':True})
upsert({'id':'d2','category':'decision','prov':'explicitDecision','keywords':['نسخة'],'content':'V1.1','updated':200,'active':True})
active = [i for i in store if i['active']]
check("mirror: newer decision overrides older", any(i['id']=='d2' for i in active) and not any(i['id']=='d1' for i in active))

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(0 if FAIL == 0 else 1)
