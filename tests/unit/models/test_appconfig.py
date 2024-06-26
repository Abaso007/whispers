import re

import pytest

from whispers.core.constants import DEFAULT_SEVERITY
from whispers.core.utils import default_rules, list_rule_prop
from whispers.models.appconfig import AppConfig


def test_appconfig():
    config = AppConfig({})
    assert config.ast is False
    assert config.include.files == ["**/*"]
    assert config.include.rules == list_rule_prop("id", default_rules())
    assert config.include.severity == DEFAULT_SEVERITY
    assert config.exclude.files is None
    assert config.exclude.keys is None
    assert config.exclude.values is None
    assert config.exclude.rules == []
    assert config.exclude.severity == []


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        ({"ast": True}, True),
        ({"ast": False}, False),
        ({}, False),
    ],
)
def test_appconfig_ast(config, expected):
    config = AppConfig(config)
    assert config.ast is expected


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        ({"include": {"severity": ["Critical"]}, "exclude": {}}, ["Critical"]),
        ({"include": {}, "exclude": {}}, DEFAULT_SEVERITY),
    ],
)
def test_appconfig_severity(config, expected):
    config = AppConfig(config)
    assert config.include.severity == expected
    assert config.exclude.severity == []


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        ({"include": {}, "exclude": {"rules": ["rule-id"]}}, ["rule-id"]),
        ({"include": {}, "exclude": {}}, []),
    ],
)
def test_appconfig_rules(config, expected):
    config = AppConfig(config)
    assert config.include.rules == list_rule_prop("id", default_rules())
    assert config.exclude.rules == expected


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        ({"include": {"groups": ["group1"]}, "exclude": {}}, ["group1"]),
        ({"include": {}, "exclude": {}}, list_rule_prop("group", default_rules())),
    ],
)
def test_appconfig_groups(config, expected):
    config = AppConfig(config)
    assert config.include.groups == expected
    assert config.exclude.groups == []


def test_appconfig_compile():
    config = AppConfig({"exclude": {"files": ["test"]}})
    assert config.exclude.files == re.compile(r"test", flags=re.IGNORECASE)
    assert config.exclude.keys is None
    assert config.exclude.values is None
