"""Account Registry — إدارة عدة حسابات بريد بأمان (Multi-Account).

كل حساب: account_id ثابت + display name + provider + email + token_path مستقل + scopes.
الـ registry يعيش خارج الـ repo (/opt/data/email_accounts.json) — لا tokens ولا secrets في repo.
إضافة حساب جديد = إضافة entry في الـ JSON (لا تغيير كود).
"""
import json, os


class EmailAccount:
    def __init__(self, account_id, display_name, provider, email, token_path, scopes=None):
        self.account_id = account_id
        self.display_name = display_name
        self.provider = provider
        self.email = email
        self.token_path = token_path
        self.scopes = scopes or []

    def to_dict(self):
        return {
            "account_id": self.account_id,
            "display_name": self.display_name,
            "provider": self.provider,
            "email": self.email,
            "token_path": self.token_path,
            "scopes": self.scopes,
        }


def make_provider(account):
    """يحوّل حساباً إلى EmailProvider بناءً على provider. إضافة Outlook = فرع هنا."""
    from email_provider import GmailProvider
    if account.provider == "gmail":
        return GmailProvider(account.token_path)
    raise ValueError(f"unsupported provider: {account.provider}")


class AccountRegistry:
    """سجل الحسابات + عمليات موحّدة (unified) تحمل account_id في كل نتيجة."""

    def __init__(self, accounts, providers=None):
        self._accounts = {a.account_id: a for a in accounts}
        self._providers = providers if providers is not None else {a.account_id: make_provider(a) for a in accounts}

    def all_accounts(self):
        return list(self._accounts.values())

    def account_ids(self):
        return list(self._accounts.keys())

    def get(self, account_id):
        return self._accounts.get(account_id)

    def provider(self, account_id):
        return self._providers.get(account_id)

    def _ids(self, account_id):
        return [account_id] if account_id else self.account_ids()

    def summary(self, account_id=None, limit=10, q=None):
        """Unified inbox: يجمع رسائل كل الحسابات (أو حساب واحد) ويميّز كل رسالة بـ account_id."""
        out = []
        for aid in self._ids(account_id):
            prov = self._providers.get(aid)
            acct = self._accounts.get(aid)
            if not prov or not acct:
                continue
            try:
                for m in prov.summary(limit=limit, q=q):
                    m = dict(m)
                    m["account_id"] = aid
                    m["account"] = acct.display_name
                    out.append(m)
            except Exception:
                # فشل حساب واحد لا يكسر الحسابات الأخرى
                continue
        return out

    def search(self, account_id=None, query="", limit=20):
        out = []
        for aid in self._ids(account_id):
            prov = self._providers.get(aid)
            acct = self._accounts.get(aid)
            if not prov or not acct:
                continue
            try:
                for m in prov.search(query, limit=limit):
                    m = dict(m)
                    m["account_id"] = aid
                    m["account"] = acct.display_name
                    out.append(m)
            except Exception:
                continue
        return out

    def read(self, account_id, mid):
        prov = self.provider(account_id)
        if not prov:
            return None
        return prov.read_message(mid)

    def headers(self, account_id, mid):
        prov = self.provider(account_id)
        if not prov:
            return None
        return prov.message_headers(mid)

    def send(self, account_id, to, subject, body):
        prov = self.provider(account_id)
        if not prov:
            raise ValueError("unknown_account")
        return prov.send(to, subject, body)

    @classmethod
    def from_json(cls, path):
        d = json.load(open(path, encoding="utf-8"))
        accounts = []
        for a in d.get("accounts", []):
            accounts.append(EmailAccount(
                a["account_id"],
                a.get("display_name", a["account_id"]),
                a.get("provider", "gmail"),
                a["email"],
                a["token_path"],
                a.get("scopes", [])))
        return cls(accounts)


REGISTRY_PATH = os.environ.get("JARVIS_ACCOUNT_REGISTRY", "/opt/data/email_accounts.json")


def default_registry():
    """يبني السجل من الملف إن وُجد، وإلا حساب شخصي واحد (backward compatible)."""
    if os.path.exists(REGISTRY_PATH):
        return AccountRegistry.from_json(REGISTRY_PATH)
    return AccountRegistry([EmailAccount(
        "personal", "Personal", "gmail",
        os.environ.get("JARVIS_PERSONAL_EMAIL", "salemaladbi1981@gmail.com"),
        os.environ.get("GOOGLE_TOKEN_PATH", "/opt/data/google_token.json"),
        ["read", "send"])])
