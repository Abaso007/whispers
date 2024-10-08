import re
from pathlib import Path

import pytest

from tests.unit.conftest import FIXTURE_PATH, config_path, fixture_path, forbidden_path, tmp_path
from whispers.core.args import parse_args
from whispers.core.config import load_config
from whispers.core.pairs import filter_included, filter_static, load_plugin, make_pairs, tag_file
from whispers.models.pair import KeyValuePair
from whispers.plugins.config import Config
from whispers.plugins.dockercfg import Dockercfg
from whispers.plugins.dockerfile import Dockerfile
from whispers.plugins.html import Html
from whispers.plugins.htpasswd import Htpasswd
from whispers.plugins.jproperties import Jproperties
from whispers.plugins.json import Json
from whispers.plugins.npmrc import Npmrc
from whispers.plugins.pip import Pip
from whispers.plugins.plaintext import Plaintext
from whispers.plugins.pypirc import Pypirc
from whispers.plugins.semgrep import Semgrep
from whispers.plugins.shell import Shell
from whispers.plugins.xml import Xml
from whispers.plugins.yml import Yml


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        (tmp_path("File.404"), 0),
        (forbidden_path(), 0),
        (fixture_path("language.py2"), 0),
        (fixture_path(".npmrc"), 5),
        (fixture_path("placeholders.xml"), 0),
        (fixture_path("privatekey.pem"), 1),
        (fixture_path("putty.ppk"), 0),
    ],
)
def test_make_pairs(filename, expected):
    args = parse_args(["-c", config_path("exclude_values.yml"), filename])
    config = load_config(args)
    pairs = list(make_pairs(config, Path(filename)))
    assert len(pairs) == expected


def test_tag_file():
    pair = KeyValuePair("key", "value", file="")
    assert tag_file(FIXTURE_PATH, pair).file == fixture_path()


@pytest.mark.parametrize(
    ("key", "value", "expected"),
    [
        ("is", "included", KeyValuePair("is", "included", ["is"])),
        ("is_not", "included", None),
        ("is", "excluded", None),
    ],
)
def test_filter_included(key, value, expected):
    args = parse_args([fixture_path()])
    config = load_config(args)
    config.exclude.keys = re.compile(r"is_not")
    config.exclude.values = re.compile(r"excluded")
    pair = KeyValuePair(key, value, [key])
    assert filter_included(config, pair) == expected


@pytest.mark.parametrize(
    ("xkeys", "xvalues", "expected"),
    [
        (re.compile(r"is_not"), re.compile(r"excluded"), type(None)),
        (None, re.compile(r"excluded"), type(None)),
        (re.compile(r"is_not"), None, type(None)),
        (None, None, KeyValuePair),
    ],
)
def test_filter_included_config(xkeys, xvalues, expected):
    args = parse_args([fixture_path()])
    config = load_config(args)
    config.exclude.keys = xkeys
    config.exclude.values = xvalues
    pair = KeyValuePair("is_not", "excluded", ["is_not"])
    result = filter_included(config, pair)
    assert isinstance(result, expected)


@pytest.mark.parametrize(
    ("key", "value", "expected"),
    [
        ("aws_secret", "${aws_secret}", None),
        ("thesame", "THESAME", None),
        ("is", "static", KeyValuePair("is", "static")),
    ],
)
def test_filter_static(key, value, expected):
    pair = KeyValuePair(key, value)
    assert filter_static(pair) == expected


@pytest.mark.parametrize(
    ("filename", "ast", "expected"),
    [
        ("", False, None),
        ("File.404", False, None),
        (".aws/credentials", False, Config),
        (".dockercfg", False, Dockercfg),
        (".env", False, Shell),
        (".gitlab-ci.yml", False, Yml),
        (".htpasswd", False, Htpasswd),
        (".npmrc", False, Npmrc),
        (".pypirc", False, Pypirc),
        ("apikeys.json", False, Json),
        ("apikeys.xml", False, Xml),
        ("apikeys.yml", False, Yml),
        ("beans.xml.dist", False, Xml),
        ("beans.xml.template", False, Xml),
        ("beans.xml", False, Xml),
        ("cloudformation.yml", False, Yml),
        ("connection.config", False, Config),
        ("Dockerfile", False, Dockerfile),
        ("integration.conf", False, Config),
        ("invalid.json", False, Json),
        ("invalid.yml", False, Yml),
        ("invalid.ini", False, Config),
        ("java.properties", False, Jproperties),
        ("language/fixture.py", True, Semgrep),
        ("language/fixture.py", False, None),
        ("language/fixture.sh", False, Shell),
        ("nginx.conf", False, Config),
        ("page.html", False, Html),
        ("passwords.yml", False, Yml),
        ("pip.conf", False, Pip),
        ("plaintext.txt", False, Plaintext),
        ("settings01.ini", False, Config),
        ("settings02.ini", False, Config),
        ("settings.cfg", False, Config),
        ("settings.env", False, Shell),
    ],
)
def test_load_plugin(filename, ast, expected):
    plugin = load_plugin(FIXTURE_PATH.joinpath(filename), ast=ast)
    assert plugin == expected
