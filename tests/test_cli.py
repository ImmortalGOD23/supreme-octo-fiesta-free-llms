import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
from super_fcc import cli

class WorkspaceTests(unittest.TestCase):
    def test_init_is_private_and_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(cli, 'ROOT', root), contextlib.redirect_stdout(io.StringIO()):
                cli.init_workspace()
                first = (root / '.runtime/stack.env').read_bytes()
                cli.init_workspace()
            self.assertEqual(first, (root / '.runtime/stack.env').read_bytes())
            config = json.loads((root / '.runtime/cliproxyapi.yaml').read_text())
            self.assertFalse(config['management']['allow-remote'])
            self.assertEqual(config['access']['api-keys'][0], (root / '.runtime/cliproxyapi.key').read_text().strip())
            if os.name != 'nt':
                self.assertEqual((root / '.runtime/stack.env').stat().st_mode & 0o777, 0o600)

    def test_catalog_error_does_not_expose_key(self):
        error = urllib.error.HTTPError('http://example', 401, 'unauthorized', {}, None)
        with patch.object(cli.urllib.request, 'urlopen', side_effect=error):
            with self.assertRaises(ValueError) as caught:
                cli.models('nvidia', 'SECRET-NEVER-LOG')
        self.assertNotIn('SECRET-NEVER-LOG', str(caught.exception))

    def test_missing_model_does_not_change_fcc(self):
        with patch.object(cli, 'provider_key', return_value='secret'), patch.object(cli, 'models', return_value=[]), patch.object(cli, 'apply_fcc') as apply:
            with self.assertRaises(ValueError):
                cli.configure_nvidia()
            apply.assert_not_called()

    def test_connection_is_stable(self):
        with patch.object(cli, 'provider_key', return_value='secret'), patch.object(cli, 'models', return_value=['actual-model']), patch.object(cli, 'apply_fcc') as apply:
            cli.connect('freellmapi', 'actual-model', 'fallback')
            first = apply.call_args.args[0]
            cli.connect('freellmapi', 'actual-model', 'available')
            second = apply.call_args.args[0]
            self.assertEqual(first['provider']['provider_id'], second['provider']['provider_id'])
            self.assertEqual(first['provider']['api_keys'], ['secret'])

    def test_agent_preserves_directory(self):
        with patch.object(cli, 'uv_command', return_value=['fcc-claude']), patch.object(cli.subprocess, 'run') as run, patch('sys.argv', ['super-fcc', 'agent', 'claude']):
            cli.main()
            self.assertNotIn('cwd', run.call_args.kwargs)

    def test_gitlinks_match_lock(self):
        lock = json.loads((cli.ROOT / 'upstreams.lock.json').read_text())
        for name, entry in lock.items():
            commit = subprocess.check_output(['git', '-C', str(cli.ROOT / 'upstream' / name), 'rev-parse', 'HEAD'], text=True).strip()
            self.assertEqual(commit, entry['commit'])
