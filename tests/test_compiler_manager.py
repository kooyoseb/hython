import hashlib
import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from hython import compiler_manager


def make_wheel(path: Path, members=None) -> str:
    with zipfile.ZipFile(path,"w") as archive:
        for name,data in (members or {"hython/__init__.py":b'__version__="9.0"\n'}).items():
            archive.writestr(name,data)
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CompilerManagerTests(unittest.TestCase):
    def test_query_latest_requires_https_and_reads_pypi_digest(self):
        with self.assertRaisesRegex(compiler_manager.CompilerUpdateError,"HTTPS"):
            compiler_manager.query_latest(url="http://example.invalid/index")
        payload={"info":{"version":"9.0.0"},"releases":{"9.0.0":[{
            "packagetype":"bdist_wheel","filename":"hython_lang-9.0.0-py3-none-any.whl",
            "url":"https://example.invalid/hython.whl","digests":{"sha256":"a"*64},
        }]}}
        with patch("urllib.request.urlopen",return_value=io.BytesIO(json.dumps(payload).encode())):
            result=compiler_manager.query_latest()
        self.assertEqual(result["version"],"9.0.0")
        self.assertEqual(result["sha256"],"a"*64)

    def test_hash_mismatch_does_not_activate_compiler(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{"HYTHON_HOME":directory}):
            wheel=Path(directory)/"candidate.whl"; make_wheel(wheel)
            with self.assertRaisesRegex(compiler_manager.CompilerUpdateError,"SHA-256"):
                compiler_manager.install_wheel(wheel,version="9.0.0",sha256="0"*64)
            self.assertIsNone(compiler_manager.active_version())

    def test_unsafe_wheel_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{"HYTHON_HOME":directory}):
            wheel=Path(directory)/"candidate.whl"; digest=make_wheel(wheel,{"../escape.py":b"bad"})
            with self.assertRaisesRegex(compiler_manager.CompilerUpdateError,"안전하지 않은"):
                compiler_manager.install_wheel(wheel,version="9.0.0",sha256=digest)
            self.assertFalse((Path(directory)/"escape.py").exists())

    def test_install_activate_rollback_and_remove(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{"HYTHON_HOME":directory}):
            with patch.object(compiler_manager,"_smoke_test"):
                first=Path(directory)/"first.whl"; first_digest=make_wheel(first)
                compiler_manager.install_wheel(first,version="8.0.0",sha256=first_digest)
                second=Path(directory)/"second.whl"; second_digest=make_wheel(second)
                compiler_manager.install_wheel(second,version="9.0.0",sha256=second_digest)
            self.assertEqual(compiler_manager.active_version(),"9.0.0")
            self.assertEqual(compiler_manager.rollback(),"8.0.0")
            self.assertEqual(compiler_manager.active_version(),"8.0.0")
            self.assertEqual(compiler_manager.remove(),"8.0.0")
            self.assertIsNone(compiler_manager.active_version())

    def test_failed_smoke_test_preserves_active_version(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{"HYTHON_HOME":directory}):
            wheel=Path(directory)/"first.whl"; digest=make_wheel(wheel)
            with patch.object(compiler_manager,"_smoke_test"):
                compiler_manager.install_wheel(wheel,version="8.0.0",sha256=digest)
            bad=Path(directory)/"bad.whl"; bad_digest=make_wheel(bad)
            with patch.object(compiler_manager,"_smoke_test",side_effect=compiler_manager.CompilerUpdateError("실패")):
                with self.assertRaises(compiler_manager.CompilerUpdateError):
                    compiler_manager.install_wheel(bad,version="9.0.0",sha256=bad_digest)
            self.assertEqual(compiler_manager.active_version(),"8.0.0")
