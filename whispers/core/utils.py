import logging
import re
import string
from base64 import b64decode
from pathlib import Path
from typing import List, Optional, Pattern, Union

from jellyfish import jaro_winkler_similarity
from luhn import verify as luhn_verify
from yaml import safe_load, safe_load_all

from whispers.core.constants import DEFAULT_PATH, REGEX_ENVVAR, REGEX_IAC, REGEX_PATH, REGEX_URI
from whispers.models.pair import KeyValuePair


def global_exception_handler(file: Union[str, Path], data: str):
    """Global Exception Handler"""
    logging.exception(f"Failed parsing file '{str(file)}' with {data}")


def load_regex(regex: str, flags: Optional[re.RegexFlag] = 0) -> Pattern:
    """Try to compile a regex statement"""
    try:
        return re.compile(regex, flags=flags)

    except re.error:
        raise ValueError(f"Failed compiling RegEx: {regex}")


def load_yaml_from_file(filepath: Path) -> dict:
    """Safe load yaml from given file path"""
    ret = safe_load(filepath.read_text())
    return {} if not isinstance(ret, dict) else ret


def truncate_all_space(value: str) -> str:
    """Replace multiple space characters by a single space character"""
    return "" if not value else re.sub(r"\s+", " ", value)


def strip_string(value: str) -> str:
    """Strips leading and trailing quotes and spaces"""
    return "" if not value else value.strip(" '\"\n\r\t")


def simple_string(value: str) -> str:
    """Returns a simplified value for loose comparison"""
    if not value:
        return ""

    value = strip_string(value)  # Remove quotes
    value = value.rstrip("\\")  # Remove trailing backslashes
    value = value.lower()  # Lowercase
    value = re.sub(r"[^a-z0-9]", "_", value.strip())  # Simplify

    return value


def similar_strings(a: str, b: str) -> float:
    """Returns similarity coefficient between two strings"""
    a = simple_string(a).replace("_", "")
    b = simple_string(b).replace("_", "")

    return jaro_winkler_similarity(a, b)


def is_static(key: str, value: str) -> bool:
    """Check if pair is static"""
    if not isinstance(value, str):
        return False  # Not string

    if not value:
        return False  # Empty

    if value.lower() == "null":
        return False  # Empty

    if value.startswith("$") and "$" not in value[2:]:
        if REGEX_ENVVAR.match(value):
            return False  # Variable

    if value.startswith("%") and value.endswith("%"):
        return False  # Variable

    if value.startswith("${") and value.endswith("}"):
        return False  # Variable

    if value.startswith("{") and value.endswith("}"):
        if len(value) > 50:
            if is_base64_bytes(value[1:-1]):
                return True  # Token

        return False  # Variable

    if "{{" in value and "}}" in value:
        return False  # Variable

    if value.startswith("<") and value.endswith(">"):
        return False  # Placeholder

    if value.startswith("ENC[AES256_GCM,data:") and value.endswith("]"):
        return False  # Encrypted SOPS key

    s_key = simple_string(key)
    s_value = simple_string(value)

    if s_key == s_value:
        return False  # Placeholder

    if s_value.endswith(s_key):
        return False  # Placeholder

    return False if is_iac(value) else not is_path(value)


def is_ascii(data: str) -> bool:
    """Checks if given data is printable text"""
    if isinstance(data, bytes):
        try:
            data = data.decode("utf-8")
        except Exception:
            return False

    if not isinstance(data, (str, int)):
        return False

    return all(ch in string.printable for ch in str(data))


def is_base64(data: str) -> bool:
    """Checks if given data is base64-decodable to text"""
    if not isinstance(data, str):
        return False

    try:
        b64decode(data).decode("utf-8")
        return True

    except Exception:
        return False


def is_base64_bytes(data: str) -> bool:
    """Checks if given data is base64-decodable to bytes"""
    try:
        return b64decode(data) != b""

    except Exception:
        return False


def is_uri(data: str) -> bool:
    """Checks if given data resemples a URI"""
    if not is_ascii(data):
        return False

    if isinstance(data, int):
        return False

    if any(map(lambda ch: ch in data, string.whitespace)):
        return False

    return bool(REGEX_URI.match(data))


def is_path(data: str) -> bool:
    """Checks if given data resemples a system path"""
    if not is_ascii(data):
        return False

    return False if isinstance(data, int) else bool(REGEX_PATH.match(data))


def is_iac(data: str) -> bool:
    """Checks if given data resemples IaC function"""
    if not is_ascii(data):
        return False

    return False if isinstance(data, int) else bool(REGEX_IAC.match(data))


def is_luhn(data: str) -> bool:
    """Checks if given data resembles a credit card number"""
    if not is_ascii(data):
        return False

    return False if not data.isnumeric() else luhn_verify(data)


def is_similar(key: str, value: str, similarity: float) -> bool:
    """
    Checks similarity between key and value.
    Returns True if calculated similarity is greater than given similarity.
    """
    return similar_strings(key, value) >= similarity


def find_line_number(pair: KeyValuePair) -> int:
    """Finds line number using pair keypath and value"""
    if pair.line:
        return pair.line  # Already set

    valuepath = pair.value.split("\n")[0][:16]
    findpath = [*pair.keypath, valuepath]
    foundline = 0

    try:
        with Path(pair.file).open() as fh:
            for lineno, line in enumerate(fh, 1):
                founditems = 0

                for item in findpath:
                    if item not in line:
                        break

                    founditems += 1
                    foundline = lineno

                findpath = findpath[founditems:]

                if not findpath:
                    return foundline

    except Exception:  # pragma: no cover
        global_exception_handler(pair.file, "find_line_number()")

    return 0


def default_rules() -> List[dict]:
    """Read and parse builtin rules"""
    rules = []
    files = DEFAULT_PATH.joinpath("rules").glob("*.yml")
    for file in files:
        list(map(rules.extend, safe_load_all(file.read_text())))

    return rules


def list_rule_prop(prop: str, rules: List[dict]) -> List[str]:
    """List rule property given a list of rules"""
    return sorted(set(map(lambda rule: rule[prop], rules)))
