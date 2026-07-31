from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


@unittest.skipIf(os.name == "nt" or shutil.which("bash") is None, "bash required")
class RunShTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary_directory.cleanup)
        self.root = Path(self._temporary_directory.name)

        source_root = Path(__file__).resolve().parents[1]
        self.script = self.root / "run.sh"
        self.script.write_text(
            (source_root / "run.sh").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        activate = self.root / ".venv" / "bin" / "activate"
        activate.parent.mkdir(parents=True)
        activate.write_text("", encoding="utf-8")

        probe = self.root / "probe.sh"
        probe.write_text(
            "python() { printf 'provider=%s\\n' \"$SPEECH_PROVIDER\"; }\n",
            encoding="utf-8",
        )
        self.environment = os.environ.copy()
        self.environment.update(
            {
                "BASH_ENV": str(probe),
                "SPEECH_PROVIDER": "gcp",
                "GOOGLE_CLOUD_PROJECT": "test-project",
            }
        )

    def _run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(self.script), *arguments],
            cwd=self.root,
            env=self.environment,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_no_options_uses_local_despite_inherited_provider(self) -> None:
        result = self._run()

        self.assertEqual(result.stdout.strip(), "provider=local")

    def test_provider_option_overrides_local_default(self) -> None:
        result = self._run("--provider", "gcp")

        self.assertEqual(result.stdout.strip(), "provider=gcp")


if __name__ == "__main__":
    unittest.main()
