"""Unit tests for calc_dir_size."""

from __future__ import annotations

from pathlib import Path

import pytest

from proton_manager.scan.sizes import calc_dir_size


def test_empty_directory(tmp_path: Path) -> None:
    assert calc_dir_size(tmp_path) == 0


def test_single_file(tmp_path: Path) -> None:
    (tmp_path / "file.txt").write_bytes(b"x" * 100)
    assert calc_dir_size(tmp_path) == 100


def test_nested_files(tmp_path: Path) -> None:
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "a.bin").write_bytes(b"\x00" * 512)
    (sub / "b.bin").write_bytes(b"\x00" * 256)
    (sub / "c.bin").write_bytes(b"\x00" * 128)
    assert calc_dir_size(tmp_path) == 896


def test_symlinks_skipped(tmp_path: Path) -> None:
    real = tmp_path / "real.bin"
    real.write_bytes(b"\x00" * 400)
    link = tmp_path / "link.bin"
    link.symlink_to(real)
    # Should count real.bin only; symlink target must not be double-counted
    assert calc_dir_size(tmp_path) == 400


def test_nonexistent_path(tmp_path: Path) -> None:
    assert calc_dir_size(tmp_path / "no_such_dir") == 0


def test_file_path_returns_zero(tmp_path: Path) -> None:
    f = tmp_path / "file.txt"
    f.write_bytes(b"hello")
    # calc_dir_size only handles directories
    assert calc_dir_size(f) == 0
