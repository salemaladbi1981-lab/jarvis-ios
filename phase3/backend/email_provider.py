"""Email Provider abstraction — NOT Gmail-only.

كل حساب بريد يرتبط بـ EmailProvider بتنفيذ provider محدد (Gmail الآن، Outlook لاحقاً).
إضافة provider جديد = subclass جديد هنا + فرع في make_provider (email_accounts.py).
"""
import gmail_tools
import ms_graph


class EmailProvider:
    """واجهة موحّدة لأي مزوّد بريد. التنفيذ الفعلي في الـ subclass."""
    provider_name = "base"

    def summary(self, limit=10, q=None):
        raise NotImplementedError

    def search(self, q, limit=20):
        raise NotImplementedError

    def read_message(self, mid):
        raise NotImplementedError

    def message_headers(self, mid):
        raise NotImplementedError

    def send(self, to, subject, body):
        raise NotImplementedError


class MicrosoftProvider(EmailProvider):
    provider_name = "microsoft"

    def __init__(self, token_path):
        self.token_path = token_path

    def summary(self, limit=10, q=None):
        return ms_graph.summary(limit=limit, q=q, token_path=self.token_path)

    def search(self, q, limit=20):
        return ms_graph.search(q, limit=limit, token_path=self.token_path)

    def read_message(self, mid):
        return ms_graph.read_message(mid, token_path=self.token_path)

    def message_headers(self, mid):
        return ms_graph.message_headers(mid, token_path=self.token_path)

    def send(self, to, subject, body):
        return ms_graph.send(to, subject, body, token_path=self.token_path)


class GmailProvider(EmailProvider):
    provider_name = "gmail"

    def __init__(self, token_path):
        self.token_path = token_path

    def summary(self, limit=10, q=None):
        return gmail_tools.summary(limit=limit, q=q, token_path=self.token_path)

    def search(self, q, limit=20):
        return gmail_tools.search(q, limit=limit, token_path=self.token_path)

    def read_message(self, mid):
        return gmail_tools.read_message(mid, token_path=self.token_path)

    def message_headers(self, mid):
        return gmail_tools.message_headers(mid, token_path=self.token_path)

    def send(self, to, subject, body):
        return gmail_tools.send(to, subject, body, token_path=self.token_path)
