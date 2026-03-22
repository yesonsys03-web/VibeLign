import unittest

from vibelign.core.secret_scan import scan_unified_diff_for_secrets


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


if __name__ == "__main__":
    _ = unittest.main()
