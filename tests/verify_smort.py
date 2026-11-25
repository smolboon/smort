#!/usr/bin/env python3
"""Comprehensive 16-suite zero-dependency verification harness for smort.md (v7 · 2026-11-25.v11).
Tests:
  1. Extraction (32 blocks), syntax, stdlib-only compliance, STOP-READING guard, cross-refs, placeholders, collision safety
  2. Hot/Cold context budgets (PROGRAM.md <= 5 KB, sharded handoffs/*.md, Week-2 headroom) & ratchets
  3. Base-ref auto-resolution across Git topologies (_smort_lib.py)
  4. Unbounded cohesive tickets & parallel hardened gate (--fail-fast, --sequential, smart gitleaks, --verify-red-cmd)
  5. touch-set-check & hardened fake-work-scan (BASE..HEAD intermediate-commit history & Shannon-entropy secrets)
  6. tasks-index full §5 delegation & batched git cat-file --batch live overlay
  7. project-map & live --section reading docs/PLAYBOOK.md & docs/OPERATIONS.md
  8. code-index polyglot/monorepo, (mtime_ns,size) no-op cache, compact JSON, tsconfig paths/barrels, scoped affected, comment-safe bypass
  9. ci-guard 2/4-space YAML, block scalars & expression timeouts
 10. claim-check & starter verify/claims.json
 11. conflict-matrix parallel merge-tree, sound disjoint-path pre-filter, spaces, worktree cache & timestamps
 12. gate-brief (M0, --max-prs 5, Risk-Sliced A1 Review Maps, JSON manifest) & lessons-reflect (O(log K) compact + Git --as-of)
 13. smort-resume 1-call role-tailored startup packet, topic filter, redaction & not_shown
 14. slot-apply deterministic reply parsing, unverified guard, --dry-run & --execute (merges, ADRs, toggles, receipt)
 15. install-hooks mechanical .githooks pre-commit secret block & pre-push main protection
 16. End-to-end smort v7 lifecycle smoke (extract -> hooks -> resume -> red/green gate -> brief -> slot-apply)"""
import ast
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SMORT_MD = REPO_ROOT / "smort.md"


def run(cmd, cwd, env=None, check=False, input_text=None):
    merged_env = os.environ.copy()
    merged_env.setdefault("GIT_AUTHOR_NAME", "Smort Tester")
    merged_env.setdefault("GIT_AUTHOR_EMAIL", "tester@example.com")
    merged_env.setdefault("GIT_COMMITTER_NAME", "Smort Tester")
    merged_env.setdefault("GIT_COMMITTER_EMAIL", "tester@example.com")
    if env:
        merged_env.update(env)
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        env=merged_env,
        input=input_text,
        capture_output=True,
        text=True,
        check=check,
    )


def extract_smort(dest: Path) -> int:
    src = SMORT_MD.read_text(encoding="utf-8")
    for d in (
        "tasks/archive",
        "changes",
        "docs/decisions",
        "handoffs",
        "verify/conflicts",
        "verify/logs",
        "verify/lessons",
        "scripts/verify",
    ):
        (dest / d).mkdir(parents=True, exist_ok=True)
    fence = "~" * 4
    pat = re.compile(
        rf"^### [78]\.\d+ `([^`]+)`[^\n]*\n\n{fence}[a-z]*\n(.*?)\n{fence}",
        re.M | re.S,
    )
    count = 0
    for m in pat.finditer(src):
        target = dest / m.group(1)
        out = target if not target.exists() else Path(f"{target}.smort-new")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(m.group(2) + "\n", encoding="utf-8")
        if m.group(1).startswith("scripts/verify/"):
            out.chmod(out.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        count += 1
    return count


def init_git_repo(work: Path, bare: Path | None = None, default_branch: str = "main"):
    run(["git", "init", "-b", default_branch], work, check=True)
    run(["git", "config", "user.name", "Smort Tester"], work, check=True)
    run(["git", "config", "user.email", "tester@example.com"], work, check=True)
    (work / ".gitignore").write_text("verify/logs/\nverify/code-index*.json\n.env\n", encoding="utf-8")
    if bare is not None:
        run(["git", "init", "--bare", str(bare)], bare.parent, check=True)
        run(["git", "remote", "add", "origin", str(bare)], work, check=True)


def commit_all(work: Path, msg: str, env=None) -> str:
    run(["git", "add", "-A"], work, check=True)
    run(["git", "commit", "-m", msg], work, env=env, check=True)
    return run(["git", "rev-parse", "HEAD"], work, check=True).stdout.strip()


def make_task(
    tid: str,
    title: str = "Sample task",
    approval: str = "A0",
    lane: str = "backend",
    priority: str = "P1",
    estimate: str = "M",
    status: str = "ready",
    constituents: list[str] | None = None,
    depends_on: list[str] | None = None,
    touch_set: list[str] | None = None,
    contract_only: bool = False,
    approval_reason: str = "none",
) -> str:
    consts = ", ".join(constituents or ["S1.C1"])
    deps = ", ".join(depends_on or [])
    ts_lines = "\n".join(f"  - {p}" for p in (touch_set or ["src/core/domain/**"]))
    return f"""---
id: {tid}
title: {title}
feature: F-001
constituents: [{consts}]
domain: 1 Correctness & Soundness
traces_to: [FR-001]
lane: {lane}
approval: {approval}
approval_reason: {approval_reason}
priority: {priority}
estimate: {estimate}
depends_on: [{deps}]
contract_only: {str(contract_only).lower()}
touch_set:
{ts_lines}
regenerate:
  - none
flag: none
status: {status}
claim: none
pr: none
---

## Context
Test task {tid}.
"""


# ---------------------------------------------------------------------------
# Suite 1: Extraction (32 blocks), Syntax, Zero-Dep, STOP-READING, Cross-Refs
# ---------------------------------------------------------------------------
def suite_1_extraction_and_static_checks():
    src = SMORT_MD.read_text(encoding="utf-8")
    assert "Template version: 2026-11-25.v11" in src
    assert "TOKEN-BUDGET DIRECTIVE — STOP READING AT" in src[:1500]
    assert "<!-- SMORT-STOP-READING-HERE -->" in src
    assert len(re.findall(r"^~~~~", src, re.M)) == 64, "Expected 64 ~~~~ fence markers"

    for bad in ("{{400}}", "{{800}}", "{{MAX_GATE_LINES}}", "{{5}}", "{{45}}", "{{T2}}", "2026-11-25.v10", "smort v6"):
        assert bad not in src, f"Stale placeholder/version {bad} still present in smort.md"
    assert not re.search(r"PROGRAM\.md\s*§[2-8]", src), "Stale PROGRAM.md §2-§8 ref still present in smort.md"

    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        ext_match = re.search(r"### 4\.1 .*?```bash\n(.*?)\n```", src, re.S)
        assert ext_match, "Missing §4.1 extractor block"
        r = run(["bash", "-c", ext_match.group(1)], work, env={"SMORT_FILE": str(SMORT_MD)})
        assert r.returncode == 0, f"§4.1 extractor failed:\n{r.stdout}\n{r.stderr}"
        assert "extracted 32 smort v7 files" in r.stdout

        expected_files = [
            "AGENTS.md", "PROGRAM.md", "PROJECT-MAP.md", "TASKS.md", "PRD.md",
            "ARCHITECTURE-TDD.md", "AUDIT.md", "AUDIT-LOG.md",
            "DEVELOPMENT-WORKFLOW.md", "HANDOFF.md", "docs/PLAYBOOK.md", "docs/OPERATIONS.md",
            "scripts/verify/_smort_lib.py", "scripts/verify/gate",
            "scripts/verify/touch-set-check", "scripts/verify/fake-work-scan",
            "scripts/verify/ratchet-check", "scripts/verify/tasks-index",
            "scripts/verify/project-map", "scripts/verify/code-index",
            "scripts/verify/conflict-matrix", "scripts/verify/gate-brief",
            "scripts/verify/lessons-reflect", "scripts/verify/project-checks.sh",
            "scripts/verify/ci-guard", "scripts/verify/claim-check",
            "scripts/verify/smort-resume", "scripts/verify/slot-apply",
            "scripts/verify/install-hooks",
            "verify/ratchet.json", "verify/claims.json", "verify/budgets.json",
        ]
        assert len(expected_files) == 32
        for rel in expected_files:
            p = work / rel
            assert p.is_file(), f"Missing extracted file: {rel}"
            if rel.startswith("scripts/verify/"):
                assert os.access(p, os.X_OK), f"Script not executable: {rel}"

        stdlib = set(sys.stdlib_module_names) | {"_smort_lib"}
        for p in sorted((work / "scripts/verify").iterdir()):
            txt = p.read_text(encoding="utf-8")
            assert '.lstrip("./")' not in txt and ".lstrip('./')" not in txt, f"Dotfile lstrip bug in {p.name}"
            if txt.startswith("#!/usr/bin/env python3"):
                tree = ast.parse(txt, filename=p.name)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for a in node.names:
                            assert a.name.split(".")[0] in stdlib, f"Non-stdlib import {a.name} in {p.name}"
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        assert node.module.split(".")[0] in stdlib, f"Non-stdlib from-import {node.module} in {p.name}"
            elif txt.startswith("#!/usr/bin/env bash"):
                bn = run(["bash", "-n", str(p)], work)
                assert bn.returncode == 0, f"bash -n failed for {p.name}: {bn.stderr}"

        for jf in ("verify/ratchet.json", "verify/claims.json", "verify/budgets.json"):
            json.loads((work / jf).read_text(encoding="utf-8"))

        stale_rx = re.compile(r"(?:AGENTS\.md\s*(?:§|:)(?:5|6\.[1-9]|7|8|9|10|2\.4)|PROGRAM\.md\s*§[2-8])")
        for rel in expected_files:
            if rel.endswith((".md", ".json")):
                hits = stale_rx.findall((work / rel).read_text(encoding="utf-8"))
                assert not hits, f"Stale cross-ref(s) in {rel}: {hits}"

        (work / "AGENTS.md").write_text("CUSTOM OWNER CONTENT\n", encoding="utf-8")
        r2 = run(["bash", "-c", ext_match.group(1)], work, env={"SMORT_FILE": str(SMORT_MD)})
        assert r2.returncode == 0
        assert (work / "AGENTS.md").read_text(encoding="utf-8") == "CUSTOM OWNER CONTENT\n"
        assert (work / "AGENTS.md.smort-new").is_file()


# ---------------------------------------------------------------------------
# Suite 2: Hot/Cold Context Budgets (PROGRAM.md <= 5 KB), Sharded Handoffs & Ratchets
# ---------------------------------------------------------------------------
def suite_2_hot_set_and_ratchets():
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        assert extract_smort(work) == 32

        # Day-1 hot set passes and is dramatically slimmed (< 28 KB; PROGRAM.md <= 5 KB)
        r = run(["scripts/verify/ratchet-check", "--verify-config", "--budgets", "verify/budgets.json", "--check-hot-set", "--json"], work)
        assert r.returncode == 0, f"Day-1 hot set failed:\n{r.stdout}\n{r.stderr}"
        rep_d1 = json.loads(r.stdout)
        assert rep_d1["files"]["AGENTS.md"]["bytes"] <= 20480
        assert rep_d1["files"]["PROGRAM.md"]["bytes"] <= 5120, f"PROGRAM.md too large: {rep_d1['files']['PROGRAM.md']['bytes']}"
        assert rep_d1["total_bytes"] < 28000, f"Day-1 Hot Set expected < 28 KB, got {rep_d1['total_bytes']}"

        # Negative control: bloating PROGRAM.md > 5120 B fails hot-set budget check
        orig_prog = (work / "PROGRAM.md").read_text(encoding="utf-8")
        (work / "PROGRAM.md").write_text(orig_prog + ("x" * 6000) + "\n", encoding="utf-8")
        r_pb = run(["scripts/verify/ratchet-check", "--budgets", "verify/budgets.json", "--check-hot-set"], work)
        assert r_pb.returncode == 1 and "PROGRAM.md bytes" in r_pb.stdout
        (work / "PROGRAM.md").write_text(orig_prog, encoding="utf-8")

        # Week-2 worst-case stress: full 4096 B HANDOFF + full 8192 B LESSONS + valid shard
        (work / "HANDOFF.md").write_text(("x" * 70 + "\n") * 55, encoding="utf-8")
        (work / "verify/LESSONS.md").write_text(("# L\n" + ("y" * 79 + "\n") * 102)[:8192], encoding="utf-8")
        (work / "handoffs/builder-a.md").write_text("Active: T-001\n" * 20, encoding="utf-8")
        r_w2 = run(["scripts/verify/ratchet-check", "--budgets", "verify/budgets.json", "--check-hot-set", "--json"], work)
        assert r_w2.returncode == 0, f"Week-2 worst-case Hot Set failed:\n{r_w2.stdout}\n{r_w2.stderr}"
        rep = json.loads(r_w2.stdout)
        assert rep["total_bytes"] < 42000, f"Week-2 total bytes {rep['total_bytes']} >= 42000"
        assert rep["total_est_tokens"] < 12000, f"Week-2 tokens {rep['total_est_tokens']} >= 12000"
        assert "handoffs/builder-a.md" in rep["handoff_shards"]

        # Negative controls on sharded handoffs
        (work / "handoffs/builder-bloated.md").write_text("z" * 4200 + "\n", encoding="utf-8")
        r_shard = run(["scripts/verify/ratchet-check", "--budgets", "verify/budgets.json", "--check-hot-set"], work)
        assert r_shard.returncode == 1 and "handoffs/builder-bloated.md" in r_shard.stdout
        (work / "handoffs/builder-bloated.md").unlink()

        (work / "handoffs/builder-long.md").write_text("line\n" * 65, encoding="utf-8")
        r_lines = run(["scripts/verify/ratchet-check", "--budgets", "verify/budgets.json", "--check-hot-set"], work)
        assert r_lines.returncode == 1 and "lines 65 > cap 60" in r_lines.stdout
        (work / "handoffs/builder-long.md").unlink()

        # Ratchet monotonic raise + regression block + exit 4 without ADR + allow with ADR
        assert run(["scripts/verify/ratchet-check", "--tests", "10", "--coverage", "80.0", "--update"], work).returncode == 0
        assert run(["scripts/verify/ratchet-check", "--tests", "9", "--coverage", "80.0"], work).returncode == 1
        assert run(["scripts/verify/ratchet-check", "--tests", "9", "--allow-lower"], work).returncode == 4
        assert run(["scripts/verify/ratchet-check", "--tests", "9", "--allow-lower", "--decision", "D-007", "--update"], work).returncode == 0

        (work / "verify/ratchet.json").write_text('{"test_count": -1, "coverage_pct": 150}\n', encoding="utf-8")
        r_cfg = run(["scripts/verify/ratchet-check", "--verify-config"], work)
        assert r_cfg.returncode == 1 and "RATCHET CONFIG ERRORS" in r_cfg.stdout

        b = json.loads((work / "verify/budgets.json").read_text(encoding="utf-8"))
        b["perf"] = {"max_p95_ms": 50.0, "min_hit_rate": 0.90, "max_regression_pct": 5.0}
        (work / "verify/budgets.json").write_text(json.dumps(b), encoding="utf-8")
        (work / "verify/baseline.json").write_text('{"p95_ms": 20.0, "hit_rate": 0.95}\n', encoding="utf-8")
        assert run(["scripts/verify/ratchet-check", "--budgets", "verify/budgets.json", "--measure", "p95_ms=20.5", "--measure", "hit_rate=0.95", "--baseline", "verify/baseline.json"], work).returncode == 0
        assert run(["scripts/verify/ratchet-check", "--budgets", "verify/budgets.json", "--measure", "p95_ms=20.5", "--measure", "hit_rate=0.70"], work).returncode == 1
        assert run(["scripts/verify/ratchet-check", "--budgets", "verify/budgets.json", "--measure", "p95_ms=25.0", "--measure", "hit_rate=0.95", "--baseline", "verify/baseline.json"], work).returncode == 1


# ---------------------------------------------------------------------------
# Suite 3: Base-Ref Auto-Resolution across Topologies (_smort_lib.py)
# ---------------------------------------------------------------------------
def suite_3_base_ref_resolution():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        bare, work = root / "origin.git", root / "work"
        work.mkdir()
        init_git_repo(work, bare, default_branch="main")
        assert extract_smort(work) == 32
        commit_all(work, "chore: init")
        run(["git", "push", "-u", "origin", "main"], work, check=True)
        run(["git", "checkout", "-b", "smort/dev"], work, check=True)
        (work / "README.md").write_text("# App\n", encoding="utf-8")
        commit_all(work, "chore: dev branch")
        run(["git", "push", "-u", "origin", "smort/dev"], work, check=True)

        r_dev = run(["python3", "scripts/verify/_smort_lib.py", "--resolve-base"], work)
        assert r_dev.returncode == 0 and r_dev.stdout.strip() == "origin/main"

        run(["git", "checkout", "-b", "smort/T-001"], work, check=True)
        r_t1 = run(["python3", "scripts/verify/_smort_lib.py", "--resolve-base"], work)
        assert r_t1.returncode == 0 and r_t1.stdout.strip() == "origin/smort/dev"

        pm = (work / "PROGRAM.md").read_text(encoding="utf-8")
        pm = re.sub(r"\| `A0` continuous flow \|.*", "| `A0` continuous flow | `auto-merge-main` |", pm)
        (work / "PROGRAM.md").write_text(pm, encoding="utf-8")
        r_am = run(["python3", "scripts/verify/_smort_lib.py", "--resolve-base"], work)
        assert r_am.returncode == 0 and r_am.stdout.strip() == "origin/main"

        r_bad = run(["python3", "scripts/verify/_smort_lib.py", "--resolve-base", "origin/does-not-exist"], work)
        assert r_bad.returncode == 2

    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        init_git_repo(work, bare=None, default_branch="master")
        assert extract_smort(work) == 32
        commit_all(work, "chore: init master")
        run(["git", "checkout", "-b", "smort/T-001"], work, check=True)
        r_m = run(["python3", "scripts/verify/_smort_lib.py", "--resolve-base"], work)
        assert r_m.returncode == 0 and r_m.stdout.strip() == "master"


# ---------------------------------------------------------------------------
# Suite 4: Unbounded Cohesive Tickets, Parallel Gate, Smart gitleaks & --verify-red-cmd
# ---------------------------------------------------------------------------
def suite_4_unbounded_ticket_and_gate():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        bare, work = root / "origin.git", root / "work"
        work.mkdir()
        init_git_repo(work, bare)
        assert extract_smort(work) == 32
        (work / "scripts/verify/project-checks.sh").write_text("#!/usr/bin/env bash\nPYTHONPATH=. python3 tests/test_engine.py\n", encoding="utf-8")
        (work / "scripts/verify/project-checks.sh").chmod(0o755)
        (work / "src/core/domain").mkdir(parents=True)
        (work / "src/core/domain/__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
        (work / "tests").mkdir(exist_ok=True)
        (work / "tests/test_engine.py").write_text("print('base ok')\n", encoding="utf-8")
        pm = (work / "PROJECT-MAP.md").read_text(encoding="utf-8")
        pm = pm.replace("{{src,lib,app}}", "src").replace("{{src/core/domain}}", "src/core/domain")
        (work / "PROJECT-MAP.md").write_text(pm, encoding="utf-8")
        run(["scripts/verify/project-map"], work, check=True)
        (work / "tasks/T-001-big-feature.md").write_text(
            make_task("T-001", "Build cohesive 650-line engine", approval="A0", touch_set=["src/core/domain/**", "tests/**"]),
            encoding="utf-8",
        )
        run(["scripts/verify/tasks-index"], work, check=True)
        commit_all(work, "chore: base install")
        run(["git", "push", "-u", "origin", "main"], work, check=True)
        run(["git", "checkout", "-b", "smort/dev"], work, check=True)
        run(["git", "push", "-u", "origin", "smort/dev"], work, check=True)

        run(["git", "checkout", "-b", "smort/T-001"], work, check=True)
        merge_base_sha = run(["git", "rev-parse", "HEAD"], work, check=True).stdout.strip()

        # Commit genuine failing Red test first (fails because engine.py doesn't exist yet!)
        (work / "tests/test_engine.py").write_text(
            "from src.core.domain.engine import step_10\nassert step_10(5) == 15\n",
            encoding="utf-8",
        )
        red_sha = commit_all(work, "test(T-001): add failing acceptance check")

        # Commit 650-line cohesive feature (unbounded, well above old 400-line cap)
        lines = [f"def step_{i}(x: int) -> int:\n    return x + {i}\n" for i in range(325)]
        (work / "src/core/domain/engine.py").write_text("\n".join(lines), encoding="utf-8")
        head_sha = commit_all(work, "feat(T-001): implement cohesive engine")

        # Smart gitleaks policy: missing gitleaks does NOT force exit 2 in --fast (covered by fake-work-scan history+entropy)
        env_no_gl = {"SECRET_SCANNER_CMD": "nonexistent_gitleaks_binary_smort"}
        r = run(
            [
                "scripts/verify/gate", "--fast", "--task", "T-001",
                "--red-sha", red_sha,
                "--verify-red-cmd", "PYTHONPATH=. python3 tests/test_engine.py",
                "--emit-pow",
            ],
            work, env=env_no_gl,
        )
        assert r.returncode == 0, f"v7 parallel gate + --verify-red-cmd failed:\n{r.stdout}\n{r.stderr}"
        assert not (work / "scripts/verify/__pycache__").exists(), "scripts/verify/__pycache__ should never be created!"
        assert "unlimited" in r.stdout
        assert "[PASS] verify-red-cmd" in r.stdout
        assert "mechanically-proved-failing" in r.stdout
        assert "### Proof of work: T-001" in r.stdout
        last_line = r.stdout.strip().splitlines()[-1]
        assert last_line.startswith("smort-done ok=1 exit=0"), f"Bad final line: {last_line!r}"

        # Negative control: --verify-red-cmd fails loudly if command exits 0 at red-sha!
        r_fake_red = run(
            ["scripts/verify/gate", "--fast", "--task", "T-001", "--red-sha", red_sha, "--verify-red-cmd", "true"],
            work, env=env_no_gl,
        )
        assert r_fake_red.returncode == 1 and "did NOT fail before fix" in r_fake_red.stdout

        # --require-gitleaks and --full enforce exit 2 when gitleaks is missing
        r_req_gl = run(["scripts/verify/gate", "--fast", "--task", "T-001", "--require-gitleaks"], work, env=env_no_gl)
        assert r_req_gl.returncode == 2 and "reason=unverifiable" in r_req_gl.stdout
        r_full_gl = run(["scripts/verify/gate", "--full", "--task", "T-001"], work, env=env_no_gl)
        assert r_full_gl.returncode == 2 and "reason=unverifiable" in r_full_gl.stdout

        # --sequential and --fail-fast modes
        r_seq = run(["scripts/verify/gate", "--fast", "--sequential", "--task", "T-001"], work, env=env_no_gl)
        assert r_seq.returncode == 0
        r_ff = run(["scripts/verify/gate", "--fast", "--fail-fast", "--max-lines", "200"], work, env=env_no_gl)
        assert r_ff.returncode == 1 and "project-checks" not in r_ff.stdout

        # Opt-in --max-lines dry-run exits 4
        r_dry = run(["scripts/verify/gate", "--dry-run", "--max-lines", "200"], work, env=env_no_gl)
        assert r_dry.returncode == 4

        # Negative controls: untracked file, --red-sha HEAD, --red-sha merge-base, invalid base, SMORT_ALLOWED_IDENT
        (work / "stray_untracked.py").write_text("x = 1\n", encoding="utf-8")
        assert run(["scripts/verify/gate", "--fast", "--task", "T-001"], work, env=env_no_gl).returncode == 1
        (work / "stray_untracked.py").unlink()
        assert run(["scripts/verify/gate", "--fast", "--task", "T-001", "--red-sha", head_sha], work, env=env_no_gl).returncode == 1
        assert run(["scripts/verify/gate", "--fast", "--task", "T-001", "--red-sha", merge_base_sha], work, env=env_no_gl).returncode == 1
        assert run(["scripts/verify/gate", "--fast", "--base", "origin/no-such-branch"], work, env=env_no_gl).returncode == 2
        assert run(["scripts/verify/gate", "--fast", "--task", "T-001"], work, env={**env_no_gl, "SMORT_ALLOWED_IDENT": "Other <o@e.com>"}).returncode == 1
        assert run(["scripts/verify/gate", "--fast", "--task", "T-001"], work, env={**env_no_gl, "SMORT_ALLOWED_IDENT": "Smort Tester <tester@example.com>"}).returncode == 0


# ---------------------------------------------------------------------------
# Suite 5: touch-set-check & Hardened fake-work-scan (History + Shannon Entropy)
# ---------------------------------------------------------------------------
def suite_5_touch_set_and_fake_work():
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        init_git_repo(work)
        assert extract_smort(work) == 32
        (work / "tasks/T-001-a0.md").write_text(make_task("T-001", approval="A0", touch_set=["src/**"]), encoding="utf-8")
        (work / "tasks/T-002-ci.md").write_text(make_task("T-002", approval="A1", touch_set=[".github/workflows/**"]), encoding="utf-8")
        (work / "tests").mkdir(exist_ok=True)
        (work / "tests/sample_test.go").write_text("package t\nfunc TestKeep() {}\nfunc TestDrop() {}\n", encoding="utf-8")
        (work / "tests/SampleTest.java").write_text("class S {\n  @Test void a(){}\n  @Test void b(){}\n}\n", encoding="utf-8")
        commit_all(work, "chore: base")

        # 5a: A0 touching sensitive path blocked
        run(["git", "checkout", "-b", "smort/T-001"], work, check=True)
        (work / "src/auth").mkdir(parents=True)
        (work / "src/auth/login.py").write_text("def login(): return True\n", encoding="utf-8")
        commit_all(work, "feat: auth")
        r_sens = run(["scripts/verify/touch-set-check", "T-001"], work)
        assert r_sens.returncode == 1 and "A0 SENSITIVE-PATH ESCALATION" in r_sens.stdout

        # 5b: Builder tampering scripts/verify/gate ALWAYS blocked
        run(["git", "checkout", "-b", "smort/tamper", "main"], work, check=True)
        (work / "tasks/T-099-evil.md").write_text(make_task("T-099", approval="A1", touch_set=["scripts/verify/**"]), encoding="utf-8")
        (work / "scripts/verify/gate").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        commit_all(work, "chore: try tamper")
        assert run(["scripts/verify/fake-work-scan", "--lane", "builder", "--task", "T-099"], work).returncode == 1
        assert run(["scripts/verify/fake-work-scan", "--lane", "integration"], work).returncode == 0

        # 5c: Authorized A1 builder editing .github/workflows/ci.yml allowed; unauthorized blocked
        run(["git", "checkout", "-b", "smort/T-002", "main"], work, check=True)
        (work / ".github/workflows").mkdir(parents=True)
        (work / ".github/workflows/ci.yml").write_text("name: CI\non: [push]\njobs:\n  t:\n    runs-on: ubuntu-latest\n    timeout-minutes: 10\n    steps:\n      - run: echo ok\n", encoding="utf-8")
        commit_all(work, "ci: add workflow")
        assert run(["scripts/verify/fake-work-scan", "--lane", "builder"], work).returncode == 1
        assert run(["scripts/verify/fake-work-scan", "--lane", "builder", "--task", "T-002"], work).returncode == 0

        # 5d: Python except: pass + Go/Java test deletion
        run(["git", "checkout", "-b", "smort/slop", "main"], work, check=True)
        (work / "src").mkdir(exist_ok=True)
        (work / "src/swallow.py").write_text("try:\n    risky()\nexcept Exception:\n    pass\n", encoding="utf-8")
        (work / "tests/sample_test.go").write_text("package t\nfunc TestKeep() {}\n", encoding="utf-8")
        (work / "tests/SampleTest.java").write_text("class S {\n  @Test void a(){}\n}\n", encoding="utf-8")
        commit_all(work, "fix: sloppy")
        r_slop = run(["scripts/verify/fake-work-scan"], work)
        assert r_slop.returncode == 1
        assert "silent Python except/pass block" in r_slop.stdout
        assert "sample_test.go: net test count decreased" in r_slop.stdout
        assert "SampleTest.java: net test count decreased" in r_slop.stdout

        # 5e: Intermediate-commit secret leak (added in commit 1, deleted in commit 2) CAUGHT by history scan!
        run(["git", "checkout", "-b", "smort/hist-leak", "main"], work, check=True)
        (work / "src").mkdir(exist_ok=True)
        fake_gh = "ghp_" + "A1b2C3d4E5f6" * 3
        (work / "src/cfg.py").write_text(f'TOKEN = "{fake_gh}"\n', encoding="utf-8")
        commit_all(work, "wip: oops committed secret")
        (work / "src/cfg.py").write_text('import os\nTOKEN = os.environ.get("TOKEN", "")\n', encoding="utf-8")
        commit_all(work, "fix: delete secret from tip")
        r_hist = run(["scripts/verify/fake-work-scan"], work)
        assert r_hist.returncode == 1 and "history:" in r_hist.stdout and "secret literal in branch commit history" in r_hist.stdout

        # 5f: Shannon-entropy high-entropy secret caught; SHA-256 hex digest & example placeholder pass clean!
        run(["git", "checkout", "-b", "smort/entropy", "main"], work, check=True)
        (work / "src").mkdir(exist_ok=True)
        (work / "src/safe_vals.py").write_text(
            'FILE_DIGEST = "706f4a87a788d255243d7fd00997103c28fd8f690d088ef395087cc2950ada31"\n'
            'API_SECRET = "example_placeholder_value_not_real"\n',
            encoding="utf-8",
        )
        commit_all(work, "chore: safe constants")
        assert run(["scripts/verify/fake-work-scan"], work).returncode == 0
        (work / "src/real_secret.py").write_text('API_SECRET = "k9Qm4xPz8vR2nL7wJ5tB1cF6hY3dN0sA"\n', encoding="utf-8")
        run(["git", "add", "src/real_secret.py"], work, check=True)
        r_ent = run(["scripts/verify/fake-work-scan", "--staged"], work)
        assert r_ent.returncode == 1 and "high-entropy secret assignment" in r_ent.stdout

        # --redact strips secrets cleanly
        r_red = run(["scripts/verify/fake-work-scan", "--redact"], work, input_text=f"Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abcdefghijk123456 {fake_gh}\n")
        assert r_red.returncode == 0 and fake_gh not in r_red.stdout and "[redacted]" in r_red.stdout


# ---------------------------------------------------------------------------
# Suite 6: tasks-index Full §5 Delegation & Batched Live Overlay
# ---------------------------------------------------------------------------
def suite_6_tasks_index_delegation():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        bare, work = root / "origin.git", root / "work"
        work.mkdir()
        init_git_repo(work, bare)
        assert extract_smort(work) == 32

        for d in ("src/c1", "src/c2", "src/c3"):
            (work / d).mkdir(parents=True)
        (work / "src/c1/a.py").write_text("x = 1\n", encoding="utf-8")
        (work / "src/c2/b.py").write_text("y = 2\n", encoding="utf-8")
        pm = (work / "PROJECT-MAP.md").read_text(encoding="utf-8")
        pm = pm.replace("{{src,lib,app}}", "src")
        pm = pm.replace("| S1.C1 | {{Domain types & rules}} | Component | L0 | data | planned | `{{src/core/domain}}`", "| S1.C1 | Core | Component | L0 | data | verified | `src/c1`")
        pm = pm.replace("| S1.C2 | {{Storage adapter}} | Component | L1 | data | planned | `{{src/core/storage}}`", "| S1.C2 | Store | Component | L1 | data | built | `src/c2`")
        pm = pm.replace("| S2.C1 | {{API / UI boundary}} | Component | L3 | backend | planned | `{{src/api}}`", "| S2.C1 | API | Component | L3 | backend | planned | `src/c3`")
        (work / "PROJECT-MAP.md").write_text(pm, encoding="utf-8")
        run(["scripts/verify/project-map"], work, check=True)

        (work / "tasks/T-010-l.md").write_text(make_task("T-010", "Large S1.C1", approval="A0", priority="P1", estimate="L", constituents=["S1.C1"], touch_set=["src/c1/l.py"]), encoding="utf-8")
        (work / "tasks/T-011-s.md").write_text(make_task("T-011", "Small S1.C1", approval="A0", priority="P1", estimate="S", constituents=["S1.C1"], touch_set=["src/c1/s.py"]), encoding="utf-8")
        (work / "tasks/T-012-unblocker.md").write_text(make_task("T-012", "Unblocks 2 tasks", approval="A0", priority="P1", estimate="M", constituents=["S1.C1"], touch_set=["src/c1/u.py"]), encoding="utf-8")
        (work / "tasks/T-013-dep1.md").write_text(make_task("T-013", "Waits on T-012", approval="A0", priority="P1", estimate="S", constituents=["S1.C2"], depends_on=["T-012"], touch_set=["src/c2/d1.py"]), encoding="utf-8")
        (work / "tasks/T-014-dep2.md").write_text(make_task("T-014", "Also waits T-012", approval="A0", priority="P1", estimate="S", constituents=["S1.C2"], depends_on=["T-012"], touch_set=["src/c2/d2.py"]), encoding="utf-8")
        (work / "tasks/T-015-later-order.md").write_text(make_task("T-015", "Order 2 S1.C2", approval="A0", priority="P1", estimate="S", constituents=["S1.C2"], touch_set=["src/c2/o2.py"]), encoding="utf-8")
        (work / "tasks/T-016-dnt.md").write_text(make_task("T-016", "Touches forbidden", approval="A0", priority="P0", estimate="S", constituents=["S1.C1"], touch_set=["src/c1/secret.py"]), encoding="utf-8")
        run(["scripts/verify/tasks-index"], work, check=True)
        commit_all(work, "chore: seed tasks")
        run(["git", "push", "-u", "origin", "main"], work, check=True)

        # Remote branch claim overlaid via batched git cat-file --batch
        run(["git", "checkout", "-b", "smort/T-010"], work, check=True)
        (work / "tasks/T-010-l.md").write_text(make_task("T-010", "Large S1.C1", approval="A0", priority="P1", estimate="L", status="claimed", constituents=["S1.C1"], touch_set=["src/c1/l.py"]), encoding="utf-8")
        commit_all(work, "chore: claim T-010")
        run(["git", "push", "-u", "origin", "smort/T-010"], work, check=True)
        run(["git", "checkout", "main"], work, check=True)

        r = run(["scripts/verify/tasks-index", "--live", "--next", "--do-not-touch", "src/c1/secret.py", "--json"], work)
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        ids = [x["id"] for x in data["next"]]
        assert ids == ["T-012", "T-011", "T-015"], f"Unexpected §5 ranking: {ids}"
        assert "T-010" in data["active"]
        assert data["not_shown"]["blocked_do_not_touch"] == 1
        assert data["not_shown"]["blocked_deps"] == 2

        prog = (work / "PROGRAM.md").read_text(encoding="utf-8")
        (work / "PROGRAM.md").write_text(re.sub(r"\| Lifecycle mode \|.*", "| Lifecycle mode | `maintenance` |", prog), encoding="utf-8")
        assert "@no why=lifecycle=maintenance" in run(["scripts/verify/tasks-index", "--live", "--next", "--compact"], work).stdout
        (work / "PROGRAM.md").write_text(re.sub(r"\| Release freeze \|.*", "| Release freeze | on since 2026-11-25 |", prog), encoding="utf-8")
        assert "@no why=release_freeze=on" in run(["scripts/verify/tasks-index", "--live", "--next", "--lane", "backend", "--compact"], work).stdout
        (work / "PROGRAM.md").write_text(prog, encoding="utf-8")

        (work / "tasks/T-016-dnt.md").unlink()
        r_sh = run(["scripts/verify/tasks-index"], work)
        assert r_sh.returncode == 4 and "SHRINK-GUARD" in r_sh.stderr


# ---------------------------------------------------------------------------
# Suite 7: project-map & Live --section Reading docs/PLAYBOOK.md & docs/OPERATIONS.md
# ---------------------------------------------------------------------------
def suite_7_project_map_and_cold_docs():
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        init_git_repo(work)
        assert extract_smort(work) == 32
        commit_all(work, "chore: init")

        assert run(["scripts/verify/project-map", "--check"], work).returncode == 0

        r_pb = run(["scripts/verify/project-map", "--section", "3. Work verifiability"], work)
        assert r_pb.returncode == 0 and "docs/PLAYBOOK.md" in r_pb.stdout and "Acceptance checks come first" in r_pb.stdout

        r_ops = run(["scripts/verify/project-map", "--section", "4.3 Continuous"], work)
        assert r_ops.returncode == 0 and "docs/OPERATIONS.md" in r_ops.stdout and "stage-smort-dev" in r_ops.stdout

        r_imp = run(["scripts/verify/project-map", "--impact", "S1.C1", "--compact"], work)
        assert r_imp.returncode == 0 and "@ok target=S1.C1 constituents=S1.C1,S1.C2,S2.C1" in r_imp.stdout

        pm = (work / "PROJECT-MAP.md").read_text(encoding="utf-8")
        (work / "PROJECT-MAP.md").write_text(pm.replace("| EXTRACTED |", "| INFERRED (0.5) |", 1), encoding="utf-8")
        assert run(["scripts/verify/project-map", "--check"], work).returncode == 1
        (work / "PROJECT-MAP.md").write_text(pm, encoding="utf-8")
        assert run(["scripts/verify/project-map", "--section", "anything", "--file", "../etc/passwd"], work).returncode == 1


# ---------------------------------------------------------------------------
# Suite 8: code-index Polyglot, Stat No-Op Cache, Compact JSON, tsconfig Aliases & Scoped affected
# ---------------------------------------------------------------------------
def suite_8_code_index_v7():
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        init_git_repo(work)
        assert extract_smort(work) == 32
        for d in ("src/auth", "src/api", "src/web", "src/jvm/com/app", "src/native", "src/dotnet", "infra/modules/vpc", "infra/env", "db", "scripts", "packages/web"):
            (work / d).mkdir(parents=True, exist_ok=True)
        (work / "tsconfig.json").write_text(
            '// JSONC comment\n{\n  "compilerOptions": {\n    "baseUrl": ".",\n    "paths": { "@web/*": ["src/web/*"], },\n  },\n}\n',
            encoding="utf-8",
        )
        (work / "src/web/util.ts").write_text("export function parse(x: string) { return x; }\nexport function uniqueRender() { return 1; }\n", encoding="utf-8")
        (work / "src/web/index.ts").write_text("export * from './util';\n", encoding="utf-8")
        (work / "src/api/app.ts").write_text("import { parse, uniqueRender } from '@web/util';\nexport function boot() { return parse('a') + uniqueRender(); }\n", encoding="utf-8")
        # Unrelated file calling generic 'parse()' without importing src/web/util.ts
        (work / "src/api/unrelated.ts").write_text("export function other() { return parse('noise'); }\n", encoding="utf-8")

        (work / "src/auth/hub.py").write_text("def verify_jwt(tok: str) -> bool:\n    return bool(tok)\n", encoding="utf-8")
        (work / "src/api/good.py").write_text("from src.auth.hub import verify_jwt\ndef handle(t):\n    return verify_jwt(t)\n", encoding="utf-8")
        (work / "src/api/comments_only.py").write_text("# Never call jwt.decode(tok) directly here\ndef ping():\n    return 'ok'\n", encoding="utf-8")
        (work / "src/api/comments_ts.ts").write_text("/* jwt.decode(x) in block comment */\n// jwt.decode(y)\nexport function health() { return 1; }\n", encoding="utf-8")
        (work / "src/jvm/com/app/TokenService.java").write_text("package com.app;\npublic class TokenService {\n  public boolean validate() { return true; }\n}\n", encoding="utf-8")
        (work / "src/jvm/com/app/ApiController.java").write_text("package com.app;\nimport com.app.TokenService;\npublic class ApiController {\n  public void run() { validate(); }\n}\n", encoding="utf-8")
        (work / "src/native/math.h").write_text("struct Vec2 { int x; };\n", encoding="utf-8")
        (work / "src/native/calc.cpp").write_text('#include "math.h"\nint add(int a, int b) { return a + b; }\n', encoding="utf-8")
        (work / "src/dotnet/Billing.cs").write_text("public class BillingService {\n  public int Charge() { return 1; }\n}\n", encoding="utf-8")
        (work / "infra/modules/vpc/main.tf").write_text('resource "aws_vpc" "main" {}\n', encoding="utf-8")
        (work / "infra/env/main.tf").write_text('module "net" {\n  source = "../modules/vpc"\n}\n', encoding="utf-8")
        (work / "db/schema.sql").write_text("CREATE TABLE bookings (id INT);\nSELECT * FROM bookings;\n", encoding="utf-8")
        (work / "scripts/helper.py").write_text("def cli_helper():\n    return 42\n", encoding="utf-8")
        (work / "packages/web/package.json").write_text('{"dependencies": {"react": "19.0.0"}}\n', encoding="utf-8")
        commit_all(work, "feat: polyglot + tsconfig fixture")

        r_b1 = run(["scripts/verify/code-index", "build", "--worktree", "isolated"], work)
        assert r_b1.returncode == 0, f"code-index build failed:\n{r_b1.stdout}\n{r_b1.stderr}"
        caches = list((work / "verify").glob("code-index-*.json"))
        assert len(caches) == 1
        raw_cache = caches[0].read_text(encoding="utf-8")
        assert len(raw_cache.splitlines()) == 1, "Cache JSON should be compact single-line"
        mtime1 = caches[0].stat().st_mtime_ns
        time.sleep(0.05)

        # Second build with 0 changes hits (mtime_ns, size) fast-path and skips rewriting cache!
        r_b2 = run(["scripts/verify/code-index", "build", "--worktree", "isolated"], work)
        assert r_b2.returncode == 0
        assert caches[0].stat().st_mtime_ns == mtime1, "No-op code-index build rewrote cache unnecessarily!"

        idx = json.loads(raw_cache)
        assert idx["schema_version"] == 3
        edge_pairs = {(e["source"], e["target"]) for e in idx["edges"]}
        # tsconfig @web/* alias AND barrel re-export resolved!
        assert ("src/api/app.ts", "src/web/util.ts") in edge_pairs, f"tsconfig @web/* alias unresolved: {edge_pairs}"
        assert ("src/web/index.ts", "src/web/util.ts") in edge_pairs
        assert ("src/api/good.py", "src/auth/hub.py") in edge_pairs
        assert ("src/jvm/com/app/ApiController.java", "src/jvm/com/app/TokenService.java") in edge_pairs
        assert ("src/native/calc.cpp", "src/native/math.h") in edge_pairs
        assert ("infra/env/main.tf", "infra/modules/vpc/main.tf") in edge_pairs
        assert "scripts/helper.py" in idx["files"] and not any(f.startswith("scripts/verify/") for f in idx["files"])
        assert "packages/web/package.json" in idx["manifests"]

        # Scoped affected: generic 'parse' skips unrelated.ts name-only match and reports name_only_generic_skipped=1!
        r_aff = run(["scripts/verify/code-index", "affected", "src/web/util.ts::parse", "--worktree", "isolated", "--json"], work)
        assert r_aff.returncode == 0, r_aff.stderr
        aff = json.loads(r_aff.stdout)
        assert "src/api/app.ts" in aff["direct_files"]
        assert "src/api/unrelated.ts" not in aff["direct_files"] and "src/api/unrelated.ts" not in aff["name_only_files"]
        assert aff["not_shown"]["name_only_generic_skipped"] >= 1, f"Expected generic stopword skip: {aff}"

        # Comment-safe bypass check
        assert run(["scripts/verify/code-index", "bypass", "src/auth/hub.py", "--pattern", r"jwt\.decode\("], work).returncode == 0
        (work / "src/api/rogue.py").write_text("import jwt\ndef evil(t):\n    return jwt.decode(t)\n", encoding="utf-8")
        commit_all(work, "feat: rogue bypass")
        r_bp = run(["scripts/verify/code-index", "bypass", "src/auth/hub.py", "--pattern", r"jwt\.decode\("], work)
        assert r_bp.returncode == 1 and "src/api/rogue.py:L3" in r_bp.stdout


# ---------------------------------------------------------------------------
# Suite 9: ci-guard 2/4-Space, Block Scalars & Expression Timeouts
# ---------------------------------------------------------------------------
def suite_9_ci_guard():
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        assert extract_smort(work) == 32
        r_st = run(["scripts/verify/ci-guard", "--self-test"], work)
        assert r_st.returncode == 0 and "self-test: PASS" in r_st.stdout
        wf = work / ".github/workflows"
        wf.mkdir(parents=True)
        (wf / "ci.yml").write_text(
            "name: FourSpace\non: [push]\njobs:\n    test:\n        runs-on: ubuntu-latest\n        timeout-minutes: ${{ inputs.t }}\n        steps:\n            - run: |\n                  cat <<'EOF'\n                  not_a_job: &bad\n                  EOF\n",
            encoding="utf-8",
        )
        assert run(["scripts/verify/ci-guard"], work).returncode == 1
        assert run(["scripts/verify/ci-guard", "--allow-expr-timeout"], work).returncode == 0


# ---------------------------------------------------------------------------
# Suite 10: claim-check & Starter verify/claims.json
# ---------------------------------------------------------------------------
def suite_10_claim_check():
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        init_git_repo(work)
        assert extract_smort(work) == 32
        commit_all(work, "chore: init")
        assert "self-test: PASS" in run(["scripts/verify/claim-check", "--self-test"], work, check=True).stdout
        r_ok = run(["scripts/verify/claim-check"], work)
        assert r_ok.returncode == 0, f"Starter templates failed claim-check:\n{r_ok.stdout}\n{r_ok.stderr}"
        (work / "BAD.md").write_text("CI is green even though CI was unavailable locally.\n\nEvidence verified at /tmp/local_run.log.\n", encoding="utf-8")
        r_bad = run(["scripts/verify/claim-check", "BAD.md"], work)
        assert r_bad.returncode == 1 and "SMORT-NO-FALSE-CI-GREEN" in r_bad.stdout and "SMORT-NO-LOCAL-EVIDENCE" in r_bad.stdout


# ---------------------------------------------------------------------------
# Suite 11: conflict-matrix Parallel Merge-Tree & Disjoint-Path Pre-Filter
# ---------------------------------------------------------------------------
def suite_11_conflict_matrix():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        bare, work = root / "origin.git", root / "work"
        work.mkdir()
        init_git_repo(work, bare)
        assert extract_smort(work) == 32
        (work / "src/core/domain").mkdir(parents=True)
        (work / "src/unrelated").mkdir(parents=True)
        (work / "src/core/domain/my file.py").write_text("A = 1\n", encoding="utf-8")
        (work / "src/unrelated/solo.py").write_text("Z = 1\n", encoding="utf-8")
        pm = (work / "PROJECT-MAP.md").read_text(encoding="utf-8")
        pm = pm.replace("{{src,lib,app}}", "src").replace("{{src/core/domain}}", "src/core/domain")
        (work / "PROJECT-MAP.md").write_text(pm, encoding="utf-8")
        commit_all(work, "chore: base")
        run(["git", "push", "-u", "origin", "main"], work, check=True)

        run(["git", "checkout", "-b", "smort/T-001", "main"], work, check=True)
        (work / "src/core/domain/my file.py").write_text("A = 2\n", encoding="utf-8")
        commit_all(work, "feat(T-001): 2")
        run(["git", "push", "-u", "origin", "smort/T-001"], work, check=True)

        run(["git", "checkout", "-b", "smort/T-002", "main"], work, check=True)
        (work / "src/core/domain/my file.py").write_text("A = 3\n", encoding="utf-8")
        commit_all(work, "feat(T-002): 3")
        run(["git", "push", "-u", "origin", "smort/T-002"], work, check=True)

        run(["git", "checkout", "-b", "smort/T-003", "main"], work, check=True)
        (work / "src/unrelated/solo.py").write_text("Z = 99\n", encoding="utf-8")
        commit_all(work, "feat(T-003): disjoint")
        run(["git", "push", "-u", "origin", "smort/T-003"], work, check=True)

        # Disjoint pre-filter skips (T-001, T-003) and (T-002, T-003) while catching (T-001, T-002) conflict!
        r = run(["scripts/verify/conflict-matrix", "--worktree", "isolated"], work)
        assert r.returncode == 1 and "disjoint_pairs_skipped=2" in r.stdout, f"Unexpected conflict-matrix stdout:\n{r.stdout}"
        reports = sorted((work / "verify/conflicts").glob("*.md"))
        assert len(reports) == 1 and re.match(r"^\d{4}-\d{2}-\d{2}-\d{6}\.md$", reports[0].name)
        content = reports[0].read_text(encoding="utf-8")
        assert "src/core/domain/my file.py" in content and "SEMANTIC-RISK" in content and "disjoint_pairs_skipped=2" in content

        # --all-pairs disables pre-filter
        r_all = run(["scripts/verify/conflict-matrix", "--all-pairs", "--report-only", "--out", "verify/conflicts/all.md"], work)
        assert r_all.returncode == 0 and "disjoint_pairs_skipped=0" in r_all.stdout


# ---------------------------------------------------------------------------
# Suite 12: gate-brief (M0, Risk-Sliced A1 Maps, JSON) & lessons-reflect (O(log K) Compact + Git --as-of)
# ---------------------------------------------------------------------------
def suite_12_gate_brief_and_lessons():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        bare, work = root / "origin.git", root / "work"
        work.mkdir()
        init_git_repo(work, bare)
        assert extract_smort(work) == 32
        (work / "src").mkdir(exist_ok=True)
        (work / "src/mod.py").write_text("V = 1\n", encoding="utf-8")
        commit_all(work, "chore: base v1", env={"GIT_AUTHOR_DATE": "2026-10-01T10:00:00Z", "GIT_COMMITTER_DATE": "2026-10-01T10:00:00Z"})
        run(["git", "push", "-u", "origin", "main"], work, check=True)

        run(["git", "checkout", "-b", "smort/dev"], work, check=True)
        (work / "src/a0_one.py").write_text("X = 1\n", encoding="utf-8")
        commit_all(work, "feat(T-001): A0 one", env={"GIT_AUTHOR_DATE": "2026-10-02T10:00:00Z", "GIT_COMMITTER_DATE": "2026-10-02T10:00:00Z"})
        (work / "src/a0_two.py").write_text("Y = 2\n", encoding="utf-8")
        commit_all(work, "feat(T-002): A0 two", env={"GIT_AUTHOR_DATE": "2026-10-03T10:00:00Z", "GIT_COMMITTER_DATE": "2026-10-03T10:00:00Z"})
        run(["git", "push", "-u", "origin", "smort/dev"], work, check=True)

        for idx in range(1, 7):
            tid = f"T-10{idx}"
            run(["git", "checkout", "-b", f"smort/{tid}", "origin/smort/dev"], work, check=True)
            (work / f"tasks/{tid}-a1.md").write_text(
                make_task(tid, f"A1 feature {idx}", approval="A1", status="awaiting-slot", approval_reason="auth change"),
                encoding="utf-8",
            )
            if idx == 1:
                # 950-line cohesive PR spanning sensitive, contracts, core, and tests!
                for d in ("src/auth", "src/api", "src/core", "tests"):
                    (work / d).mkdir(parents=True, exist_ok=True)
                (work / "src/auth/guard.py").write_text("\n".join(f"A_{j} = {j}" for j in range(120)) + "\n", encoding="utf-8")
                (work / "src/api/routes.py").write_text("\n".join(f"R_{j} = {j}" for j in range(130)) + "\n", encoding="utf-8")
                (work / "src/core/svc.py").write_text("\n".join(f"S_{j} = {j}" for j in range(500)) + "\n", encoding="utf-8")
                (work / "tests/test_guard.py").write_text("\n".join(f"def test_g_{j}(): pass" for j in range(200)) + "\n", encoding="utf-8")
            else:
                (work / f"src/a1_{idx}.py").write_text("\n".join(f"V_{j} = {j}" for j in range(40)) + "\n", encoding="utf-8")
            commit_all(work, f"feat({tid}): A1 {idx}")
            run(["git", "push", "-u", "origin", f"smort/{tid}"], work, check=True)

        run(["git", "checkout", "smort/T-101"], work, check=True)
        manifest_path = work / "verify/logs/slot-manifest.json"
        r_gb = run(["scripts/verify/gate-brief", "--slot", "Evening", "--json-out", str(manifest_path)], work)
        assert r_gb.returncode == 0, f"gate-brief failed:\n{r_gb.stderr}"
        out = r_gb.stdout
        assert "`M0`" in out and "origin/smort/dev -> origin/main" in out
        assert "approve M0 M1 M2 M3 M4 M5" in out
        assert "### Risk-Sliced Review Maps" in out
        assert "sensitive=120, contracts/api=130, core=500, tests/docs=200" in out, f"Bad risk slice:\n{out}"
        assert "a1_overflow_deferred=1" in out

        man = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert man["merges"][0]["code"] == "M0" and man["merges"][1]["code"] == "M1"
        assert man["merges"][1]["risk_slice"]["sensitive"] == 120

        # Opt-in --max-lines 200 still never starves first 950-line PR
        r_gb2 = run(["scripts/verify/gate-brief", "--max-lines", "200"], work)
        assert r_gb2.returncode == 0 and "T-101" in r_gb2.stdout and "a1_overflow_deferred=5" in r_gb2.stdout

        # lessons-reflect Git-backed --as-of + O(log K) compaction across 150 lessons
        run(["git", "checkout", "main"], work, check=True)
        assert run([
            "scripts/verify/lessons-reflect", "log",
            "--topic", "mod-v1-rule", "--outcome", "useful",
            "--note", "Keep V=1 invariant", "--files", "src/mod.py",
            "--task", "T-001", "--ts", "2026-10-02T12:00:00Z", "--human",
        ], work).returncode == 0
        (work / "src/mod.py").write_text("V = 2\n", encoding="utf-8")
        commit_all(work, "feat: bump mod v2", env={"GIT_AUTHOR_DATE": "2026-10-10T10:00:00Z", "GIT_COMMITTER_DATE": "2026-10-10T10:00:00Z"})

        ov_live = json.loads(run(["scripts/verify/lessons-reflect", "build", "--now", "2026-10-15T12:00:00Z", "--json"], work, check=True).stdout)
        assert ov_live["stale_evicted"] == 1 and "mod-v1-rule" not in ov_live["human_overrides"]
        ov_ok = json.loads(run(["scripts/verify/lessons-reflect", "build", "--as-of", "2026-10-05", "--json"], work, check=True).stdout)
        assert ov_ok["stale_evicted"] == 0 and "mod-v1-rule" in ov_ok["human_overrides"]
        ov_st = json.loads(run(["scripts/verify/lessons-reflect", "build", "--as-of", "2026-10-15", "--json"], work, check=True).stdout)
        assert ov_st["stale_evicted"] == 1 and "mod-v1-rule" not in ov_st["human_overrides"]

        # 150 lessons compacted in O(log K) renders to <= 8192 B
        lines_jsonl = []
        for i in range(150):
            lines_jsonl.append(json.dumps({
                "id": f"id-{i:04d}",
                "ts": "2026-10-14T12:00:00Z",
                "created_at": "2026-10-14T12:00:00Z",
                "valid_from": "2026-10-14T12:00:00Z",
                "valid_until": None,
                "task": f"T-{i:03d}",
                "topic": f"topic-{i:03d}",
                "outcome": "useful",
                "human": False,
                "note": f"Detailed engineering lesson {i} " + ("context " * 20),
                "correction": "",
                "files": {},
            }))
        (work / "verify/lessons/bulk.jsonl").write_text("\n".join(lines_jsonl) + "\n", encoding="utf-8")
        assert run(["scripts/verify/lessons-reflect", "build", "--now", "2026-10-15T12:00:00Z"], work).returncode == 0
        assert len((work / "verify/LESSONS.md").read_bytes()) <= 8192
        ov_c = json.loads((work / "verify/.lessons_overlay.json").read_text(encoding="utf-8"))
        assert ov_c["not_shown"]["trimmed_for_budget"] > 100
        assert run(["scripts/verify/ratchet-check", "--budgets", "verify/budgets.json", "--check-hot-set"], work).returncode == 0


# ---------------------------------------------------------------------------
# Suite 13: smort-resume (1-Call Role Startup Packet, Topic Filter & Redaction)
# ---------------------------------------------------------------------------
def suite_13_smort_resume():
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        init_git_repo(work)
        assert extract_smort(work) == 32
        (work / "tasks/T-001-ready.md").write_text(make_task("T-001", "Ready backend task", approval="A0", lane="backend"), encoding="utf-8")
        fake_gh = "ghp_" + "Z9y8X7w6V5u4" * 3
        (work / "handoffs/dev-1.md").write_text(f"# Agent handoff\nResuming T-001 (leaked {fake_gh})\n", encoding="utf-8")
        (work / "verify/LESSONS.md").write_text(
            "# Lessons\n- **auth.guard**: Always check authz first\n- **billing.stripe**: Idempotency keys required\n",
            encoding="utf-8",
        )
        run(["scripts/verify/tasks-index"], work, check=True)
        commit_all(work, "chore: init resume fixture")

        # JSON output
        r_j = run(["scripts/verify/smort-resume", "--lane", "backend", "--agent", "dev-1", "--topic", "auth", "--offline", "--json"], work)
        assert r_j.returncode == 0, r_j.stderr
        pkt = json.loads(r_j.stdout)
        assert pkt["state"]["template_version"] == "2026-11-25.v11"
        assert "T-001" in pkt["tasks_next"]
        assert fake_gh not in pkt["agent_handoff"] and "[redacted]" in pkt["agent_handoff"]
        assert "auth.guard" in pkt["lessons"] and "billing.stripe" not in pkt["lessons"]
        assert pkt["not_shown"]["lessons_filtered_by_topic"] == 1

        # Compact output
        r_c = run(["scripts/verify/smort-resume", "--lane", "verifier", "--agent", "dev-1", "--offline", "--compact"], work)
        assert r_c.returncode == 0
        assert "@state " in r_c.stdout and "@not_shown " in r_c.stdout and fake_gh not in r_c.stdout

        # Bounded --max-chars preserves not_shown footer outside truncation budget
        r_m = run(["scripts/verify/smort-resume", "--lane", "solo", "--offline", "--max-chars", "500"], work)
        assert r_m.returncode == 0 and "chars_truncated=" in r_m.stdout and "not_shown:" in r_m.stdout


# ---------------------------------------------------------------------------
# Suite 14: slot-apply (Deterministic Batch-Reply Parser, Unverified Guard & Execution)
# ---------------------------------------------------------------------------
def suite_14_slot_apply():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        bare, work = root / "origin.git", root / "work"
        work.mkdir()
        init_git_repo(work, bare)
        assert extract_smort(work) == 32
        (work / "src").mkdir(exist_ok=True)
        (work / "src/app.py").write_text("V = 0\n", encoding="utf-8")
        commit_all(work, "chore: init main")
        run(["git", "push", "-u", "origin", "main"], work, check=True)

        # Stage M0 on smort/dev
        run(["git", "checkout", "-b", "smort/dev"], work, check=True)
        (work / "src/a0.py").write_text("A0 = 1\n", encoding="utf-8")
        commit_all(work, "feat(T-001): staged A0")
        run(["git", "push", "-u", "origin", "smort/dev"], work, check=True)

        # Verified A1 branch M1
        run(["git", "checkout", "-b", "smort/T-010", "origin/smort/dev"], work, check=True)
        (work / "src/a1.py").write_text("A1 = 1\n", encoding="utf-8")
        commit_all(work, "feat(T-010): verified A1")
        run(["git", "push", "-u", "origin", "smort/T-010"], work, check=True)

        run(["git", "checkout", "main"], work, check=True)
        manifest = {
            "schema_version": 1,
            "slot": "Evening",
            "generated_at_utc": "2026-11-25 18:30 UTC",
            "base": "origin/smort/dev",
            "main": "main",
            "merges": [
                {"code": "M0", "kind": "m0-staging", "source_ref": "origin/smort/dev", "target_ref": "main", "verified": True},
                {"code": "M1", "kind": "a1-pr", "task_id": "T-010", "branch": "origin/smort/T-010", "target_ref": "main", "pr": "none", "status": "awaiting-slot", "verified": True},
                {"code": "M2", "kind": "a1-pr", "task_id": "T-011", "branch": "origin/smort/T-011", "target_ref": "main", "pr": "none", "status": "in-review", "verified": False},
            ],
            "decisions": [
                {"code": "D1", "task_id": "T-020", "title": "Enable auto-merge-main", "approval_reason": "A0_FLOW ratification"},
                {"code": "D2", "task_id": "T-021", "title": "Add Redis cache", "approval_reason": "new dep"},
            ],
            "not_shown": {},
        }
        mpath = work / "verify/logs/manifest.json"
        mpath.parent.mkdir(parents=True, exist_ok=True)
        mpath.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        # Negative control 1: unknown code fails with exit 2
        r_unk = run(["scripts/verify/slot-apply", "--manifest", str(mpath), "--reply", "approve M99"], work)
        assert r_unk.returncode == 2 and "unknown merge code" in r_unk.stderr

        # Negative control 2: approving unverified M2 is BLOCKED with exit 1!
        r_unv = run(["scripts/verify/slot-apply", "--manifest", str(mpath), "--reply", "approve M0 M2"], work)
        assert r_unv.returncode == 1 and "NOT verified" in r_unv.stderr

        # Dry-run succeeds without mutating Git or files
        reply = "approve M0 M1; hold M2 (needs load test); D1 A; D2 defer; freeze"
        r_dry = run(["scripts/verify/slot-apply", "--manifest", str(mpath), "--reply", reply, "--dry-run", "--json"], work)
        assert r_dry.returncode == 0, r_dry.stderr
        dres = json.loads(r_dry.stdout)
        assert dres["mode"] == "dry-run" and len(dres["merges"]) == 2 and not (work / "src/a0.py").exists()

        # Execute merges M0 + M1 into main, writes ADR D1, toggles freeze in PROGRAM.md, saves receipt!
        r_ex = run(["scripts/verify/slot-apply", "--manifest", str(mpath), "--reply", reply, "--execute", "--merge-mode", "git", "--json"], work)
        assert r_ex.returncode == 0, f"slot-apply --execute failed:\n{r_ex.stdout}\n{r_ex.stderr}"
        eres = json.loads(r_ex.stdout)
        assert (work / "src/a0.py").is_file() and (work / "src/a1.py").is_file()
        adrs = list((work / "docs/decisions").glob("D1-T-020-*.md"))
        assert len(adrs) == 1 and "`A`" in adrs[0].read_text(encoding="utf-8")
        assert "on since" in (work / "PROGRAM.md").read_text(encoding="utf-8")
        assert eres["receipt"] and (work / eres["receipt"]).is_file()


# ---------------------------------------------------------------------------
# Suite 15: install-hooks (Mechanical Pre-Commit Secret & Pre-Push Main Guards)
# ---------------------------------------------------------------------------
def suite_15_install_hooks():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        bare, work = root / "origin.git", root / "work"
        work.mkdir()
        init_git_repo(work, bare)
        assert extract_smort(work) == 32
        commit_all(work, "chore: init")
        run(["git", "push", "-u", "origin", "main"], work, check=True)

        # Install hooks & verify --check
        assert run(["scripts/verify/install-hooks"], work).returncode == 0
        assert run(["scripts/verify/install-hooks", "--check"], work).returncode == 0

        # Pre-commit hook mechanically blocks committing a staged secret!
        fake_gh = "ghp_" + "Q1w2E3r4T5y6" * 3
        (work / "secret_test.py").write_text(f'KEY = "{fake_gh}"\n', encoding="utf-8")
        run(["git", "add", "secret_test.py"], work, check=True)
        r_cm = run(["git", "commit", "-m", "oops secret"], work)
        assert r_cm.returncode != 0 and "secret literal detected" in (r_cm.stdout + r_cm.stderr)
        run(["git", "reset", "HEAD", "secret_test.py"], work, check=True)
        (work / "secret_test.py").unlink()

        # Pre-push hook mechanically blocks direct push to main!
        (work / "README.md").write_text("# Direct main edit\n", encoding="utf-8")
        commit_all(work, "chore: direct main commit")
        r_push_blk = run(["git", "push", "origin", "main"], work)
        assert r_push_blk.returncode != 0 and "BLOCKED: direct push to protected branch 'main'" in r_push_blk.stderr

        # Feature branch smort/T-001 push succeeds cleanly!
        run(["git", "checkout", "-b", "smort/T-001"], work, check=True)
        r_push_feat = run(["git", "push", "-u", "origin", "smort/T-001"], work)
        assert r_push_feat.returncode == 0, r_push_feat.stderr

        # Explicit SMORT_ALLOW_MAIN_PUSH=1 authorizes slot fast-forward merge push to main!
        run(["git", "checkout", "main"], work, check=True)
        r_push_ok = run(["git", "push", "origin", "main"], work, env={"SMORT_ALLOW_MAIN_PUSH": "1"})
        assert r_push_ok.returncode == 0, r_push_ok.stderr

        # Uninstall & verify --check now reports inactive
        assert run(["scripts/verify/install-hooks", "--uninstall", "--remove-files"], work).returncode == 0
        assert run(["scripts/verify/install-hooks", "--check"], work).returncode == 1


# ---------------------------------------------------------------------------
# Suite 16: End-to-End smort v7 Lifecycle Smoke
# ---------------------------------------------------------------------------
def suite_16_e2e_v7_lifecycle():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        bare, work = root / "origin.git", root / "work"
        work.mkdir()
        init_git_repo(work, bare)
        assert extract_smort(work) == 32
        (work / "scripts/verify/project-checks.sh").write_text("#!/usr/bin/env bash\nPYTHONPATH=. python3 tests/test_calc.py\n", encoding="utf-8")
        (work / "scripts/verify/project-checks.sh").chmod(0o755)
        (work / "src/core/domain").mkdir(parents=True)
        (work / "src/core/domain/__init__.py").write_text("", encoding="utf-8")
        (work / "tests").mkdir(exist_ok=True)
        (work / "tests/test_calc.py").write_text("assert 1 + 1 == 2\n", encoding="utf-8")
        pm = (work / "PROJECT-MAP.md").read_text(encoding="utf-8").replace("{{src,lib,app}}", "src").replace("{{src/core/domain}}", "src/core/domain")
        (work / "PROJECT-MAP.md").write_text(pm, encoding="utf-8")
        run(["scripts/verify/project-map"], work, check=True)
        (work / "tasks/T-001-calc.md").write_text(
            make_task("T-001", "Add domain calculator", approval="A0", touch_set=["src/core/domain/**", "tests/**"]),
            encoding="utf-8",
        )
        run(["scripts/verify/tasks-index"], work, check=True)
        # 1. Install hooks during bootstrap so .githooks/ is version-controlled cleanly
        assert run(["scripts/verify/install-hooks"], work).returncode == 0
        commit_all(work, "chore: install smort v7", env={"SMORT_LANE": "integration"})
        # pre-push hook blocks direct push to main unless SMORT_ALLOW_MAIN_PUSH=1
        assert run(["git", "push", "-u", "origin", "main"], work).returncode != 0
        run(["git", "push", "-u", "origin", "main"], work, check=True, env={"SMORT_ALLOW_MAIN_PUSH": "1"})
        run(["git", "checkout", "-b", "smort/dev"], work, check=True)
        run(["git", "push", "-u", "origin", "smort/dev"], work, check=True)

        # 2. 1-call resume packet
        r_res = run(["scripts/verify/smort-resume", "--lane", "solo", "--offline", "--compact"], work)
        assert r_res.returncode == 0 and "T-001" in r_res.stdout

        # 3. Claim -> Red -> Green -> Gate with --verify-red-cmd (pre-commit hook runs on every commit!)
        run(["git", "checkout", "-b", "smort/T-001", "origin/smort/dev"], work, check=True)
        (work / "tests/test_calc.py").write_text("from src.core.domain.calc import add\nassert add(2, 3) == 5\n", encoding="utf-8")
        red_sha = commit_all(work, "test(T-001): red calc test")
        (work / "src/core/domain/calc.py").write_text("def add(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8")
        commit_all(work, "feat(T-001): green calc")
        r_g = run(
            ["scripts/verify/gate", "--fast", "--task", "T-001", "--red-sha", red_sha, "--verify-red-cmd", "PYTHONPATH=. python3 tests/test_calc.py", "--emit-pow"],
            work, env={"SECRET_SCANNER_CMD": "nonexistent_gl"},
        )
        assert r_g.returncode == 0 and r_g.stdout.strip().splitlines()[-1].startswith("smort-done ok=1 exit=0"), f"gate failed:\n{r_g.stdout}\n{r_g.stderr}"

        # 4. Integrate A0 onto smort/dev, generate brief + manifest, apply M0 via slot-apply --execute!
        run(["git", "checkout", "smort/dev"], work, check=True)
        run(["git", "merge", "--no-ff", "smort/T-001", "-m", "merge(T-001): A0 to smort/dev"], work, check=True)
        run(["git", "push", "origin", "smort/dev"], work, check=True)
        run(["git", "checkout", "smort/T-001"], work, check=True)
        manifest_file = work / "verify/logs/e2e-slot.json"
        assert run(["scripts/verify/gate-brief", "--json-out", str(manifest_file)], work).returncode == 0
        r_sa = run(["scripts/verify/slot-apply", "--manifest", str(manifest_file), "--reply", "approve M0", "--execute", "--merge-mode", "git"], work)
        assert r_sa.returncode == 0, f"E2E slot-apply failed:\n{r_sa.stdout}\n{r_sa.stderr}"
        assert (work / "src/core/domain/calc.py").is_file()
        run(["git", "push", "origin", "main"], work, check=True, env={"SMORT_ALLOW_MAIN_PUSH": "1"})


SUITES = [
    ("1. Extraction (32 blocks), syntax, zero-dep, STOP-READING & cross-refs", suite_1_extraction_and_static_checks),
    ("2. Hot/Cold budgets (PROGRAM.md <= 5 KB), sharded handoffs & ratchets", suite_2_hot_set_and_ratchets),
    ("3. Base-ref auto-resolution across Git topologies", suite_3_base_ref_resolution),
    ("4. Unbounded cohesive tickets, parallel gate, smart gitleaks & --verify-red-cmd", suite_4_unbounded_ticket_and_gate),
    ("5. touch-set-check & hardened fake-work-scan (history + Shannon entropy)", suite_5_touch_set_and_fake_work),
    ("6. tasks-index full §5 delegation & batched git cat-file overlay", suite_6_tasks_index_delegation),
    ("7. project-map & live --section docs/PLAYBOOK.md & docs/OPERATIONS.md", suite_7_project_map_and_cold_docs),
    ("8. code-index polyglot, stat no-op cache, tsconfig aliases & scoped affected", suite_8_code_index_v7),
    ("9. ci-guard 2/4-space YAML, block scalars & expr timeouts", suite_9_ci_guard),
    ("10. claim-check & starter verify/claims.json", suite_10_claim_check),
    ("11. conflict-matrix parallel merge-tree & disjoint-path pre-filter", suite_11_conflict_matrix),
    ("12. gate-brief (M0, Risk-Sliced Maps, JSON) & lessons-reflect (O(log K) + --as-of)", suite_12_gate_brief_and_lessons),
    ("13. smort-resume 1-call startup packet, topic filter & redaction", suite_13_smort_resume),
    ("14. slot-apply deterministic batch reply, unverified guard & execution", suite_14_slot_apply),
    ("15. install-hooks mechanical pre-commit secret & pre-push main guards", suite_15_install_hooks),
    ("16. End-to-end smort v7 lifecycle smoke", suite_16_e2e_v7_lifecycle),
]


def main() -> int:
    passed, failed = 0, 0
    for name, fn in SUITES:
        try:
            fn()
            print(f"[PASS] {name}")
            passed += 1
        except Exception as exc:
            import traceback
            print(f"[FAIL] {name}: {exc}")
            traceback.print_exc()
            failed += 1
    print(f"\nSummary: {passed}/{len(SUITES)} suites passed, {failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
