import importlib
import sys
from unittest import TestCase
from unittest.mock import MagicMock, patch

from kipp.options import options as opt


class RunnerSecurityTestCase(TestCase):
    def setUp(self):
        opt.set_option("patch_utilities", lambda: None)
        opt._command_args = None
        if hasattr(opt, "_parser"):
            delattr(opt, "_parser")
        sys.modules.pop("kipp.runner.runner", None)

    def tearDown(self):
        for key in ["patch_utilities", "command", "command_args", "timeout"]:
            opt.del_option(key)
        sys.modules.pop("kipp.runner.runner", None)

    def test_setup_arguments_preserves_command_args(self):
        runner_mod = importlib.import_module("kipp.runner.runner")
        with patch("sys.argv", ["kipp_runner", "python", "-V"]):
            runner_mod.setup_arguments()
        self.assertEqual(opt.command, "python -V")
        self.assertEqual(opt.command_args, ["python", "-V"])

    def test_runner_executes_without_shell(self):
        runner_mod = importlib.import_module("kipp.runner.runner")
        opt.set_option("timeout", 0)
        process = MagicMock(returncode=0)
        process.communicate.return_value = ("", "")
        with patch.object(runner_mod, "RunStatsMonitor"), patch.object(runner_mod, "clean_monitor_logs"), patch.object(runner_mod, "catch_sys_quit_signal"), patch.object(runner_mod, "kill_process"), patch("kipp.runner.runner.subprocess.Popen", return_value=process) as popen:
            runner_mod.runner(["python", "-V"])
        self.assertEqual(popen.call_args[0][0], ["python", "-V"])
        self.assertFalse(popen.call_args[1]["shell"])
