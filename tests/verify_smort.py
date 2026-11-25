#!/usr/bin/env python3
"""Comprehensive 12-suite zero-dependency verification harness for smort.md (v6 · 2026-11-25.v10).
Tests extraction, syntax, stdlib-only compliance, Hot/Cold context budgets, unbounded cohesive tickets,
base-ref auto-resolution, hardened gate/fake-work-scan/touch-set-check, full §5 tasks-index delegation,
project-map + PLAYBOOK.md live sections, polyglot/monorepo/comment-safe code-index, hardened ci-guard,
claim-check, conflict-matrix, gate-brief (M0 + --max-prs 5), and lessons-reflect (auto-compaction + Git --as-of)."""
import ast
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
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
# Suite 1: Extraction, Syntax, Zero-Dep, Cross-Refs, Placeholders, Collisions
# ---------------------------------------------------------------------------
def suite_1_extraction_and_static_checks():
    src = SMORT_MD.read_text(encoding="utf-8")
    assert "Template version: 2026-11-25.v10" in src
    assert len(re.findall(r"^~~~~", src, re.M)) == 56, "Expected 56 ~~~~ fence markers"

    # Zero stale old caps / undefined placeholders
    for bad in ("{{400}}", "{{800}}", "{{MAX_GATE_LINES}}", "{{5}}", "{{45}}", "{{T2}}"):
        assert bad not in src, f"Stale placeholder {bad} still present in smort.md"

    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        # Execute the exact §4.1 extractor snippet verbatim via subprocess
        ext_match = re.search(r"### 4\.1 .*?```bash\n(.*?)\n```", src, re.S)
        assert ext_match, "Missing §4.1 extractor block"
        r = run(["bash", "-c", ext_match.group(1)], work, env={"SMORT_FILE": str(SMORT_MD)})
        assert r.returncode == 0, f"§4.1 extractor failed:\n{r.stdout}\n{r.stderr}"
        assert "extracted 28 smort v6 files" in r.stdout

        expected_files = [
            "AGENTS.md", "PROGRAM.md", "PROJECT-MAP.md", "TASKS.md", "PRD.md",
            "ARCHITECTURE-TDD.md", "AUDIT.md", "AUDIT-LOG.md",
            "DEVELOPMENT-WORKFLOW.md", "HANDOFF.md", "docs/PLAYBOOK.md",
            "scripts/verify/_smort_lib.py", "scripts/verify/gate",
            "scripts/verify/touch-set-check", "scripts/verify/fake-work-scan",
            "scripts/verify/ratchet-check", "scripts/verify/tasks-index",
            "scripts/verify/project-map", "scripts/verify/code-index",
            "scripts/verify/conflict-matrix", "scripts/verify/gate-brief",
            "scripts/verify/lessons-reflect", "scripts/verify/project-checks.sh",
            "scripts/verify/ci-guard", "scripts/verify/claim-check",
            "verify/ratchet.json", "verify/claims.json", "verify/budgets.json",
        ]
        for rel in expected_files:
            p = work / rel
            assert p.is_file(), f"Missing extracted file: {rel}"
            if rel.startswith("scripts/verify/"):
                assert os.access(p, os.X_OK), f"Script not executable: {rel}"

        # Zero third-party imports & syntax clean
        stdlib = set(sys.stdlib_module_names) | {"_smort_lib"}
        for p in sorted((work / "scripts/verify").iterdir()):
            txt = p.read_text(encoding="utf-8")
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

        # Valid JSON configs
        for jf in ("verify/ratchet.json", "verify/claims.json", "verify/budgets.json"):
            json.loads((work / jf).read_text(encoding="utf-8"))

        # Zero stale AGENTS.md §5/§6.x/§7/§8/§9/§10/§2.4 cross-refs across extracted templates & claims.json
        stale_rx = re.compile(r"AGENTS\.md\s*(?:§|:)(?:5|6\.[1-9]|7|8|9|10|2\.4)")
        for rel in expected_files:
            if rel.endswith((".md", ".json")):
                hits = stale_rx.findall((work / rel).read_text(encoding="utf-8"))
                assert not hits, f"Stale AGENTS.md ref(s) in {rel}: {hits}"

        # Collision safety: re-running extractor never overwrites existing files
        (work / "AGENTS.md").write_text("CUSTOM OWNER CONTENT\n", encoding="utf-8")
        r2 = run(["bash", "-c", ext_match.group(1)], work, env={"SMORT_FILE": str(SMORT_MD)})
        assert r2.returncode == 0
        assert (work / "AGENTS.md").read_text(encoding="utf-8") == "CUSTOM OWNER CONTENT\n"
        assert (work / "AGENTS.md.smort-new").is_file()


# ---------------------------------------------------------------------------
# Suite 2: Hot/Cold Context Budgets, Sharded Handoffs & Ratchet Integrity
# ---------------------------------------------------------------------------
def suite_2_hot_set_and_ratchets():
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        assert extract_smort(work) == 28

        # Day-1 hot set passes
        r = run(["scripts/verify/ratchet-check", "--verify-config", "--budgets", "verify/budgets.json", "--check-hot-set"], work)
        assert r.returncode == 0, f"Day-1 hot set failed:\n{r.stdout}\n{r.stderr}"

        # Week-2 worst-case stress: full 4096 B HANDOFF + full 8192 B LESSONS + valid shard
        (work / "HANDOFF.md").write_text(("x" * 70 + "\n") * 55, encoding="utf-8")  # 3905 B, 55 lines
        (work / "verify/LESSONS.md").write_text(("# L\n" + ("y" * 79 + "\n") * 102)[:8192], encoding="utf-8")
        (work / "handoffs/builder-a.md").write_text("Active: T-001\n" * 20, encoding="utf-8")
        r_w2 = run(["scripts/verify/ratchet-check", "--budgets", "verify/budgets.json", "--check-hot-set", "--json"], work)
        assert r_w2.returncode == 0, f"Week-2 worst-case Hot Set failed:\n{r_w2.stdout}\n{r_w2.stderr}"
        rep = json.loads(r_w2.stdout)
        assert rep["total_bytes"] < 65536, f"Week-2 total bytes {rep['total_bytes']} >= 65536"
        assert rep["total_est_tokens"] < 18000, f"Week-2 tokens {rep['total_est_tokens']} >= 18000"
        assert "handoffs/builder-a.md" in rep["handoff_shards"]

        # Negative control: bloated sharded handoff > 4096 B fails
        (work / "handoffs/builder-bloated.md").write_text("z" * 4200 + "\n", encoding="utf-8")
        r_shard = run(["scripts/verify/ratchet-check", "--budgets", "verify/budgets.json", "--check-hot-set"], work)
        assert r_shard.returncode == 1 and "handoffs/builder-bloated.md" in r_shard.stdout
        (work / "handoffs/builder-bloated.md").unlink()

        # Negative control: sharded handoff > 60 lines fails
        (work / "handoffs/builder-long.md").write_text("line\n" * 65, encoding="utf-8")
        r_lines = run(["scripts/verify/ratchet-check", "--budgets", "verify/budgets.json", "--check-hot-set"], work)
        assert r_lines.returncode == 1 and "lines 65 > cap 60" in r_lines.stdout
        (work / "handoffs/builder-long.md").unlink()

        # Ratchet monotonic raise + regression block + exit 4 without ADR + allow with ADR
        assert run(["scripts/verify/ratchet-check", "--tests", "10", "--coverage", "80.0", "--update"], work).returncode == 0
        assert run(["scripts/verify/ratchet-check", "--tests", "9", "--coverage", "80.0"], work).returncode == 1
        assert run(["scripts/verify/ratchet-check", "--tests", "9", "--allow-lower"], work).returncode == 4
        assert run(["scripts/verify/ratchet-check", "--tests", "9", "--allow-lower", "--decision", "D-007", "--update"], work).returncode == 0

        # --verify-config catches invalid ratchet.json
        (work / "verify/ratchet.json").write_text('{"test_count": -1, "coverage_pct": 150}\n', encoding="utf-8")
        r_cfg = run(["scripts/verify/ratchet-check", "--verify-config"], work)
        assert r_cfg.returncode == 1 and "RATCHET CONFIG ERRORS" in r_cfg.stdout

        # Perf ceiling + sanity floor + baseline regression
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
    # Topology A: origin/main + origin/smort/dev (stage-smort-dev vs auto-merge-main)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        bare, work = root / "origin.git", root / "work"
        work.mkdir()
        init_git_repo(work, bare, default_branch="main")
        assert extract_smort(work) == 28
        commit_all(work, "chore: init")
        run(["git", "push", "-u", "origin", "main"], work, check=True)
        run(["git", "checkout", "-b", "smort/dev"], work, check=True)
        (work / "README.md").write_text("# App\n", encoding="utf-8")
        commit_all(work, "chore: dev branch")
        run(["git", "push", "-u", "origin", "smort/dev"], work, check=True)

        # On smort/dev itself -> should resolve origin/main (not itself!)
        r_dev = run(["python3", "scripts/verify/_smort_lib.py", "--resolve-base"], work)
        assert r_dev.returncode == 0 and r_dev.stdout.strip() == "origin/main", f"got: {r_dev.stdout!r}"

        # On smort/T-001 -> should resolve origin/smort/dev
        run(["git", "checkout", "-b", "smort/T-001"], work, check=True)
        r_t1 = run(["python3", "scripts/verify/_smort_lib.py", "--resolve-base"], work)
        assert r_t1.returncode == 0 and r_t1.stdout.strip() == "origin/smort/dev", f"got: {r_t1.stdout!r}"

        # Switch PROGRAM.md to explicit auto-merge-main -> resolves origin/main
        pm = (work / "PROGRAM.md").read_text(encoding="utf-8")
        pm = re.sub(r"\| `A0` continuous flow \|.*", "| `A0` continuous flow | `auto-merge-main` |", pm)
        (work / "PROGRAM.md").write_text(pm, encoding="utf-8")
        r_am = run(["python3", "scripts/verify/_smort_lib.py", "--resolve-base"], work)
        assert r_am.returncode == 0 and r_am.stdout.strip() == "origin/main", f"got: {r_am.stdout!r}"

        # Bogus explicit base fails loudly with exit 2
        r_bad = run(["python3", "scripts/verify/_smort_lib.py", "--resolve-base", "origin/does-not-exist"], work)
        assert r_bad.returncode == 2

    # Topology B: local-only repo with master branch (no origin remote)
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        init_git_repo(work, bare=None, default_branch="master")
        assert extract_smort(work) == 28
        commit_all(work, "chore: init master")
        run(["git", "checkout", "-b", "smort/T-001"], work, check=True)
        r_m = run(["python3", "scripts/verify/_smort_lib.py", "--resolve-base"], work)
        assert r_m.returncode == 0 and r_m.stdout.strip() == "master", f"got: {r_m.stdout!r}"


# ---------------------------------------------------------------------------
# Suite 4: Unbounded Cohesive Tickets & Hardened Gate
# ---------------------------------------------------------------------------
def suite_4_unbounded_ticket_and_gate():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        bare, work = root / "origin.git", root / "work"
        work.mkdir()
        init_git_repo(work, bare)
        assert extract_smort(work) == 28
        # Wire project-checks.sh to pass
        (work / "scripts/verify/project-checks.sh").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        (work / "scripts/verify/project-checks.sh").chmod(0o755)
        (work / "src/core/domain").mkdir(parents=True)
        (work / "src/core/domain/__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
        # Update PROJECT-MAP.md so src/core/domain is owned and non-placeholder
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

        # Branch task off smort/dev
        run(["git", "checkout", "-b", "smort/T-001"], work, check=True)
        merge_base_sha = run(["git", "rev-parse", "HEAD"], work, check=True).stdout.strip()

        # Commit Red failing test first
        (work / "tests").mkdir(exist_ok=True)
        (work / "tests/test_engine.py").write_text("def test_engine_works():\n    assert 1 == 1\n", encoding="utf-8")
        red_sha = commit_all(work, "test(T-001): add failing acceptance check")

        # Commit 650-line cohesive feature (well above old 400-line cap!)
        lines = [f"def step_{i}(x: int) -> int:\n    return x + {i}\n" for i in range(325)]
        (work / "src/core/domain/engine.py").write_text("\n".join(lines), encoding="utf-8")
        head_sha = commit_all(work, "feat(T-001): implement cohesive engine")

        # Gate passes WITHOUT --allow-large, auto-resolves origin/smort/dev, emits PoW + guaranteed final smort-done!
        env = {"SECRET_SCANNER_CMD": "true"}
        r = run(
            ["scripts/verify/gate", "--fast", "--task", "T-001", "--red-sha", red_sha, "--emit-pow"],
            work, env=env,
        )
        assert r.returncode == 0, f"650-line cohesive PR failed gate:\n{r.stdout}\n{r.stderr}"
        assert "unlimited" in r.stdout
        assert "### Proof of work: T-001" in r.stdout
        last_line = r.stdout.strip().splitlines()[-1]
        assert last_line.startswith("smort-done ok=1 exit=0"), f"Final line was not smort-done: {last_line!r}"

        # Opt-in --max-lines 200 still works when explicitly requested
        r_dry = run(["scripts/verify/gate", "--dry-run", "--max-lines", "200"], work, env=env)
        assert r_dry.returncode == 4, f"Expected exit 4 on opt-in --max-lines dry-run, got {r_dry.returncode}"
        r_cap = run(["scripts/verify/gate", "--fast", "--max-lines", "200"], work, env=env)
        assert r_cap.returncode == 1 and "opt-in cap 200" in r_cap.stdout

        # Negative control: untracked non-ignored file fails clean-tree
        (work / "stray_untracked.py").write_text("x = 1\n", encoding="utf-8")
        r_untr = run(["scripts/verify/gate", "--fast", "--task", "T-001", "--red-sha", red_sha], work, env=env)
        assert r_untr.returncode == 1 and "dirty working tree" in r_untr.stdout
        (work / "stray_untracked.py").unlink()

        # Negative controls: --red-sha HEAD and --red-sha merge-base both rejected
        r_red_head = run(["scripts/verify/gate", "--fast", "--task", "T-001", "--red-sha", head_sha], work, env=env)
        assert r_red_head.returncode == 1 and "equals HEAD" in r_red_head.stdout
        r_red_mb = run(["scripts/verify/gate", "--fast", "--task", "T-001", "--red-sha", merge_base_sha], work, env=env)
        assert r_red_mb.returncode == 1 and "strictly after merge-base" in r_red_mb.stdout

        # Negative control: bogus explicit --base fails loudly with exit 2
        r_bad_base = run(["scripts/verify/gate", "--fast", "--base", "origin/no-such-branch"], work, env=env)
        assert r_bad_base.returncode == 2 and "invalid-base" in r_bad_base.stdout

        # SMORT_ALLOWED_IDENT mismatch fails; match passes
        r_id_bad = run(["scripts/verify/gate", "--fast", "--task", "T-001", "--red-sha", red_sha], work, env={**env, "SMORT_ALLOWED_IDENT": "Other Bot <other@example.com>"})
        assert r_id_bad.returncode == 1 and "ident-guard" in r_id_bad.stdout
        r_id_ok = run(["scripts/verify/gate", "--fast", "--task", "T-001", "--red-sha", red_sha], work, env={**env, "SMORT_ALLOWED_IDENT": "Smort Tester <tester@example.com>"})
        assert r_id_ok.returncode == 0


# ---------------------------------------------------------------------------
# Suite 5: touch-set-check & Hardened fake-work-scan
# ---------------------------------------------------------------------------
def suite_5_touch_set_and_fake_work():
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        init_git_repo(work)
        assert extract_smort(work) == 28
        (work / "tasks/T-001-a0.md").write_text(make_task("T-001", approval="A0", touch_set=["src/**"]), encoding="utf-8")
        (work / "tasks/T-002-ci.md").write_text(make_task("T-002", approval="A1", touch_set=[".github/workflows/**"]), encoding="utf-8")
        (work / "tests").mkdir(exist_ok=True)
        (work / "tests/sample_test.go").write_text("package t\nfunc TestKeep() {}\nfunc TestDrop() {}\n", encoding="utf-8")
        (work / "tests/SampleTest.java").write_text("class S {\n  @Test void a(){}\n  @Test void b(){}\n}\n", encoding="utf-8")
        commit_all(work, "chore: base")

        # 5a: A0 task touching sensitive auth path blocked by touch-set-check
        run(["git", "checkout", "-b", "smort/T-001"], work, check=True)
        (work / "src/auth").mkdir(parents=True)
        (work / "src/auth/login.py").write_text("def login(): return True\n", encoding="utf-8")
        commit_all(work, "feat: auth")
        r_sens = run(["scripts/verify/touch-set-check", "T-001"], work)
        assert r_sens.returncode == 1 and "A0 SENSITIVE-PATH ESCALATION" in r_sens.stdout

        # 5b: Builder editing scripts/verify/gate is ALWAYS blocked (even with A1 task!)
        run(["git", "checkout", "-b", "smort/tamper", "main"], work, check=True)
        (work / "tasks/T-099-evil.md").write_text(make_task("T-099", approval="A1", touch_set=["scripts/verify/**"]), encoding="utf-8")
        (work / "scripts/verify/gate").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        commit_all(work, "chore: try tamper")
        r_tamp = run(["scripts/verify/fake-work-scan", "--lane", "builder", "--task", "T-099"], work)
        assert r_tamp.returncode == 1 and "immutable verification script/config" in r_tamp.stdout
        r_int = run(["scripts/verify/fake-work-scan", "--lane", "integration"], work)
        assert r_int.returncode == 0

        # 5c: Authorized A1 builder editing .github/workflows/ci.yml in touch_set is ALLOWED; without A1 task is BLOCKED
        run(["git", "checkout", "-b", "smort/T-002", "main"], work, check=True)
        (work / ".github/workflows").mkdir(parents=True)
        (work / ".github/workflows/ci.yml").write_text("name: CI\non: [push]\njobs:\n  t:\n    runs-on: ubuntu-latest\n    timeout-minutes: 10\n    steps:\n      - run: echo ok\n", encoding="utf-8")
        commit_all(work, "ci: add workflow")
        assert run(["scripts/verify/fake-work-scan", "--lane", "builder"], work).returncode == 1
        assert run(["scripts/verify/fake-work-scan", "--lane", "builder", "--task", "T-002"], work).returncode == 0

        # 5d: Python multi-line except: pass + Go/Java test deletion + --staged secret catch
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

        # --staged catches secret before commit
        fake_gh = "ghp_" + "A1b2C3d4E5f6" * 3
        (work / "src/leak.py").write_text(f'TOKEN = "{fake_gh}"\n', encoding="utf-8")
        run(["git", "add", "src/leak.py"], work, check=True)
        r_stg = run(["scripts/verify/fake-work-scan", "--staged"], work)
        assert r_stg.returncode == 1 and "secret literal detected" in r_stg.stdout

        # --redact strips secrets cleanly
        r_red = run(["scripts/verify/fake-work-scan", "--redact"], work, input_text=f"auth Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abcdefghijk123456 and {fake_gh}\n")
        assert r_red.returncode == 0 and fake_gh not in r_red.stdout and "[redacted]" in r_red.stdout


# ---------------------------------------------------------------------------
# Suite 6: tasks-index Full §5 Delegation Alignment
# ---------------------------------------------------------------------------
def suite_6_tasks_index_delegation():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        bare, work = root / "origin.git", root / "work"
        work.mkdir()
        init_git_repo(work, bare)
        assert extract_smort(work) == 28

        # Configure real PROJECT-MAP.md with S1.C1 (Order 1, verified), S1.C2 (Order 2, built), S2.C1 (Order 3, planned)
        (work / "src/c1").mkdir(parents=True)
        (work / "src/c2").mkdir(parents=True)
        (work / "src/c3").mkdir(parents=True)
        (work / "src/c1/a.py").write_text("x = 1\n", encoding="utf-8")
        (work / "src/c2/b.py").write_text("y = 2\n", encoding="utf-8")
        pm = (work / "PROJECT-MAP.md").read_text(encoding="utf-8")
        pm = pm.replace("{{src,lib,app}}", "src")
        pm = pm.replace("| S1.C1 | {{Domain types & rules}} | Component | L0 | data | planned | `{{src/core/domain}}`", "| S1.C1 | Core | Component | L0 | data | verified | `src/c1`")
        pm = pm.replace("| S1.C2 | {{Storage adapter}} | Component | L1 | data | planned | `{{src/core/storage}}`", "| S1.C2 | Store | Component | L1 | data | built | `src/c2`")
        pm = pm.replace("| S2.C1 | {{API / UI boundary}} | Component | L3 | backend | planned | `{{src/api}}`", "| S2.C1 | API | Component | L3 | backend | planned | `src/c3`")
        (work / "PROJECT-MAP.md").write_text(pm, encoding="utf-8")
        run(["scripts/verify/project-map"], work, check=True)

        # Tasks testing: build order, dependents unblocked, estimate S < M < L, DO_NOT_TOUCH
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

        # Ranking check: T-012 (Order 1, unblocks 2) -> T-011 (Order 1, S) -> T-010 (Order 1, L) -> T-015 (Order 2); T-016 blocked by DO_NOT_TOUCH!
        r = run(["scripts/verify/tasks-index", "--live", "--next", "--do-not-touch", "src/c1/secret.py", "--json"], work)
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        ids = [x["id"] for x in data["next"]]
        assert ids == ["T-012", "T-011", "T-010", "T-015"], f"Unexpected §5 ranking: {ids}"
        assert data["not_shown"]["blocked_do_not_touch"] == 1
        assert data["not_shown"]["blocked_deps"] == 2

        # Lifecycle maintenance stops delegation cleanly
        prog = (work / "PROGRAM.md").read_text(encoding="utf-8")
        prog_maint = re.sub(r"\| Lifecycle mode \|.*", "| Lifecycle mode | `maintenance` |", prog)
        (work / "PROGRAM.md").write_text(prog_maint, encoding="utf-8")
        r_m = run(["scripts/verify/tasks-index", "--live", "--next", "--compact"], work)
        assert r_m.returncode == 0 and "@no why=lifecycle=maintenance" in r_m.stdout

        # Release freeze pauses builders but allows integration lane
        prog_frz = re.sub(r"\| Release freeze \|.*", "| Release freeze | on since 2026-11-25 |", prog)
        (work / "PROGRAM.md").write_text(prog_frz, encoding="utf-8")
        r_frz = run(["scripts/verify/tasks-index", "--live", "--next", "--lane", "backend", "--compact"], work)
        assert "@no why=release_freeze=on" in r_frz.stdout
        (work / "PROGRAM.md").write_text(prog, encoding="utf-8")

        # Shrink-guard exits 4 if a task disappears without archiving
        (work / "tasks/T-016-dnt.md").unlink()
        r_sh = run(["scripts/verify/tasks-index"], work)
        assert r_sh.returncode == 4 and "SHRINK-GUARD" in r_sh.stderr


# ---------------------------------------------------------------------------
# Suite 7: project-map & Live --section Reading docs/PLAYBOOK.md
# ---------------------------------------------------------------------------
def suite_7_project_map_and_playbook():
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        init_git_repo(work)
        assert extract_smort(work) == 28
        commit_all(work, "chore: init")

        # Starter PROJECT-MAP.md passes --check on Day 1 with zero drift
        r = run(["scripts/verify/project-map", "--check"], work)
        assert r.returncode == 0, f"Day-1 project-map --check failed:\n{r.stdout}\n{r.stderr}"

        # Live --section discovers docs/PLAYBOOK.md automatically!
        r_sec = run(["scripts/verify/project-map", "--section", "3. Work verifiability"], work)
        assert r_sec.returncode == 0 and "docs/PLAYBOOK.md" in r_sec.stdout and "Acceptance checks come first" in r_sec.stdout

        # --impact --compact
        r_imp = run(["scripts/verify/project-map", "--impact", "S1.C1", "--compact"], work)
        assert r_imp.returncode == 0 and "@ok target=S1.C1 constituents=S1.C1,S1.C2,S2.C1" in r_imp.stdout

        # Negative control: banned 0.5 confidence fails
        pm = (work / "PROJECT-MAP.md").read_text(encoding="utf-8")
        (work / "PROJECT-MAP.md").write_text(pm.replace("| EXTRACTED |", "| INFERRED (0.5) |", 1), encoding="utf-8")
        r_c = run(["scripts/verify/project-map", "--check"], work)
        assert r_c.returncode == 1 and "0.5 is banned" in r_c.stdout
        (work / "PROJECT-MAP.md").write_text(pm, encoding="utf-8")

        # Negative control: path traversal rejected
        r_tr = run(["scripts/verify/project-map", "--section", "anything", "--file", "../etc/passwd"], work)
        assert r_tr.returncode == 1


# ---------------------------------------------------------------------------
# Suite 8: code-index Polyglot, Monorepo & Comment-Safe Hub Bypass
# ---------------------------------------------------------------------------
def suite_8_code_index_polyglot_and_bypass():
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        init_git_repo(work)
        assert extract_smort(work) == 28
        # Polyglot files + user scripts/ + nested monorepo manifest
        for d in ("src/auth", "src/api", "src/jvm/com/app", "src/native", "src/dotnet", "infra/modules/vpc", "infra/env", "db", "scripts", "packages/web"):
            (work / d).mkdir(parents=True, exist_ok=True)
        (work / "src/auth/hub.py").write_text("def verify_jwt(tok: str) -> bool:\n    return bool(tok)\n", encoding="utf-8")
        (work / "src/api/good.py").write_text("from src.auth.hub import verify_jwt\ndef handle(t):\n    return verify_jwt(t)\n", encoding="utf-8")
        # Comment-only mention of jwt.decode must NOT trigger false bypass!
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
        commit_all(work, "feat: polyglot fixture")

        r_b = run(["scripts/verify/code-index", "build", "--worktree", "isolated"], work)
        assert r_b.returncode == 0, f"code-index build failed:\n{r_b.stdout}\n{r_b.stderr}"
        caches = list((work / "verify").glob("code-index-*.json"))
        assert len(caches) == 1
        idx = json.loads(caches[0].read_text(encoding="utf-8"))

        # Check all polyglot files + user scripts/helper.py indexed, scripts/verify/* excluded
        assert "scripts/helper.py" in idx["files"]
        assert not any(f.startswith("scripts/verify/") for f in idx["files"])
        for f in (
            "src/jvm/com/app/ApiController.java",
            "src/native/calc.cpp",
            "src/dotnet/Billing.cs",
            "infra/env/main.tf",
            "db/schema.sql",
        ):
            assert f in idx["files"], f"Missing polyglot file {f}"
        # Monorepo nested manifest discovered
        assert "packages/web/package.json" in idx["manifests"] and "react" in idx["manifests"]["packages/web/package.json"]
        # Cross-file edges resolved for Python, Java, C++, and Terraform
        edge_pairs = {(e["source"], e["target"]) for e in idx["edges"]}
        assert ("src/api/good.py", "src/auth/hub.py") in edge_pairs
        assert ("src/jvm/com/app/ApiController.java", "src/jvm/com/app/TokenService.java") in edge_pairs
        assert ("src/native/calc.cpp", "src/native/math.h") in edge_pairs
        assert ("infra/env/main.tf", "infra/modules/vpc/main.tf") in edge_pairs

        # Comment-safe bypass check: comments_only.py and comments_ts.ts must NOT trigger!
        r_bp_ok = run(["scripts/verify/code-index", "bypass", "src/auth/hub.py", "--pattern", r"jwt\.decode\("], work)
        assert r_bp_ok.returncode == 0, f"Comment triggered false bypass:\n{r_bp_ok.stdout}"

        # Real bypass IS caught!
        (work / "src/api/rogue.py").write_text("import jwt\ndef evil(t):\n    return jwt.decode(t)\n", encoding="utf-8")
        commit_all(work, "feat: rogue bypass")
        r_bp_fail = run(["scripts/verify/code-index", "bypass", "src/auth/hub.py", "--pattern", r"jwt\.decode\("], work)
        assert r_bp_fail.returncode == 1 and "src/api/rogue.py:L3" in r_bp_fail.stdout


# ---------------------------------------------------------------------------
# Suite 9: ci-guard 2/4-Space, Block Scalars & Expression Timeouts
# ---------------------------------------------------------------------------
def suite_9_ci_guard():
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        assert extract_smort(work) == 28
        r_st = run(["scripts/verify/ci-guard", "--self-test"], work)
        assert r_st.returncode == 0 and "self-test: PASS" in r_st.stdout

        wf = work / ".github/workflows"
        wf.mkdir(parents=True)
        # 4-space YAML with heredoc decoy and expression timeout
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
        assert extract_smort(work) == 28
        commit_all(work, "chore: init")
        r_st = run(["scripts/verify/claim-check", "--self-test"], work)
        assert r_st.returncode == 0 and "self-test: PASS" in r_st.stdout
        r_ok = run(["scripts/verify/claim-check"], work)
        assert r_ok.returncode == 0, f"Starter templates failed claim-check:\n{r_ok.stdout}\n{r_ok.stderr}"

        # Negative controls
        (work / "BAD.md").write_text("CI is green even though CI was unavailable locally.\n\nEvidence verified at /tmp/local_run.log.\n", encoding="utf-8")
        r_bad = run(["scripts/verify/claim-check", "BAD.md"], work)
        assert r_bad.returncode == 1
        assert "SMORT-NO-FALSE-CI-GREEN" in r_bad.stdout
        assert "SMORT-NO-LOCAL-EVIDENCE" in r_bad.stdout


# ---------------------------------------------------------------------------
# Suite 11: conflict-matrix (Spaces in Path, Worktree Cache, Second Precision)
# ---------------------------------------------------------------------------
def suite_11_conflict_matrix():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        bare, work = root / "origin.git", root / "work"
        work.mkdir()
        init_git_repo(work, bare)
        assert extract_smort(work) == 28
        (work / "src/core/domain").mkdir(parents=True)
        (work / "src/core/domain/my file.py").write_text("A = 1\n", encoding="utf-8")
        pm = (work / "PROJECT-MAP.md").read_text(encoding="utf-8")
        pm = pm.replace("{{src,lib,app}}", "src").replace("{{src/core/domain}}", "src/core/domain")
        (work / "PROJECT-MAP.md").write_text(pm, encoding="utf-8")
        commit_all(work, "chore: base")
        run(["git", "push", "-u", "origin", "main"], work, check=True)

        # Two branches editing the same file with spaces in name
        run(["git", "checkout", "-b", "smort/T-001", "main"], work, check=True)
        (work / "src/core/domain/my file.py").write_text("A = 2\n", encoding="utf-8")
        commit_all(work, "feat(T-001): change to 2")
        run(["git", "push", "-u", "origin", "smort/T-001"], work, check=True)

        run(["git", "checkout", "-b", "smort/T-002", "main"], work, check=True)
        (work / "src/core/domain/my file.py").write_text("A = 3\n", encoding="utf-8")
        commit_all(work, "feat(T-002): change to 3")
        run(["git", "push", "-u", "origin", "smort/T-002"], work, check=True)

        r = run(["scripts/verify/conflict-matrix", "--worktree", "isolated"], work)
        assert r.returncode == 1, f"Expected conflict exit 1, got {r.returncode}: {r.stdout}"
        reports = sorted((work / "verify/conflicts").glob("*.md"))
        assert len(reports) == 1
        assert re.match(r"^\d{4}-\d{2}-\d{2}-\d{6}\.md$", reports[0].name), f"Not second-precision: {reports[0].name}"
        content = reports[0].read_text(encoding="utf-8")
        assert "src/core/domain/my file.py" in content, f"Space-containing path mangled:\n{content}"
        assert "SEMANTIC-RISK" in content and "S1.C1" in content


# ---------------------------------------------------------------------------
# Suite 12: gate-brief (M0 + --max-prs 5 No-Starvation) & lessons-reflect (Auto-Compaction + Git --as-of)
# ---------------------------------------------------------------------------
def suite_12_gate_brief_and_lessons():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        bare, work = root / "origin.git", root / "work"
        work.mkdir()
        init_git_repo(work, bare)
        assert extract_smort(work) == 28
        (work / "src").mkdir(exist_ok=True)
        (work / "src/mod.py").write_text("V = 1\n", encoding="utf-8")
        commit_all(work, "chore: base v1", env={"GIT_AUTHOR_DATE": "2026-10-01T10:00:00Z", "GIT_COMMITTER_DATE": "2026-10-01T10:00:00Z"})
        run(["git", "push", "-u", "origin", "main"], work, check=True)

        # Stage 2 autonomous A0 commits onto smort/dev
        run(["git", "checkout", "-b", "smort/dev"], work, check=True)
        (work / "src/a0_one.py").write_text("X = 1\n", encoding="utf-8")
        commit_all(work, "feat(T-001): A0 one", env={"GIT_AUTHOR_DATE": "2026-10-02T10:00:00Z", "GIT_COMMITTER_DATE": "2026-10-02T10:00:00Z"})
        (work / "src/a0_two.py").write_text("Y = 2\n", encoding="utf-8")
        commit_all(work, "feat(T-002): A0 two", env={"GIT_AUTHOR_DATE": "2026-10-03T10:00:00Z", "GIT_COMMITTER_DATE": "2026-10-03T10:00:00Z"})
        run(["git", "push", "-u", "origin", "smort/dev"], work, check=True)

        # Create 6 verified A1 PR branches off origin/smort/dev (first one is 950 lines!)
        for idx in range(1, 7):
            tid = f"T-10{idx}"
            run(["git", "checkout", "-b", f"smort/{tid}", "origin/smort/dev"], work, check=True)
            (work / f"tasks/{tid}-a1.md").write_text(
                make_task(tid, f"A1 feature {idx}", approval="A1", status="awaiting-slot", approval_reason="auth change"),
                encoding="utf-8",
            )
            nlines = 950 if idx == 1 else 40
            (work / f"src/a1_{idx}.py").write_text("\n".join(f"V_{j} = {j}" for j in range(nlines)) + "\n", encoding="utf-8")
            commit_all(work, f"feat({tid}): A1 {idx}")
            run(["git", "push", "-u", "origin", f"smort/{tid}"], work, check=True)

        run(["git", "checkout", "smort/dev"], work, check=True)
        # Switch to a task branch so resolve_base_ref picks origin/smort/dev automatically
        run(["git", "checkout", "smort/T-101"], work, check=True)
        r_gb = run(["scripts/verify/gate-brief", "--slot", "Evening"], work)
        assert r_gb.returncode == 0, f"gate-brief failed:\n{r_gb.stderr}"
        out = r_gb.stdout
        assert "`M0`" in out and "origin/smort/dev -> origin/main" in out, f"Missing M0:\n{out}"
        assert "approve M0 M1 M2 M3 M4 M5" in out, f"Bad reply template:\n{out}"
        assert "T-101" in out and "950" in out, "950-line cohesive A1 PR was starved!"
        assert "a1_overflow_deferred=1" in out, f"Expected 1 deferred PR:\n{out}"

        # Even with explicit opt-in --max-lines 200, first 950-line PR is NEVER starved!
        r_gb2 = run(["scripts/verify/gate-brief", "--max-lines", "200"], work)
        assert r_gb2.returncode == 0 and "T-101" in r_gb2.stdout and "a1_overflow_deferred=5" in r_gb2.stdout

        # lessons-reflect: Git-backed --as-of historical SHA-256 verification
        run(["git", "checkout", "main"], work, check=True)
        # Log lesson against src/mod.py v1 at 2026-10-02
        r_log = run([
            "scripts/verify/lessons-reflect", "log",
            "--topic", "mod-v1-rule", "--outcome", "useful",
            "--note", "Keep V=1 invariant", "--files", "src/mod.py",
            "--task", "T-001", "--ts", "2026-10-02T12:00:00Z", "--human",
        ], work)
        assert r_log.returncode == 0
        # Mutate src/mod.py to v2 at 2026-10-10
        (work / "src/mod.py").write_text("V = 2\n", encoding="utf-8")
        commit_all(work, "feat: bump mod to v2", env={"GIT_AUTHOR_DATE": "2026-10-10T10:00:00Z", "GIT_COMMITTER_DATE": "2026-10-10T10:00:00Z"})

        # Live build retires mod-v1-rule because live src/mod.py != v1
        r_live = run(["scripts/verify/lessons-reflect", "build", "--now", "2026-10-15T12:00:00Z", "--json"], work)
        ov_live = json.loads(r_live.stdout)
        assert ov_live["stale_evicted"] == 1 and "mod-v1-rule" not in ov_live["human_overrides"]

        # Historical --as-of 2026-10-05: commit at that date had src/mod.py == v1 -> ACTIVE!
        r_past_ok = run(["scripts/verify/lessons-reflect", "build", "--as-of", "2026-10-05", "--json"], work)
        ov_past_ok = json.loads(r_past_ok.stdout)
        assert ov_past_ok["stale_evicted"] == 0 and "mod-v1-rule" in ov_past_ok["human_overrides"], f"Git --as-of 2026-10-05 failed: {ov_past_ok}"

        # Historical --as-of 2026-10-15: commit at that date had src/mod.py == v2 -> RETIRED!
        r_past_stale = run(["scripts/verify/lessons-reflect", "build", "--as-of", "2026-10-15", "--json"], work)
        ov_past_stale = json.loads(r_past_stale.stdout)
        assert ov_past_stale["stale_evicted"] == 1 and "mod-v1-rule" not in ov_past_stale["human_overrides"], f"Git --as-of 2026-10-15 failed: {ov_past_stale}"

        # Auto-compaction (--max-bytes 8192) keeps verify/LESSONS.md <= 8192 B and hot-set green
        for i in range(60):
            run([
                "scripts/verify/lessons-reflect", "log",
                "--topic", f"topic-{i:03d}", "--outcome", "useful",
                "--note", f"Detailed architectural lesson number {i} " + ("detail " * 25),
                "--task", f"T-{i:03d}", "--ts", "2026-10-14T12:00:00Z",
            ], work, check=True)
        r_b = run(["scripts/verify/lessons-reflect", "build", "--now", "2026-10-15T12:00:00Z"], work)
        assert r_b.returncode == 0, r_b.stderr
        l_bytes = len((work / "verify/LESSONS.md").read_bytes())
        assert l_bytes <= 8192, f"LESSONS.md exceeded 8192 B: {l_bytes}"
        ov_comp = json.loads((work / "verify/.lessons_overlay.json").read_text(encoding="utf-8"))
        assert ov_comp["not_shown"]["trimmed_for_budget"] > 0
        # Passes ratchet-check --check-hot-set!
        r_hs = run(["scripts/verify/ratchet-check", "--budgets", "verify/budgets.json", "--check-hot-set"], work)
        assert r_hs.returncode == 0, f"Hot-set failed after lessons compaction:\n{r_hs.stdout}"


SUITES = [
    ("1. Extraction, syntax, zero-dep, cross-refs, placeholders", suite_1_extraction_and_static_checks),
    ("2. Hot/Cold context budgets, sharded handoffs & ratchets", suite_2_hot_set_and_ratchets),
    ("3. Base-ref auto-resolution across Git topologies", suite_3_base_ref_resolution),
    ("4. Unbounded cohesive tickets & hardened gate", suite_4_unbounded_ticket_and_gate),
    ("5. touch-set-check & hardened fake-work-scan", suite_5_touch_set_and_fake_work),
    ("6. tasks-index full §5 delegation alignment", suite_6_tasks_index_delegation),
    ("7. project-map & live --section docs/PLAYBOOK.md", suite_7_project_map_and_playbook),
    ("8. code-index polyglot, monorepo & comment-safe bypass", suite_8_code_index_polyglot_and_bypass),
    ("9. ci-guard 2/4-space, block scalars & expr timeouts", suite_9_ci_guard),
    ("10. claim-check & starter verify/claims.json", suite_10_claim_check),
    ("11. conflict-matrix spaces, worktree cache & timestamps", suite_11_conflict_matrix),
    ("12. gate-brief (M0 + --max-prs) & lessons-reflect (compact + --as-of)", suite_12_gate_brief_and_lessons),
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
