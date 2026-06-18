"""conftest.py for isis tests.

Collects per-test outcomes and writes a summary file to the same directory
at the end of the session:  test_results_<YYYYMMDD_HHMMSS>.txt
"""

import datetime
import os

import pytest

_results = []
_session_start = None


def pytest_sessionstart(session):
    global _session_start
    _session_start = datetime.datetime.now()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call":
        _results.append(
            {
                "name": item.nodeid,
                "outcome": rep.outcome,
                "duration": rep.duration,
                "longrepr": str(rep.longrepr) if rep.longrepr else "",
            }
        )


def pytest_sessionfinish(session, exitstatus):
    if not _results:
        return

    start = _session_start or datetime.datetime.now()
    ts = start.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(os.path.dirname(__file__), "test_results_%s.txt" % ts)

    passed = sum(1 for r in _results if r["outcome"] == "passed")
    failed = sum(1 for r in _results if r["outcome"] == "failed")
    errors = sum(1 for r in _results if r["outcome"] not in ("passed", "failed"))
    total = len(_results)
    elapsed = (datetime.datetime.now() - start).total_seconds()

    lines = [
        "=" * 70,
        "IS-IS SRv6 Test Results",
        "Run at  : %s" % start.strftime("%Y-%m-%d %H:%M:%S"),
        "Elapsed : %.1fs" % elapsed,
        "=" * 70,
        "",
        "Summary : %d passed, %d failed, %d errors  (total %d)"
        % (passed, failed, errors, total),
        "",
        "-" * 70,
    ]

    for r in _results:
        status = r["outcome"].upper()
        dur = "%.2fs" % r["duration"]
        lines.append("  [%-6s]  %s  (%s)" % (status, r["name"], dur))
        if r["longrepr"]:
            for ln in r["longrepr"].splitlines()[:30]:
                lines.append("            " + ln)

    lines.append("-" * 70)
    lines.append("")

    with open(out_path, "w") as fh:
        fh.write("\n".join(lines))

    print("\n  [results] saved %s" % out_path)
