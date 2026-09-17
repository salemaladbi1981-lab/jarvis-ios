"""Fake email providers + registry helpers — deterministic tests (no real Gmail)."""
from email_provider import EmailProvider
from email_accounts import EmailAccount, AccountRegistry


class FakeProvider(EmailProvider):
    provider_name = "fake"

    def __init__(self, messages=None):
        self.messages = messages or {}
        self.sent = []
        self.fail = False  # simulate provider failure

    def summary(self, limit=10, q=None):
        if self.fail:
            raise Exception("provider_down")
        return [{"id": mid, "from": m["from"], "subject": m["subject"],
                 "snippet": m.get("body", "")[:60], "unread": False}
                for mid, m in list(self.messages.items())[:limit]]

    def search(self, q, limit=20):
        return self.summary(limit=limit)

    def read_message(self, mid):
        m = self.messages.get(mid)
        if not m:
            return None
        return {"id": mid, "from": m["from"], "subject": m["subject"], "body": m.get("body", "")}

    def message_headers(self, mid):
        m = self.messages.get(mid)
        if not m:
            return None
        return {"from": m["from"], "subject": m["subject"]}

    def send(self, to, subject, body):
        if self.fail:
            raise Exception("send_down")
        sid = "sent_" + str(len(self.sent) + 1)
        self.sent.append({"to": to, "subject": subject, "body": body})
        return {"id": sid, "threadId": "t_" + sid}


def fake_registry(spec):
    """spec: list of (account_id, display_name, email, messages_dict)."""
    accounts, providers = [], {}
    for aid, display, email, msgs in spec:
        accounts.append(EmailAccount(aid, display, "fake", email, "/tmp/" + aid + ".json", ["read", "send"]))
        providers[aid] = FakeProvider(msgs)
    return AccountRegistry(accounts, providers=providers)
