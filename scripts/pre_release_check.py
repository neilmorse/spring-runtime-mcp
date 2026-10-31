#!/usr/bin/env python3
"""
Pre-Release Automated Gatekeeper (自动化交付自检门禁)
一键串联：Git 敏感信息扫描 -> AST 代码残骸与安全检查 -> 依赖与漏洞审计 -> 静态检查 -> 严格测试门禁 -> 净室构建与隔离安装验证
"""

from __future__ import annotations

import argparse
import ast
from email.parser import BytesParser
import re
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from dataclasses import dataclass
from pathlib import Path

# ─── 终端色彩与格式化 ──────────────────────────────────────────────────────────
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
DIM = "\033[2m"
RESET = "\033[0m"


@dataclass
class CheckResult:
    stage: str
    status: str  # "PASS", "WARN", "FAIL"
    summary: str
    details: str = ""


# ─── 高危凭证与未完成标记正则 ──────────────────────────────────────────────────
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "Private Key Header",
        re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |PGP )?PRIVATE KEY-----"),
    ),
    (
        "OpenAI / Anthropic Key",
        re.compile(r"\bsk-(?:proj-|ant-)?[a-zA-Z0-9_-]{32,}\b"),
    ),
    (
        "GitHub Token",
        re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}\b"),
    ),
    ("AWS Access Key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    (
        "Hardcoded Secret Assignment",
        re.compile(
            r"(?i)\b(?:api_key|secret_key|access_token|password|passwd|client_secret)\b"
            r"\s*[:=]\s*['\"][A-Za-z0-9_\-/.+=]{12,}['\"]"
        ),
    ),
]

ALLOWLIST_HINTS = (
    "example",
    "dummy",
    "mock",
    "placeholder",
    "your_",
    "xxx",
    "test_",
    "fake",
    "redact",
    "sanitize",
    "<",
    "***",
)


# ─── 辅助执行函数 ─────────────────────────────────────────────────────────────
def run_cmd(
    cmd: list[str], cwd: Path | None = None, timeout: int = 300
) -> tuple[int, str, str]:
    """安全运行外部子进程并返回 (returncode, stdout, stderr)"""
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"Command timed out after {timeout}s: {' '.join(cmd)}"


def get_tracked_files(root: Path) -> list[Path]:
    """获取 Git 追踪及未忽略的新文件（排除已删除文件）"""
    # Binary NUL framing preserves quoting, whitespace and non-decodable path bytes.
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=root,
            capture_output=True,
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OSError("无法列出 Git 跟踪文件") from exc
    if proc.returncode != 0:
        raise OSError("无法列出 Git 跟踪文件")
    return [
        root / os.fsdecode(name)
        for name in proc.stdout.split(b"\0")
        if name and (root / os.fsdecode(name)).is_file()
    ]


def find_source_dirs(root: Path) -> list[Path]:
    """自动探测生产源码目录（排除 tests, scripts, docs 等非核心生产目录）"""
    if (root / "src").is_dir():
        return [root / "src"]
    excluded = {
        "tests",
        "test",
        "scripts",
        "docs",
        "examples",
        "benchmarks",
        "dist",
        "build",
    }
    dirs = [
        d
        for d in root.iterdir()
        if d.is_dir()
        and not d.name.startswith(".")
        and d.name not in excluded
        and (d / "__init__.py").exists()
    ]
    return dirs if dirs else [root]


# ─── 阶段 1：Git 状态与敏感信息扫描 ─────────────────────────────────────────────
def check_git_and_secrets(root: Path, allow_dirty: bool) -> CheckResult:
    issues: list[str] = []
    warnings: list[str] = []

    # 1. 检查工作区是否干净
    code, out, _ = run_cmd(["git", "status", "--porcelain"], cwd=root)
    if code != 0:
        return CheckResult("1. Git & 敏感凭证扫描", "FAIL", "无法读取 Git 工作区状态")
    if out:
        changed_count = len(out.splitlines())
        msg = f"Git 工作区存在未提交或未追踪的变更 ({changed_count} 处)"
        if allow_dirty:
            warnings.append(msg)
        else:
            issues.append(
                f"{msg}（发布前请保持工作区干净，或开发自检时加 --allow-dirty）"
            )

    # 2. 内置正则扫描所有被 Git 追踪的文件
    script_self = Path(__file__).resolve()
    try:
        tracked_files = get_tracked_files(root)
    except OSError:
        return CheckResult("1. Git & 敏感凭证扫描", "FAIL", "无法列出 Git 跟踪文件")
    for file_path in tracked_files:
        if file_path.resolve() == script_self:
            continue
        rel = file_path.relative_to(root)
        if rel.name == ".env" or (
            rel.name.startswith(".env.") and rel.name != ".env.example"
        ):
            issues.append(f"发现被 Git 追踪的敏感环境文件: {rel}")
            continue

        # 判断是否为测试文件或测试夹具（如红队边界/脱敏单测）
        is_test_file = (
            "tests" in rel.parts
            or "test" in rel.parts
            or rel.name.startswith("test_")
            or "fixture" in rel.name.lower()
        )
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            issues.append(f"无法读取被 Git 跟踪的文件: {rel}")
            continue

        for line_no, line in enumerate(content.splitlines(), start=1):
            lower_line = line.lower()
            if any(hint in lower_line for hint in ALLOWLIST_HINTS):
                continue
            for rule_name, pattern in SECRET_PATTERNS:
                # 测试文件中常包含用于验证脱敏器的 PEM 头或伪造密钥赋值，予以豁免
                if is_test_file and rule_name in {
                    "Hardcoded Secret Assignment",
                    "Private Key Header",
                }:
                    continue
                if pattern.search(line):
                    issues.append(
                        f"[{rule_name}] {rel}:{line_no} -> 疑似硬编码敏感凭证"
                    )

    if issues:
        return CheckResult(
            "1. Git & 敏感凭证扫描",
            "FAIL",
            f"发现 {len(issues)} 项安全/状态阻断问题",
            "\n".join(issues[:15]),
        )
    if warnings:
        return CheckResult(
            "1. Git & 敏感凭证扫描", "WARN", warnings[0], "\n".join(warnings)
        )
    return CheckResult(
        "1. Git & 敏感凭证扫描",
        "PASS",
        "工作区干净，生产代码未发现敏感文件或硬编码密钥",
    )


# ─── 阶段 2：源码 AST 残骸与未实现分支审计 ──────────────────────────────────────
def check_code_readiness(root: Path) -> CheckResult:
    src_dirs = find_source_dirs(root)
    blockers: list[str] = []
    warnings: list[str] = []

    todo_pattern = re.compile(r"#\s*(TODO|FIXME|XXX|HACK)\b", re.IGNORECASE)
    script_self = Path(__file__).resolve()

    for src_dir in src_dirs:
        for py_file in src_dir.rglob("*.py"):
            if py_file.resolve() == script_self or "tests" in py_file.parts:
                continue
            rel = py_file.relative_to(root)
            source = py_file.read_text(encoding="utf-8", errors="ignore")

            for idx, line in enumerate(source.splitlines(), start=1):
                match = todo_pattern.search(line)
                if match:
                    warnings.append(
                        f"{rel}:{idx} 遗留未完成标记 ({match.group(1).upper()}): {line.strip()}"
                    )

            try:
                tree = ast.parse(source, filename=str(rel))
            except SyntaxError as exc:
                blockers.append(f"{rel}:{exc.lineno} 存在语法错误: {exc.msg}")
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id == "breakpoint":
                        blockers.append(
                            f"{rel}:{node.lineno} 生产代码遗留调试断点 breakpoint()"
                        )
                    elif (
                        isinstance(node.func, ast.Attribute)
                        and node.func.attr == "set_trace"
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id in {"pdb", "ipdb"}
                    ):
                        blockers.append(
                            f"{rel}:{node.lineno} 生产代码遗留调试断点 {node.func.value.id}.set_trace()"
                        )

                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    decorator_names = {
                        (
                            d.id
                            if isinstance(d, ast.Name)
                            else d.attr
                            if isinstance(d, ast.Attribute)
                            else ""
                        )
                        for d in node.decorator_list
                    }
                    if (
                        "abstractmethod" not in decorator_names
                        and not node.name.startswith("_")
                    ):
                        for sub in ast.walk(node):
                            if isinstance(sub, ast.Raise) and sub.exc is not None:
                                exc_name = ""
                                if isinstance(sub.exc, ast.Name):
                                    exc_name = sub.exc.id
                                elif isinstance(sub.exc, ast.Call) and isinstance(
                                    sub.exc.func, ast.Name
                                ):
                                    exc_name = sub.exc.func.id
                                if exc_name == "NotImplementedError":
                                    blockers.append(
                                        f"{rel}:{sub.lineno} 公开函数 `{node.name}` 仍抛出 NotImplementedError"
                                    )

    if blockers:
        return CheckResult(
            "2. 生产代码完备性审计",
            "FAIL",
            f"发现 {len(blockers)} 处伪实现或调试断点",
            "\n".join(blockers[:15]),
        )
    if warnings:
        return CheckResult(
            "2. 生产代码完备性审计",
            "WARN",
            f"无阻断项，但存在 {len(warnings)} 处 TODO/FIXME 标记",
            "\n".join(warnings[:10]),
        )
    return CheckResult(
        "2. 生产代码完备性审计",
        "PASS",
        "零伪实现、零残留断点、零语法异常",
    )


# ─── 阶段 3：依赖锁一致性、版本对齐与漏洞扫描 ──────────────────────────────────
def _package_version(root: Path, data: dict[str, object]) -> str:
    project = data.get("project", {})
    if not isinstance(project, dict):
        raise ValueError("无效的 project 配置")
    version = project.get("version")
    if isinstance(version, str) and version:
        return version
    if "version" not in project.get("dynamic", []):
        raise ValueError("缺少 project.version 声明")
    tool = data.get("tool", {})
    hatch = tool.get("hatch", {}) if isinstance(tool, dict) else {}
    version_config = hatch.get("version", {}) if isinstance(hatch, dict) else {}
    path = version_config.get("path") if isinstance(version_config, dict) else None
    if not isinstance(path, str):
        raise ValueError("缺少 Hatch 动态版本路径")
    version_file = (root / path).resolve()
    if not version_file.is_relative_to(root.resolve()):
        raise ValueError("动态版本路径超出项目目录")
    try:
        tree = ast.parse(version_file.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeError) as exc:
        raise ValueError("无法读取动态版本") from exc
    values = [
        node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__version__"
            for target in node.targets
        )
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
        and node.value.value
    ]
    if len(values) != 1:
        raise ValueError("动态版本必须有且仅有一个字符串 __version__")
    return values[0]


def check_dependencies_and_version(root: Path, *, audit: bool = False) -> CheckResult:
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return CheckResult("3. 依赖与版本一致性", "FAIL", "未找到 pyproject.toml")

    issues: list[str] = []
    warnings: list[str] = []

    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    build_system = data.get("build-system", {})
    groups = data.get("dependency-groups", {})
    build_requires = (
        build_system.get("requires", []) if isinstance(build_system, dict) else []
    )
    dev_requires = groups.get("dev", []) if isinstance(groups, dict) else []
    if (
        not isinstance(build_requires, list)
        or not build_requires
        or not isinstance(dev_requires, list)
        or any(
            not isinstance(item, str)
            or re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._-]*==[A-Za-z0-9][A-Za-z0-9.!+_-]*", item
            )
            is None
            or item not in dev_requires
            for item in build_requires
        )
    ):
        issues.append("构建依赖必须固定版本并纳入 dev 锁文件审计")
    try:
        pkg_version = _package_version(root, data)
    except ValueError as exc:
        pkg_version = None
        issues.append(str(exc))

    if pkg_version:
        version_regex = re.compile(
            r"^__version__\s*=\s*['\"]([^'\"]+)['\"]", re.MULTILINE
        )
        for src_dir in find_source_dirs(root):
            for py_file in src_dir.rglob("*.py"):
                m = version_regex.search(
                    py_file.read_text(encoding="utf-8", errors="ignore")
                )
                if m and m.group(1) != pkg_version:
                    rel = py_file.relative_to(root)
                    issues.append(
                        f"版本号不一致: pyproject.toml 为 {pkg_version}，但 {rel} 中 __version__ 为 {m.group(1)}"
                    )

    if (root / "uv.lock").exists():
        code, _, err = run_cmd(["uv", "lock", "--check", "--offline"], cwd=root)
        if code != 0:
            issues.append(
                f"uv.lock 与 pyproject.toml 不同步，请运行 `uv lock` 更新锁文件:\n{err}"
            )
    else:
        issues.append("未检测到 uv.lock 锁文件")

    if audit:
        code, out, err = run_cmd(["uv", "audit", "--locked"], cwd=root)
        if code != 0:
            issues.append(f"依赖漏洞审计失败或无法完成 (exit {code}):\n{out}\n{err}")
    else:
        warnings.append("未执行联网漏洞审计；使用 --audit 单独启用")

    if issues:
        return CheckResult(
            "3. 依赖与版本一致性",
            "FAIL",
            f"发现 {len(issues)} 项版本、锁文件或审计问题",
            "\n".join(issues),
        )
    if warnings:
        return CheckResult(
            "3. 依赖与版本一致性", "WARN", warnings[0], "\n".join(warnings)
        )
    return CheckResult(
        "3. 依赖与版本一致性",
        "PASS",
        f"版本号 ({pkg_version})、uv.lock 与漏洞审计通过",
    )


# ─── 阶段 4：静态质量门禁 (Ruff + Mypy) ───────────────────────────────────────
def check_static_quality(root: Path) -> CheckResult:
    errors: list[str] = []

    # 1. Ruff Lint
    r_code, r_out, r_err = run_cmd(
        ["uv", "run", "--no-sync", "ruff", "check", "."], cwd=root
    )
    if r_code != 0:
        errors.append(f"[Ruff Lint 失败]\n{r_out or r_err}")

    # 2. Ruff Format Check
    f_code, f_out, f_err = run_cmd(
        ["uv", "run", "--no-sync", "ruff", "format", "--check", "."], cwd=root
    )
    if f_code != 0:
        errors.append(
            f"[Ruff Format 未格式化 (可运行 `uv run ruff format .` 一键修复)]\n{f_out or f_err}"
        )

    c_code, c_out, c_err = run_cmd(
        ["uv", "run", "--no-sync", "python", "scripts/validate_tool_contract.py"],
        cwd=root,
    )
    if c_code != 0:
        errors.append(f"[工具契约失败]\n{c_out or c_err}")

    # 3. Mypy Type Check (智能识别 pyproject.toml 配置或 src 目录，规避 tests 命名空间冲突)
    pyproject = root / "pyproject.toml"
    mypy_cfg: dict[str, object] = {}
    if pyproject.exists():
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        mypy_cfg = data.get("tool", {}).get("mypy", {})

    if "files" in mypy_cfg or "packages" in mypy_cfg:
        mypy_cmd = ["uv", "run", "--no-sync", "mypy"]
    elif (root / "src").is_dir():
        mypy_cmd = ["uv", "run", "--no-sync", "mypy", "src"]
    else:
        mypy_cmd = ["uv", "run", "--no-sync", "mypy", "--explicit-package-bases", "."]

    m_code, m_out, m_err = run_cmd(mypy_cmd, cwd=root)
    if m_code != 0:
        errors.append(f"[Mypy 静态类型检查失败]\n{m_out or m_err}")

    if errors:
        return CheckResult(
            "4. 静态代码与类型门禁",
            "FAIL",
            "Ruff 或 Mypy 检查未通过",
            "\n\n".join(errors),
        )
    return CheckResult(
        "4. 静态代码与类型门禁",
        "PASS",
        "Ruff (Lint & Format) 与 Mypy 全部零警告通过",
    )


# ─── 阶段 5：严格测试门禁 (Pytest + 零 Skip 审计) ─────────────────────────────
def check_test_suite(root: Path, allow_skipped: bool) -> CheckResult:
    cmd = [
        "uv",
        "run",
        "--no-sync",
        "python",
        "-m",
        "pytest",
        "-q",
        "-ra",
        "--strict-markers",
    ]
    code, out, err = run_cmd(cmd, cwd=root, timeout=600)
    combined = f"{out}\n{err}".strip()

    if code != 0:
        return CheckResult(
            "5. 自动化测试门禁",
            "FAIL",
            f"Pytest 执行失败 (Exit Code {code})",
            combined[-1500:],
        )

    skip_match = re.search(r"(\d+)\s+skipped", combined)
    xfail_match = re.search(r"(\d+)\s+xfailed", combined)
    skipped_count = int(skip_match.group(1)) if skip_match else 0
    xfailed_count = int(xfail_match.group(1)) if xfail_match else 0

    if (skipped_count > 0 or xfailed_count > 0) and not allow_skipped:
        return CheckResult(
            "5. 自动化测试门禁",
            "FAIL",
            f"检测到 {skipped_count} skipped, {xfailed_count} xfailed（正式交付要求 0 skipped，或使用 --allow-skipped 放行）",
            combined.splitlines()[-1] if combined else "",
        )

    if skipped_count or xfailed_count:
        return CheckResult(
            "5. 自动化测试门禁",
            "WARN",
            f"测试含 {skipped_count} skipped、{xfailed_count} xfailed",
        )
    summary_line = combined.splitlines()[-1] if combined else "All tests passed"
    return CheckResult("5. 自动化测试门禁", "PASS", f"全量测试通过 ({summary_line})")


# ─── 阶段 6：净室构建与隔离环境安装验证 (Clean-Room Build & Install) ───────────
def check_clean_room_build(
    root: Path, *, output_dir: Path | None = None
) -> CheckResult:
    pyproject = root / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    if "build-system" not in data:
        return CheckResult(
            "6. 净室打包与安装验证",
            "WARN",
            "pyproject.toml 未配置 [build-system]，跳过构建测试",
        )

    with tempfile.TemporaryDirectory(prefix="pre_release_dist_") as tmp_dist:
        dist_path = Path(tmp_dist)

        b_code, b_out, b_err = run_cmd(
            ["uv", "build", "--offline", "--out-dir", str(dist_path)], cwd=root
        )
        if b_code != 0:
            return CheckResult(
                "6. 净室打包与安装验证",
                "FAIL",
                "uv build 构建失败",
                f"{b_out}\n{b_err}",
            )

        wheels = list(dist_path.glob("*.whl"))
        sdists = list(dist_path.glob("*.tar.gz"))
        if len(wheels) != 1 or len(sdists) != 1:
            return CheckResult(
                "6. 净室打包与安装验证", "FAIL", "需要恰好一个 wheel 和一个 sdist"
            )

        wheel_file = wheels[0]
        sdist_file = sdists[0]
        try:
            package_version = _package_version(root, data)
        except ValueError as exc:
            return CheckResult("6. 净室打包与安装验证", "FAIL", str(exc))

        # 精确按路径段检查 Wheel 内容，防止误把 tests/ 或 .env 打包进生产产物
        leaked_files: list[str] = []
        forbidden_parts = {".env", ".pytest_cache", "__pycache__", "tests", ".git"}
        with zipfile.ZipFile(wheel_file, "r") as zf:
            metadata_files = [
                name for name in zf.namelist() if name.endswith(".dist-info/METADATA")
            ]
            if (
                len(metadata_files) != 1
                or BytesParser().parsebytes(zf.read(metadata_files[0]))["Version"]
                != package_version
            ):
                return CheckResult(
                    "6. 净室打包与安装验证", "FAIL", "Wheel 版本与源码版本不一致"
                )
            package = root / "src/spring_runtime_mcp"
            required_resources = [
                package / "schemas/tools-contract.json",
                package / "py.typed",
                *(package / "replay_data").rglob("*.json"),
            ]
            for resource in required_resources:
                name = "spring_runtime_mcp/" + resource.relative_to(package).as_posix()
                if name not in zf.namelist() or zf.read(name) != resource.read_bytes():
                    return CheckResult(
                        "6. 净室打包与安装验证",
                        "FAIL",
                        "Wheel 缺少运行资源或资源与源码不一致",
                        name,
                    )
            for name in zf.namelist():
                parts = Path(name).parts
                if any(p in forbidden_parts for p in parts) or Path(
                    name
                ).name.startswith("test_"):
                    leaked_files.append(name)

        if leaked_files:
            return CheckResult(
                "6. 净室打包与安装验证",
                "FAIL",
                f"构建产物 {wheel_file.name} 中混入了不应发布的测试或缓存文件",
                "\n".join(leaked_files[:15]),
            )

        try:
            with tarfile.open(sdist_file, "r:gz") as archive:
                members = archive.getmembers()
                metadata = [
                    m
                    for m in members
                    if len(Path(m.name).parts) == 2
                    and Path(m.name).name == "PKG-INFO"
                    and m.isfile()
                ]
                if len(metadata) != 1:
                    return CheckResult(
                        "6. 净室打包与安装验证", "FAIL", "sdist 缺少唯一包元数据"
                    )
                metadata_stream = archive.extractfile(metadata[0])
                if (
                    metadata_stream is None
                    or BytesParser().parsebytes(metadata_stream.read())["Version"]
                    != package_version
                ):
                    return CheckResult(
                        "6. 净室打包与安装验证", "FAIL", "sdist 版本与源码版本不一致"
                    )
                prefix = Path(metadata[0].name).parts[0]
                for resource in required_resources:
                    name = f"{prefix}/src/spring_runtime_mcp/{resource.relative_to(package).as_posix()}"
                    try:
                        member = archive.getmember(name)
                        resource_stream = (
                            archive.extractfile(member) if member.isfile() else None
                        )
                    except KeyError:
                        resource_stream = None
                    if (
                        resource_stream is None
                        or resource_stream.read() != resource.read_bytes()
                    ):
                        return CheckResult(
                            "6. 净室打包与安装验证",
                            "FAIL",
                            "sdist 缺少运行资源或资源与源码不一致",
                            name,
                        )
                forbidden_sdist = {
                    ".git",
                    ".venv",
                    ".pytest_cache",
                    "__pycache__",
                    "target",
                    "dist",
                    "build",
                }
                for member in members:
                    parts = Path(member.name).parts
                    name = Path(member.name).name
                    if (
                        forbidden_sdist.intersection(parts)
                        or name == ".env"
                        or (name.startswith(".env.") and name != ".env.example")
                        or member.name.endswith(".jar")
                        or Path(member.name).is_absolute()
                        or ".." in parts
                        or member.issym()
                        or member.islnk()
                    ):
                        return CheckResult(
                            "6. 净室打包与安装验证",
                            "FAIL",
                            "sdist 混入缓存、构建产物或敏感环境文件",
                            member.name,
                        )
        except (OSError, tarfile.TarError):
            return CheckResult("6. 净室打包与安装验证", "FAIL", "无法读取 sdist")

        constraints = dist_path / "runtime-constraints.txt"
        e_code, e_out, e_err = run_cmd(
            [
                "uv",
                "export",
                "--frozen",
                "--offline",
                "--no-dev",
                "--no-editable",
                "--no-emit-project",
                "--no-hashes",
                "-o",
                str(constraints),
            ],
            cwd=root,
        )
        if e_code != 0:
            return CheckResult(
                "6. 净室打包与安装验证",
                "FAIL",
                "无法从锁文件导出运行依赖约束",
                f"{e_out}\n{e_err}",
            )

        for distribution in (wheel_file, sdist_file):
            with tempfile.TemporaryDirectory(prefix="pre_release_venv_") as tmp_venv:
                venv_dir = Path(tmp_venv) / "venv"
                v_code, _, v_err = run_cmd(["uv", "venv", str(venv_dir)], cwd=dist_path)
                if v_code != 0:
                    return CheckResult(
                        "6. 净室打包与安装验证",
                        "FAIL",
                        "无法创建隔离验证虚拟环境",
                        v_err,
                    )

                python_bin = venv_dir / (
                    "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
                )
                i_code, _, i_err = run_cmd(
                    [
                        "uv",
                        "pip",
                        "install",
                        "--python",
                        str(python_bin),
                        "--offline",
                        "-c",
                        str(constraints),
                        str(distribution),
                    ],
                    cwd=dist_path,
                )
                if i_code != 0:
                    return CheckResult(
                        "6. 净室打包与安装验证",
                        "FAIL",
                        f"在纯净虚拟环境中安装 {distribution.name} 失败",
                        i_err,
                    )

                scripts = data.get("project", {}).get("scripts", {})
                for _, entrypoint in scripts.items():
                    module_name = entrypoint.split(":")[0]
                    imp_code, _, imp_err = run_cmd(
                        [str(python_bin), "-c", f"import {module_name}"],
                        cwd=Path(tmp_venv),
                    )
                    if imp_code != 0:
                        return CheckResult(
                            "6. 净室打包与安装验证",
                            "FAIL",
                            f"隔离环境下无法导入 CLI 入口模块 `{module_name}`",
                            imp_err,
                        )

                entrypoint_bin = python_bin.with_name(
                    "spring-runtime-mcp.exe"
                    if sys.platform == "win32"
                    else "spring-runtime-mcp"
                )
                version_code, version_out, version_err = run_cmd(
                    [str(entrypoint_bin), "--version"], cwd=Path(tmp_venv)
                )
                if (
                    version_code != 0
                    or version_out != f"spring-runtime-mcp {package_version}"
                ):
                    return CheckResult(
                        "6. 净室打包与安装验证",
                        "FAIL",
                        "CLI 版本与源码版本不一致",
                        version_err,
                    )
                gate_code, gate_out, gate_err = run_cmd(
                    [
                        str(python_bin),
                        "-I",
                        str(root / "scripts/check_stdio_install.py"),
                        "--command",
                        str(entrypoint_bin),
                    ],
                    cwd=Path(tmp_venv),
                    timeout=180,
                )
                if gate_code != 0:
                    return CheckResult(
                        "6. 净室打包与安装验证",
                        "FAIL",
                        "安装后的 MCP 协议/八工具路由/replay 验证失败",
                        f"{gate_out}\n{gate_err}",
                    )

        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            if list(output_dir.iterdir()):
                return CheckResult(
                    "6. 净室打包与安装验证", "FAIL", "产物输出目录必须为空"
                )
            for distribution in (wheel_file, sdist_file):
                shutil.copyfile(distribution, output_dir / distribution.name)

        return CheckResult(
            "6. 净室打包与安装验证",
            "PASS",
            "Wheel 与 sdist 资源完整，分别完成净室 MCP 握手/八工具 HTTP 路由/7 场景 replay",
        )


# ─── 主控流程 ─────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(
        description="执行项目正式交付前的全链路自动化质量与安全核验。"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="项目根目录路径 (默认当前目录)",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="允许 Git 工作区存在未提交变更",
    )
    parser.add_argument(
        "--allow-skipped",
        action="store_true",
        help="允许 Pytest 存在 skipped/xfailed 用例",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="跳过阶段 6 的净室打包验证",
    )
    parser.add_argument("--audit", action="store_true", help="执行联网 uv 漏洞审计")
    parser.add_argument(
        "--output-dir", type=Path, help="保留已验证的两个发布产物（目录必须为空）"
    )
    args = parser.parse_args()

    root = args.root.resolve()
    print(
        f"\n{BOLD}{CYAN}🚀 启动交付前全链路自动化门禁 (Pre-Release Gatekeeper){RESET}"
    )
    print(f"{DIM}目标仓库: {root}{RESET}\n" + "─" * 72)

    pipeline = [
        (
            "1. Git & 敏感凭证扫描",
            lambda: check_git_and_secrets(root, args.allow_dirty),
        ),
        ("2. 生产代码完备性审计", lambda: check_code_readiness(root)),
        (
            "3. 依赖与版本一致性",
            lambda: check_dependencies_and_version(root, audit=args.audit),
        ),
        ("4. 静态代码与类型门禁", lambda: check_static_quality(root)),
        (
            "5. 自动化测试门禁",
            lambda: check_test_suite(root, args.allow_skipped),
        ),
    ]
    if not args.skip_build:
        pipeline.append(
            (
                "6. 净室打包与安装验证",
                lambda: check_clean_room_build(root, output_dir=args.output_dir),
            )
        )
    else:
        pipeline.append(
            (
                "6. 净室打包与安装验证",
                lambda: CheckResult(
                    "6. 净室打包与安装验证", "WARN", "已跳过净室构建，检查不完整"
                ),
            )
        )

    results: list[CheckResult] = []
    try:
        for stage_name, step_fn in pipeline:
            print(
                f"{DIM}[ RUN  ] {stage_name:<24} │ 正在核验中，请稍候...{RESET}",
                end="\r",
                flush=True,
            )
            res = step_fn()
            results.append(res)
            badge = (
                f"{GREEN}[ PASS ]{RESET}"
                if res.status == "PASS"
                else f"{YELLOW}[ WARN ]{RESET}"
                if res.status == "WARN"
                else f"{RED}[ FAIL ]{RESET}"
            )
            # 清除进度行并打印结果
            print(f"\r\033[K{badge} {BOLD}{res.stage:<24}{RESET} │ {res.summary}")
            if res.details and res.status in {"FAIL", "WARN"}:
                indented = "\n".join(
                    f"         {DIM}┆{RESET} {line}"
                    for line in res.details.splitlines()
                )
                print(indented)
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}⚠️  用户手动中断了自检流程 (KeyboardInterrupt)。{RESET}\n")
        return 130

    print("─" * 72)
    failed = [r for r in results if r.status == "FAIL"]
    warned = [r for r in results if r.status == "WARN"]

    if failed:
        print(
            f"{BOLD}{RED}❌ 交付门禁未通过：{len(failed)} 个阶段阻断，{len(warned)} 个警告。请修复上述问题后再发布！{RESET}\n"
        )
        return 1

    if warned:
        print(
            f"{BOLD}{YELLOW}⚠️ 检查不完整或存在 {len(warned)} 项警告，不能据此确认可发布。{RESET}\n"
        )
        return 2
    print(f"{BOLD}{GREEN}✅ 所有 {len(results)} 个交付检查通过。{RESET}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
