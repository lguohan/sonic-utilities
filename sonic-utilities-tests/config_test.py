import sys
import os
import mock
import pytest
import traceback
from click.testing import CliRunner
import sonic_device_util

test_path = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.dirname(test_path)
scripts_path = os.path.join(modules_path, "config")
sys.path.insert(0, modules_path)

os.environ["UTILITIES_UNIT_TESTING"] = "1"
import config.main as config

config.asic_type = mock.MagicMock(return_value = "broadcom")
config._get_device_type = mock.MagicMock(return_value = "ToRRouter")

class TestConfig(object):
    @classmethod
    def setup_class(cls):
        print("SETUP")
        os.environ["PATH"] += os.pathsep + scripts_path

    def test_feature(self):
        runner = CliRunner()
        result = runner.invoke(config.config.commands["feature"], ["sflow", "enabled"])
        assert result.exit_code == 0

    def test_unknown_feature(self):
        runner = CliRunner()
        result = runner.invoke(config.config.commands["feature"], ["foo", "enabled"])
        assert result.exit_code == 1

    def test_load_minigraph(self):
        sonic_device_util.get_num_npus = mock.MagicMock(return_value = 1)
        config._get_sonic_generated_services = mock.MagicMock(return_value = (["ntp-config.service", "swss.service"], []))
        runner = CliRunner()
        result = runner.invoke(config.config.commands["load_minigraph"], ["-y"])
        print result.output
        print result.exception
        traceback.print_tb(result.exc_info[2])
        print dir(result)
        assert 0
        assert result.exit_code == 0

    @classmethod
    def teardown_class(cls):
        print("TEARDOWN")
        os.environ["PATH"] = os.pathsep.join(os.environ["PATH"].split(os.pathsep)[:-1])
        os.environ["UTILITIES_UNIT_TESTING"] = "0"


