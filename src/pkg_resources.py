from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


class DistributionNotFound(PackageNotFoundError):
    pass


class _Distribution:
    def __init__(self, dist_version: str) -> None:
        self.version = dist_version


def get_distribution(name: str) -> _Distribution:
    try:
        return _Distribution(version(name))
    except PackageNotFoundError as exc:
        raise DistributionNotFound(name) from exc
