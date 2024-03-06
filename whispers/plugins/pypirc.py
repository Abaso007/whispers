from pathlib import Path
from typing import Iterator

from whispers.models.pair import KeyValuePair


class Pypirc:
    def pairs(self, filepath: Path) -> Iterator[KeyValuePair]:
        for lineno, line in enumerate(filepath.open(), 1):
            if "password:" not in line:
                continue

            if value := line.split("password:")[-1].strip():
                key = "pypi password"
                yield KeyValuePair(key, value, line=lineno)
