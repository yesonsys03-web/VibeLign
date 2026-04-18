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


if __name__ == "__main__":
    _ = unittest.main()
