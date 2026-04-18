import subprocess
import tempfile
import unittest
from pathlib import Path

from vibelign.core.secret_scan import (
    parse_git_log_chunks,
    scan_all_history,
    scan_unified_diff_for_secrets,
)


def _git(root: Path, *args: str) -> None:
    _ = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


def _init_git_repo(root: Path) -> None:
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test User")
    _git(root, "config", "commit.gpgsign", "false")
    _git(root, "config", "core.autocrlf", "false")


class SecretScanTest(unittest.TestCase):
    def test_detects_private_key_header(self):
        diff = "@@ -0,0 +1 @@\n+-----BEGIN PRIVATE KEY-----\n"
        findings = scan_unified_diff_for_secrets(diff, "secrets.txt")
        self.assertEqual(findings[0].rule_id, "private-key")

    def test_skips_env_placeholder(self):
        diff = "@@ -0,0 +1 @@\n+api_key: ENV\n"
        findings = scan_unified_diff_for_secrets(diff, ".vibelign/config.yaml")
        self.assertEqual(findings, [])

    def test_detects_generic_secret_assignment(self):
        diff = '@@ -0,0 +1 @@\n+api_key = "supersecretvalue123456"\n'
        findings = scan_unified_diff_for_secrets(diff, "app.py")
        self.assertEqual(findings[0].rule_id, "generic-secret")

    def test_allow_marker_suppresses_detection(self):
        diff = (
            "@@ -0,0 +1 @@\n"
            '+api_key = "supersecretvalue123456"  # vibelign: allow-secret\n'
        )
        findings = scan_unified_diff_for_secrets(diff, "app.py")
        self.assertEqual(findings, [])

    def test_high_confidence_match_is_not_duplicated(self):
        diff = '@@ -0,0 +1 @@\n+api_key = "ghp_abcdefghijklmnopqrstuvwxyz123456"\n'
        findings = scan_unified_diff_for_secrets(diff, "app.py")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "github-token")

    def test_detects_jwt_token(self):
        jwt = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            ".eyJzdWIiOiIxMjM0NTY3ODkwIn0"
            ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        )
        diff = f'@@ -0,0 +1 @@\n+auth = "{jwt}"\n'
        findings = scan_unified_diff_for_secrets(diff, "app.py")
        self.assertTrue(any(f.rule_id == "jwt-token" for f in findings))

    def test_detects_postgres_url_with_password(self):
        diff = (
            "@@ -0,0 +1 @@\n"
            '+DATABASE_URL = "postgres://admin:supersecret123@db.example.com:5432/app"\n'
        )
        findings = scan_unified_diff_for_secrets(diff, "config.py")
        self.assertTrue(any(f.rule_id == "db-url-with-password" for f in findings))

    def test_detects_mongodb_srv_url_with_password(self):
        diff = (
            "@@ -0,0 +1 @@\n"
            '+uri = "mongodb+srv://user:mypassword@cluster.mongodb.net/db"\n'
        )
        findings = scan_unified_diff_for_secrets(diff, "config.py")
        self.assertTrue(any(f.rule_id == "db-url-with-password" for f in findings))

    def test_postgres_url_without_password_is_not_flagged(self):
        diff = '@@ -0,0 +1 @@\n+DATABASE_URL = "postgres://localhost:5432/app"\n'
        findings = scan_unified_diff_for_secrets(diff, "config.py")
        self.assertFalse(any(f.rule_id == "db-url-with-password" for f in findings))

    def test_detects_gcp_service_account_signature(self):
        diff = '@@ -0,0 +1 @@\n+  "type": "service_account",\n'
        findings = scan_unified_diff_for_secrets(diff, "creds.json")
        self.assertTrue(any(f.rule_id == "gcp-service-account" for f in findings))


class ParseGitLogChunksTest(unittest.TestCase):
    def test_parses_single_commit_single_file(self):
        lines = [
            "COMMIT_MARKER_abc123def\n",
            "diff --git a/app.py b/app.py\n",
            "@@ -0,0 +1 @@\n",
            '+password = "secret"\n',
        ]
        chunks = list(parse_git_log_chunks(lines))
        self.assertEqual(len(chunks), 1)
        sha, fname, diff_text = chunks[0]
        self.assertEqual(sha, "abc123def")
        self.assertEqual(fname, "app.py")
        self.assertIn('+password = "secret"', diff_text)

    def test_parses_multiple_commits(self):
        lines = [
            "COMMIT_MARKER_aaa\n",
            "diff --git a/a.py b/a.py\n",
            "+x\n",
            "COMMIT_MARKER_bbb\n",
            "diff --git a/b.py b/b.py\n",
            "+y\n",
        ]
        chunks = list(parse_git_log_chunks(lines))
        self.assertEqual(len(chunks), 2)
        self.assertEqual((chunks[0][0], chunks[0][1]), ("aaa", "a.py"))
        self.assertEqual((chunks[1][0], chunks[1][1]), ("bbb", "b.py"))

    def test_parses_commit_with_multiple_files(self):
        lines = [
            "COMMIT_MARKER_sha\n",
            "diff --git a/a.py b/a.py\n",
            "+foo\n",
            "diff --git a/b.py b/b.py\n",
            "+bar\n",
        ]
        chunks = list(parse_git_log_chunks(lines))
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0][1], "a.py")
        self.assertEqual(chunks[1][1], "b.py")

    def test_parses_crlf_line_endings(self):
        lines = [
            "COMMIT_MARKER_sha\r\n",
            "diff --git a/a.py b/a.py\r\n",
            "+foo\r\n",
        ]
        chunks = list(parse_git_log_chunks(lines))
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0][1], "a.py")

    def test_ignores_lines_before_first_diff(self):
        lines = [
            "COMMIT_MARKER_sha\n",
            "Author: Someone <a@b.c>\n",
            "Date: today\n",
            "\n",
            "    commit message\n",
            "\n",
            "diff --git a/a.py b/a.py\n",
            "+foo\n",
        ]
        chunks = list(parse_git_log_chunks(lines))
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0][1], "a.py")


class ScanAllHistoryTest(unittest.TestCase):
    def test_returns_empty_for_non_git_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = scan_all_history(Path(tmp))
            self.assertEqual(result.findings, [])

    def test_finds_secret_in_past_commit_even_after_removal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_git_repo(root)
            leaked = root / "app.py"
            _ = leaked.write_text(
                'password = "supersecretvalue123456"\n',  # vibelign: allow-secret
                encoding="utf-8",
            )
            _git(root, "add", ".")
            _git(root, "commit", "-q", "-m", "oops")
            _ = leaked.write_text('password = "SAFE"\n', encoding="utf-8")
            _git(root, "add", ".")
            _git(root, "commit", "-q", "-m", "fix")

            result = scan_all_history(root)
            self.assertTrue(
                any(f.rule_id == "generic-secret" for f in result.findings),
                f"Expected generic-secret in findings: {result.findings}",
            )

    def test_progress_callback_reports_commit_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_git_repo(root)
            for i in range(3):
                f = root / f"f{i}.txt"
                _ = f.write_text(f"v{i}\n", encoding="utf-8")
                _git(root, "add", ".")
                _git(root, "commit", "-q", "-m", f"c{i}")

            calls: list[tuple[int, int | None]] = []
            _ = scan_all_history(
                root, on_progress=lambda done, total: calls.append((done, total))
            )
            self.assertGreater(len(calls), 0)
            done_final, total_final = calls[-1]
            self.assertEqual(done_final, 3)
            self.assertEqual(total_final, 3)

    def test_clean_repo_returns_no_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_git_repo(root)
            f = root / "readme.md"
            _ = f.write_text("# Hello world\n", encoding="utf-8")
            _git(root, "add", ".")
            _git(root, "commit", "-q", "-m", "init")

            result = scan_all_history(root)
            self.assertEqual(result.findings, [])

    def test_skips_scanner_self_test_fixture_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_git_repo(root)
            fixture = root / "tests" / "test_secret_scan.py"
            fixture.parent.mkdir(parents=True, exist_ok=True)
            _ = fixture.write_text(
                'password = "supersecretvalue123456"\n',  # vibelign: allow-secret
                encoding="utf-8",
            )
            _git(root, "add", ".")
            _git(root, "commit", "-q", "-m", "fixture")

            result = scan_all_history(root)
            self.assertEqual(
                result.findings,
                [],
                f"expected fixture file to be skipped: {result.findings}",
            )


if __name__ == "__main__":
    _ = unittest.main()
