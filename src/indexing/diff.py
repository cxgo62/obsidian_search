from __future__ import annotations

from pathlib import Path


def compute_file_diff(current: dict[str, str], existing: dict[str, str]) -> dict[str, list[str]]:
    current_paths = set(current)
    existing_paths = set(existing)
    added = sorted(current_paths - existing_paths)
    deleted = sorted(existing_paths - current_paths)
    modified = sorted([p for p in (current_paths & existing_paths) if current[p] != existing[p]])
    return {"added": added, "modified": modified, "deleted": deleted}


def collect_markdown_files(
    vault_path: Path,
    include_glob: list[str],
    exclude_glob: list[str],
    exclude_dirs: list[str] | None = None,
) -> list[Path]:
    exclude_dirs = exclude_dirs or []
    excluded_roots = _normalize_exclude_dirs(vault_path, exclude_dirs)
    out: list[Path] = []
    for pattern in include_glob:
        out.extend(vault_path.glob(pattern))
    unique: list[Path] = []
    for p in sorted(set(out)):
        if not p.is_file():
            continue
        if is_path_excluded(p, vault_path, exclude_glob, exclude_dirs):
            continue
        unique.append(p)
    return unique


def is_path_excluded(path: Path, vault_path: Path, exclude_glob: list[str], exclude_dirs: list[str] | None = None) -> bool:
    exclude_dirs = exclude_dirs or []
    excluded_roots = _normalize_exclude_dirs(vault_path, exclude_dirs)
    if any(_path_in_dir(path, root) for root in excluded_roots):
        return True
    rel = str(path.relative_to(vault_path))
    return any(path.match(pattern) or rel.startswith(pattern.replace("**/", "").replace("/**", "")) for pattern in exclude_glob)


def _normalize_exclude_dirs(vault_path: Path, exclude_dirs: list[str]) -> list[Path]:
    vault_root = vault_path.resolve()
    roots: list[Path] = []
    for raw in exclude_dirs:
        if not raw:
            continue
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = vault_path / p
        resolved = p.resolve()
        try:
            resolved.relative_to(vault_root)
        except ValueError:
            continue
        roots.append(resolved)
    return roots


def _path_in_dir(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory)
        return True
    except ValueError:
        return False
