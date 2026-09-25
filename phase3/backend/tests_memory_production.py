"""Production recall paths: real isolated stores, no seeded answers or identity override."""
import os
import tempfile
import sqlite3
import unittest
from unittest.mock import patch

root = tempfile.mkdtemp(prefix='jarvis-memory-prod-')
for key, name in {'STORAGE_ROOT': 'storage', 'MEMORY_ROOT': 'memories', 'MEMORY_DIR': 'memories',
                  'USER_MEMORY': 'USER.md', 'STATE_DB': 'state.db', 'SESSIONS': 'sessions.json',
                  'AUDIT_PATH': 'audit.jsonl'}.items():
    os.environ['JARVIS_' + key] = os.path.join(root, name)
import memory_bridge
import memory_store
import messages
import chat
import conversation
import realtime
import auth
from main import app
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


class ProductionMemoryTests(unittest.TestCase):
    def ident(self, ws='PERSONAL', user='salem-aladbi'):
        return {'user_id': user, 'workspace_id': ws, 'session_id': 's1', 'conversation_id': 'c1',
                'memory_namespace': f'jarvis:{user}:{ws}:c1'}

    def test_memory_store_workspace_and_user_isolation(self):
        memory_store.store('QREC_LOCKED', 'locked-canary-829', source='user_stated')
        self.assertTrue(memory_bridge.recall('locked-canary-829', self.ident('QREC_LOCKED'))['found'])
        for ident in [self.ident(), self.ident('VENTURES'), self.ident('QREC_LOCKED', 'other')]:
            self.assertFalse(memory_bridge.recall('locked-canary-829', ident)['found'])

    def test_legacy_user_file_only_available_to_owner_personal(self):
        with open(os.environ['JARVIS_USER_MEMORY'], 'w') as f: f.write('owner-personal-canary')
        result = memory_bridge.recall('owner-personal-canary', self.ident())
        self.assertTrue(result['found'])
        self.assertIn('owner-personal-canary', result['evidence'][0]['snippet'])
        for ident in [self.ident('VENTURES'), self.ident('QREC_LOCKED'), self.ident(user='other')]:
            self.assertFalse(memory_bridge.recall('owner-personal-canary', ident)['found'])

    def test_recent_and_keyword_chat_history_are_workspace_scoped(self):
        messages.MessageStore().add('c1', 'user', 'history-canary-833', user_id='salem-aladbi', workspace_id='VENTURES')
        self.assertTrue(memory_bridge.recall('history-canary-833', self.ident('VENTURES'))['found'])
        self.assertFalse(memory_bridge.recall('history-canary-833', self.ident())['found'])
        recent = memory_bridge.recall('what were we discussing', self.ident())
        self.assertNotIn('history-canary-833', str(recent))

    def test_unscoped_legacy_database_is_not_exposed(self):
        with sqlite3.connect(os.environ['JARVIS_STATE_DB']) as db:
            db.execute('CREATE TABLE IF NOT EXISTS sessions (id TEXT, user_id TEXT, title TEXT, started_at REAL)')
            db.execute('CREATE TABLE IF NOT EXISTS messages (session_id TEXT, content TEXT, role TEXT, timestamp REAL, active INTEGER)')
            db.execute("INSERT INTO sessions VALUES ('legacy', NULL, 'private', 1)")
            db.execute("INSERT INTO messages VALUES ('legacy', 'unscoped-canary-901', 'user', 1, 1)")
        self.assertFalse(memory_bridge.recall('unscoped-canary-901', self.ident())['found'])
        self.assertFalse(memory_bridge.recall('unscoped-canary-901', self.ident('QREC_LOCKED'))['found'])

    def test_empty_store_does_not_answer_from_seed(self):
        result = memory_bridge.recall('nonexistent-personal-memory-472', self.ident())
        self.assertFalse(result['found'])
        self.assertEqual(result['reason'], 'no_stored_context')
        self.assertFalse(memory_bridge.recall('anything', {})['found'])

    def test_model_cannot_override_trusted_identity(self):
        forged = {'query': 'name', **self.ident('QREC_LOCKED', 'intruder')}
        scoped = realtime.scoped_tool_arguments(forged, self.ident())
        for key, value in self.ident().items(): self.assertEqual(scoped[key], value)
        self.assertEqual(scoped['query'], 'name')
        with self.assertRaises(ValueError): realtime.scoped_tool_arguments(forged, None)

    def test_chat_uses_stable_backend_memory_namespace(self):
        conv = conversation.ConversationStore().create('salem-aladbi', 'VENTURES')
        seen = []
        def source(text, ident, attachments):
            seen.append(ident)
            yield {'type': 'content_delta', 'delta': 'provider result'}
        for _ in range(2):
            list(chat.stream_chat(conv['conversation_id'], 'hello', self.ident('VENTURES'), stream_source=source))
        self.assertEqual(seen[0]['memory_namespace'], conv['memory_namespace'])
        self.assertEqual(seen[0]['memory_namespace'], seen[1]['memory_namespace'])

    def test_personal_question_uses_backend_memory_without_model_guessing(self):
        memory_store.store('VENTURES', 'name: scoped-personal-answer-502', source='user_stated')
        with patch('brain_tools.execute_brain_tool', side_effect=AssertionError('No model guessing')):
            result = list(chat.hermes_stream_source('what is my name', self.ident('VENTURES')))
            self.assertIn('scoped-personal-answer-502', result[0]['delta'])
            result = list(chat.hermes_stream_source('what is my name', self.ident('QREC_LOCKED')))
            self.assertNotIn('scoped-personal-answer-502', result[0]['delta'])
            self.assertIn('لا أملك', result[0]['delta'])

    def test_voice_socket_requires_session_and_rejects_locked_workspace(self):
        client = TestClient(app)
        with self.assertRaises(WebSocketDisconnect) as rejected:
            with client.websocket_connect('/realtime'): pass
        self.assertEqual(rejected.exception.code, 4401)
        token = auth.create_session('salem-aladbi', workspace_id='PERSONAL')
        with self.assertRaises(WebSocketDisconnect) as rejected:
            with client.websocket_connect('/realtime', headers={'X-Jarvis-Session': token, 'X-Jarvis-Workspace': 'QREC_LOCKED'}): pass
        self.assertEqual(rejected.exception.code, 4403)
        captured = []
        async def proxy(ws, config, trusted_identity=None):
            captured.append(trusted_identity)
            await ws.send_json({'type': 'verified'})
        with patch.object(realtime, 'openai_realtime_proxy', proxy):
            with client.websocket_connect('/realtime', headers={'X-Jarvis-Session': token, 'X-Jarvis-Workspace': 'VENTURES'}) as ws:
                self.assertEqual(ws.receive_json()['type'], 'verified')
        self.assertEqual(captured[0]['workspace_id'], 'VENTURES')
        self.assertEqual(captured[0]['user_id'], 'salem-aladbi')
        self.assertNotIn(token, str(captured))

if __name__ == '__main__': unittest.main()
