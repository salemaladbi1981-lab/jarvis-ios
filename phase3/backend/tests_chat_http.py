"""Real HTTP contract from pairing/session through conversation and chat replay."""
import os
import tempfile
import unittest
from unittest.mock import patch

root = tempfile.mkdtemp(prefix='jarvis-chat-http-')
for key, name in {'STORAGE_ROOT': 'storage', 'SESSIONS': 'sessions.json', 'AUDIT_PATH': 'audit.jsonl',
                  'AGENT_AUDIT': 'agents.jsonl', 'AGENT_STATE': 'agents.json'}.items():
    os.environ['JARVIS_' + key] = os.path.join(root, name)
import auth
import chat
import messages
from main import app
from fastapi.testclient import TestClient


class ChatHTTPTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.token = auth.create_session('http-owner', workspace_id='PERSONAL')
        self.headers = {'X-Jarvis-Session': self.token, 'X-Jarvis-Workspace': 'PERSONAL'}

    def create(self, headers=None):
        response = self.client.post('/conversations', headers=headers or self.headers, json={})
        self.assertEqual(response.status_code, 200)
        return response.json()['conversation']['conversation_id']

    def test_session_and_workspace_rejection(self):
        self.assertEqual(self.client.post('/conversations', json={}).status_code, 401)
        denied = dict(self.headers, **{'X-Jarvis-Workspace': 'QREC_LOCKED'})
        self.assertEqual(self.client.post('/conversations', headers=denied, json={}).status_code, 403)

    def test_create_load_stream_and_replay(self):
        cid = self.create()
        response = self.client.get('/conversations/' + cid, headers=self.headers)
        self.assertEqual(response.json()['conversation']['conversation_id'], cid)
        calls = []
        def source(text, ident):
            calls.append((text, ident))
            yield {'type': 'content_delta', 'delta': 'مرحبا'}
        with patch.object(chat, 'hermes_stream_source', source):
            first = self.client.post('/conversations/' + cid + '/chat', headers=self.headers,
                                     json={'text': 'hello', 'client_msg_id': 'http-retry'})
            second = self.client.post('/conversations/' + cid + '/chat', headers=self.headers,
                                      json={'text': 'hello', 'client_msg_id': 'http-retry'})
        self.assertEqual(first.status_code, 200)
        self.assertIn('text/event-stream', first.headers['content-type'])
        self.assertIn('message_complete', first.text)
        self.assertEqual(first.text, second.text)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(messages.MessageStore().list(cid)), 2)

    def test_workspace_is_applied_to_chat_and_history(self):
        cid = self.create()
        other = dict(self.headers, **{'X-Jarvis-Workspace': 'VENTURES'})
        self.assertEqual(self.client.get('/conversations/' + cid, headers=other).status_code, 404)
        self.assertEqual(self.client.post('/conversations/' + cid + '/chat', headers=other,
                                          json={'text': 'hello'}).status_code, 404)
        new_id = self.create(other)
        self.assertEqual(self.client.get('/conversations/' + new_id, headers=self.headers).status_code, 404)

    def test_new_conversation_is_explicit_and_audit_never_contains_token(self):
        first = self.create()
        self.assertEqual(first, self.create())
        result = self.client.post('/conversations', headers=self.headers, json={'create_new': True})
        self.assertEqual(result.status_code, 200)
        self.assertNotEqual(result.json()['conversation']['conversation_id'], first)
        with open(os.environ['JARVIS_AUDIT_PATH']) as f:
            self.assertNotIn(self.token, f.read())

    def test_empty_text_and_invalid_request_id_are_rejected(self):
        cid = self.create()
        for body in [{'text': ' '}, {'text': 'hello', 'client_msg_id': ''},
                     {'text': 'hello', 'client_msg_id': 'x' * 129}]:
            self.assertEqual(self.client.post('/conversations/' + cid + '/chat', headers=self.headers,
                                              json=body).status_code, 422)
        self.assertEqual(messages.MessageStore().list(cid), [])


if __name__ == '__main__': unittest.main()
