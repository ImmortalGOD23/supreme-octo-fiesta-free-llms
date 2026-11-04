"""Opt-in tests against the real FCC schema; no user config or inference."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
try:
    import free_claude_code
    HAS_FCC = True
except ImportError:
    HAS_FCC = False

@unittest.skipUnless(HAS_FCC, 'Requires FCC environment and upstream/fcc/src on PYTHONPATH')
class FCCContractTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.home = Path(self.temporary.name)
        self.path_patch = patch('pathlib.Path.home', return_value=self.home)
        self.env_patch = patch.dict(os.environ, {}, clear=True)
        self.path_patch.start()
        self.env_patch.start()
        spec = importlib.util.spec_from_file_location('fcc_config', ROOT / 'scripts/fcc_config.py')
        self.helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.helper)
    def tearDown(self):
        self.env_patch.stop()
        self.path_patch.stop()
        self.temporary.cleanup()
    def test_profile_preserves_keys_and_backups(self):
        from free_claude_code.config.loader import ManagedConfigStore
        from free_claude_code.config.api_keys import api_key_values
        store = ManagedConfigStore()
        store.initialize()
        before = store.read()
        store.commit(dict(before.managed) | {'NVIDIA_NIM_API_KEY': '["old-key"]'}, expected=before)
        original = store.path.read_bytes()
        self.helper.apply({'operation': 'nvidia', 'settings': {
            'NVIDIA_NIM_API_KEY': '["new-key"]',
            'MODEL': 'nvidia_nim/nvidia/nemotron-3-ultra-550b-a55b',
            'HOST': '127.0.0.1',
            'MODEL_FALLBACKS': '[{"model":"nvidia_nim/minimaxai/minimax-m3.1-flash"}]',
        }})
        after = store.read()
        self.assertEqual(api_key_values(after.settings.nvidia_nim_api_keys), ['new-key', 'old-key'])
        backups = list(store.path.parent.glob('*.bak'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)
    def test_connection_is_idempotent(self):
        from free_claude_code.config.loader import ManagedConfigStore
        definition = {'provider_id': 'custom_' + 'a' * 32, 'display_name': 'Test gateway',
                      'base_url': 'http://127.0.0.1:3001/v1', 'api_keys': ['gateway-key'],
                      'api_format': 'openai_chat', 'reasoning_format': 'provider_default', 'model_ids': []}
        payload = {'operation': 'connect', 'provider': definition, 'model': 'model-a', 'use_as': 'fallback'}
        self.helper.apply(payload)
        self.helper.apply(payload)
        after = ManagedConfigStore().read().settings
        self.assertEqual(len(after.custom_providers), 1)
        self.assertEqual(len(after.model_fallbacks), 1)
        self.assertTrue(after.model.startswith('nvidia_nim/'))
    def test_invalid_gateway_does_not_mutate(self):
        from free_claude_code.config.loader import ManagedConfigStore
        store = ManagedConfigStore()
        store.initialize()
        original = store.path.read_bytes()
        with self.assertRaises((ValueError, KeyError)):
            self.helper.apply({'operation': 'connect', 'provider': {'provider_id': 'bad', 'base_url': 'https://user:secret@example.com'}, 'model': 'm', 'use_as': 'available'})
        self.assertEqual(original, store.path.read_bytes())
