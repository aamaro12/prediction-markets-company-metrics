"""The command line states its version."""

import contextlib
import io
import unittest

from mef import __version__
from mef.cli import parser


class CliTests(unittest.TestCase):
    def test_the_version_is_printed(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            parser().parse_args(["--version"])
        self.assertEqual(out.getvalue().strip(), f"mef {__version__}")


if __name__ == "__main__":
    unittest.main()
