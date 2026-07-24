import tempfile
import unittest
from pathlib import Path
from hython.bytecode import read
from hython.cli import main
from hython.vm import VM

class BuildCliTests(unittest.TestCase):
    def test_builds_project_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/"src"; output=root/"out"; source.mkdir()
            (source/"도구.hy").write_text("값 = 40\n",encoding="utf-8")
            (source/"main.hy").write_text("인폴트 도구\n결과 = 도구.값 + 2\n",encoding="utf-8")
            self.assertEqual(main(["빌드",str(source),"-o",str(output)]),0)
            vm=VM([output]); vm.run(read(output/"main.hbc"))
            self.assertEqual(vm.globals["결과"],42)
