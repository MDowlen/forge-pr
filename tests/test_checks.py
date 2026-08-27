from forge_pr.checks import deterministic_diff_checks


def test_blocks_conflict_markers_and_obvious_secret():
    patch = '''diff --git a/app.py b/app.py
+<<<<<<< HEAD
+api_key = "super-secret-value"
+=======
+print("safe")
+>>>>>>> branch
'''
    checks, findings = deterministic_diff_checks(patch)
    by_name = {check.name: check for check in checks}
    assert by_name["merge-conflict-markers"].passed is False
    assert by_name["merge-conflict-markers"].blocking is True
    assert by_name["obvious-secret-pattern"].passed is False
    assert not findings


def test_large_patch_is_warning_not_blocker():
    patch = "\n".join(f"+line {index}" for index in range(1301))
    checks, findings = deterministic_diff_checks(patch)
    patch_check = next(item for item in checks if item.name == "patch-size")
    assert patch_check.passed is False
    assert patch_check.blocking is False
    assert findings[0].code == "large-change"
