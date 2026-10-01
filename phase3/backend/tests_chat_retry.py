"""Regression: retry receipts preserve identity, messages, and tool side effects."""
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor

os.environ['JARVIS_STORAGE_ROOT'] = tempfile.mkdtemp(prefix='jarvis-retry-')
os.environ['JARVIS_AUDIT_PATH'] = os.path.join(os.environ['JARVIS_STORAGE_ROOT'], 'audit.jsonl')
import chat
import chat_requests
import conversation
import messages


class RetryTests(unittest.TestCase):
    def setUp(self):
        self.ident = {'user_id': 'retry-owner', 'workspace_id': 'PERSONAL'}
        self.cid = conversation.ConversationStore().create('retry-owner', 'PERSONAL')['conversation_id']
        self.calls = 0

    def source(self, text, ident, attachments):
        self.calls += 1
        yield {'type': 'content_delta', 'delta': 'A real provider result'}

    def run_chat(self, request='r1', text='hello', **kwargs):
        return list(chat.stream_chat(self.cid, text, self.ident, client_msg_id=request,
                                     stream_source=self.source, **kwargs))

    def test_retry_replays_same_assistant_without_new_messages_or_execution(self):
        first = self.run_chat()
        self.assertEqual(first, self.run_chat())
        self.assertEqual(self.calls, 1)
        self.assertEqual(len(messages.MessageStore().list(self.cid)), 2)

    def test_request_id_cannot_be_reused_for_different_content(self):
        self.run_chat()
        result = self.run_chat(text='different')
        self.assertEqual(result[0]['data']['error_type'], 'request_conflict')
        self.assertEqual(self.calls, 1)

    def test_inflight_retry_does_not_start_second_execution(self):
        active = chat.stream_chat(self.cid, 'hello', self.ident, client_msg_id='r1', stream_source=self.source)
        next(active)
        self.assertEqual(self.run_chat()[0]['data']['error_type'], 'request_in_progress')
        active.close()
        self.assertEqual(self.run_chat()[0]['data']['error_type'], 'request_interrupted')
        self.assertEqual(len(messages.MessageStore().list(self.cid)), 2)

    def test_receipt_isolation_and_ownership(self):
        self.run_chat()
        other = {'user_id': 'intruder', 'workspace_id': 'PERSONAL'}
        result = list(chat.stream_chat(self.cid, 'hello', other, client_msg_id='r1'))
        self.assertEqual(result[0]['data']['error_type'], 'auth_error')
        other = {'user_id': 'retry-owner', 'workspace_id': 'BUSINESS'}
        result = list(chat.stream_chat(self.cid, 'hello', other, client_msg_id='r1'))
        self.assertEqual(result[0]['data']['error_type'], 'auth_error')

    def test_atomic_claim(self):
        def claim(_):
            return chat_requests.claim(self.ident, self.cid, 'concurrent', 'hello', [])[1]
        with ThreadPoolExecutor(max_workers=8) as pool:
            states = list(pool.map(claim, range(16)))
        self.assertEqual(states.count('new'), 1)
        self.assertEqual(states.count('running'), 15)

    def test_failed_tool_is_not_automatically_repeated(self):
        def failure(*args):
            self.calls += 1
            raise RuntimeError('provider unavailable')
            yield
        first = list(chat.stream_chat(self.cid, 'hello', self.ident, client_msg_id='failed', stream_source=failure))
        second = list(chat.stream_chat(self.cid, 'hello', self.ident, client_msg_id='failed', stream_source=failure))
        self.assertEqual(first, second)
        self.assertEqual(self.calls, 1)
        self.assertEqual(first[-1]['event'], 'error')


if __name__ == '__main__':
    unittest.main()
