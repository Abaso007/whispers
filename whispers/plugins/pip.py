from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse

from whispers.models.pair import KeyValuePair


class Pip:
    def pairs(self, filepath: Path) -> Iterator[KeyValuePair]:
        for lineno, line in enumerate(filepath.open(), 1):
            if "http" not in line:
                continue

            if value := urlparse(line.split("=")[-1].strip()).password:
                key = "pip password"
                yield KeyValuePair(key, value, line=lineno)
