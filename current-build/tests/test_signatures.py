"""Behavioral tests for `urlcheck.signatures`.

Black-box tests over the three public detection functions plus
`reason_for_status`. Inputs are dict-like headers (mapping `items()`) or
raw bytes for bodies. Reason strings are referenced via module constants
so tests don't break when wording is improved.

Run with:
    python -m unittest tests.test_signatures -v
"""

from __future__ import annotations

import unittest

from urlcheck.signatures import (
    REASON_403,
    REASON_429,
    REASON_503,
    REASON_AKAMAI,
    REASON_CLOUDFLARE,
    REASON_DATADOME,
    REASON_GENERIC_CHALLENGE,
    REASON_PERIMETERX,
    detect_block,
    detect_block_in_body,
    detect_block_in_headers,
    reason_for_status,
)


# ---------------------------------------------------------------------------
# Header detection
# ---------------------------------------------------------------------------

class HeaderDetectionCloudflare(unittest.TestCase):

    def test_server_header_cloudflare_lowercase(self):
        self.assertEqual(
            detect_block_in_headers({"Server": "cloudflare"}),
            REASON_CLOUDFLARE,
        )

    def test_server_header_cloudflare_titlecase(self):
        # Server-header values are matched case-insensitively.
        self.assertEqual(
            detect_block_in_headers({"Server": "Cloudflare"}),
            REASON_CLOUDFLARE,
        )

    def test_server_header_name_uppercased(self):
        # Header NAMES are also case-insensitive.
        self.assertEqual(
            detect_block_in_headers({"SERVER": "cloudflare"}),
            REASON_CLOUDFLARE,
        )

    def test_cf_mitigated_header(self):
        # cf-mitigated presence is enough — value doesn't matter.
        self.assertEqual(
            detect_block_in_headers({"cf-mitigated": "challenge"}),
            REASON_CLOUDFLARE,
        )

    def test_cf_chl_bypass_header(self):
        self.assertEqual(
            detect_block_in_headers({"cf-chl-bypass": "1"}),
            REASON_CLOUDFLARE,
        )

    def test_server_header_value_must_match(self):
        # Non-matching server value should not trigger a Cloudflare flag.
        self.assertNotEqual(
            detect_block_in_headers({"Server": "nginx"}),
            REASON_CLOUDFLARE,
        )


class HeaderDetectionAkamai(unittest.TestCase):

    def test_server_akamai(self):
        self.assertEqual(
            detect_block_in_headers({"Server": "AkamaiNetStorage"}),
            REASON_AKAMAI,
        )

    def test_akamai_ghost_server_via_ghost_pattern(self):
        self.assertEqual(
            detect_block_in_headers({"Server": "AkamaiGHost"}),
            REASON_AKAMAI,
        )

    def test_x_akamai_transformed_header(self):
        self.assertEqual(
            detect_block_in_headers({"x-akamai-transformed": "9 1234 0"}),
            REASON_AKAMAI,
        )


class HeaderDetectionPerimeterX(unittest.TestCase):

    def test_x_px_block_header(self):
        self.assertEqual(
            detect_block_in_headers({"x-px-block": "1"}),
            REASON_PERIMETERX,
        )

    def test_pxvid_in_set_cookie(self):
        self.assertEqual(
            detect_block_in_headers({
                "Set-Cookie": "_pxvid=abc123; Path=/"
            }),
            REASON_PERIMETERX,
        )

    def test_pxhd_in_set_cookie(self):
        self.assertEqual(
            detect_block_in_headers({
                "Set-Cookie": "_pxhd=xyz; HttpOnly"
            }),
            REASON_PERIMETERX,
        )


class HeaderDetectionDataDome(unittest.TestCase):

    def test_server_datadome(self):
        self.assertEqual(
            detect_block_in_headers({"Server": "DataDome"}),
            REASON_DATADOME,
        )

    def test_x_dd_b_header(self):
        self.assertEqual(
            detect_block_in_headers({"x-dd-b": "anything"}),
            REASON_DATADOME,
        )

    def test_datadome_cookie(self):
        self.assertEqual(
            detect_block_in_headers({
                "Set-Cookie": "datadome=abc; SameSite=Lax"
            }),
            REASON_DATADOME,
        )


class HeaderDetectionEdgeCases(unittest.TestCase):

    def test_none_headers(self):
        self.assertIsNone(detect_block_in_headers(None))

    def test_empty_headers(self):
        self.assertIsNone(detect_block_in_headers({}))

    def test_unrelated_headers(self):
        headers = {
            "Content-Type": "text/html",
            "Server": "nginx",
            "Cache-Control": "no-cache",
        }
        self.assertIsNone(detect_block_in_headers(headers))

    def test_non_mapping_object_returns_none(self):
        # A plain string has no .items() — should fail gracefully.
        self.assertIsNone(detect_block_in_headers("not-a-mapping"))

    def test_multidict_like_with_duplicate_set_cookie(self):
        """Header containers with `.items()` returning duplicates should work."""
        class MultiDictLike:
            def __init__(self, pairs):
                self._pairs = pairs

            def items(self):
                return list(self._pairs)

        headers = MultiDictLike([
            ("Set-Cookie", "session=abc; Path=/"),
            ("Set-Cookie", "datadome=xyz; HttpOnly"),
        ])
        self.assertEqual(detect_block_in_headers(headers), REASON_DATADOME)


# ---------------------------------------------------------------------------
# Body detection
# ---------------------------------------------------------------------------

class BodyDetectionCloudflare(unittest.TestCase):

    def test_attention_required_phrase(self):
        body = b"<html>Attention Required! | Cloudflare</html>"
        self.assertEqual(detect_block_in_body(body), REASON_CLOUDFLARE)

    def test_checking_your_browser(self):
        body = b"Please wait, Checking your browser before accessing..."
        self.assertEqual(detect_block_in_body(body), REASON_CLOUDFLARE)

    def test_cf_browser_verification(self):
        body = b'<form id="challenge-form" class="cf-browser-verification">'
        self.assertEqual(detect_block_in_body(body), REASON_CLOUDFLARE)

    def test_cf_chl_opt_marker(self):
        body = b'window._cf_chl_opt = {chlApiSitekey: "..."};'
        self.assertEqual(detect_block_in_body(body), REASON_CLOUDFLARE)


class BodyDetectionAkamai(unittest.TestCase):

    def test_access_denied_reference_pattern(self):
        body = b"Access Denied. Reference #18.b2dcb17.1234567890.abc"
        self.assertEqual(detect_block_in_body(body), REASON_AKAMAI)

    def test_real_akamai_reference_uppercase_hex(self):
        body = b"Reference #18.DEADBEEF.1716040123.ABC123"
        self.assertEqual(detect_block_in_body(body), REASON_AKAMAI)

    def test_real_akamai_reference_minimum_hex_segment(self):
        # The pattern requires only one hex segment after the initial
        # "#<digits>." — keep this case in if anyone tightens further.
        body = b"Reference #18.a.123.xyz"
        self.assertEqual(detect_block_in_body(body), REASON_AKAMAI)

    # ----- False-positive regressions for the tightened pattern -----
    #
    # The previous pattern was `reference\s*#\d+\.` — it fired on academic
    # prose like "see reference #4." or bibliography entries. The
    # tightened pattern requires a trailing hex-segment-with-dot, which
    # Akamai always includes but ordinary prose never does. These tests
    # guard against any future regression that re-broadens the pattern.

    def test_academic_citation_does_not_match(self):
        body = b"See reference #4. for more details on this topic."
        self.assertIsNone(detect_block_in_body(body))

    def test_bibliography_entry_does_not_match(self):
        body = b"<li>Reference #1. Smith et al. (2020), Journal of X.</li>"
        self.assertIsNone(detect_block_in_body(body))

    def test_prose_with_reference_number_does_not_match(self):
        body = b"reference #12. The previous reference covered methodology."
        self.assertIsNone(detect_block_in_body(body))


class BodyDetectionPerimeterX(unittest.TestCase):

    def test_px_captcha_marker(self):
        body = b'<div id="px-captcha"></div>'
        self.assertEqual(detect_block_in_body(body), REASON_PERIMETERX)

    def test_perimeterx_word(self):
        body = b"<!-- PerimeterX -->"
        self.assertEqual(detect_block_in_body(body), REASON_PERIMETERX)


class BodyDetectionDataDome(unittest.TestCase):

    def test_datadome_word(self):
        body = b'<script src="https://js.datadome.co/..."></script>'
        self.assertEqual(detect_block_in_body(body), REASON_DATADOME)


class BodyDetectionGenericChallenge(unittest.TestCase):

    def test_verify_human(self):
        body = b"Please verify you are a human to continue."
        self.assertEqual(detect_block_in_body(body), REASON_GENERIC_CHALLENGE)

    def test_recaptcha_class(self):
        body = b'<div class="g-recaptcha" data-sitekey="..."></div>'
        self.assertEqual(detect_block_in_body(body), REASON_GENERIC_CHALLENGE)

    def test_hcaptcha_domain(self):
        body = b'<script src="https://hcaptcha.com/1/api.js"></script>'
        self.assertEqual(detect_block_in_body(body), REASON_GENERIC_CHALLENGE)


class BodyDetectionEdgeCases(unittest.TestCase):

    def test_empty_body(self):
        self.assertIsNone(detect_block_in_body(b""))

    def test_none_body(self):
        # None should not raise.
        self.assertIsNone(detect_block_in_body(None))  # type: ignore[arg-type]

    def test_innocent_body_returns_none(self):
        body = (b"<!DOCTYPE html><html><body>"
                b"<h1>Welcome to Example</h1>"
                b"<p>This is a normal page.</p>"
                b"</body></html>")
        self.assertIsNone(detect_block_in_body(body))

    def test_case_insensitive_match(self):
        # Patterns are compiled with re.I; mixed case should still match.
        self.assertEqual(
            detect_block_in_body(b"VERIFY YOU ARE A HUMAN!"),
            REASON_GENERIC_CHALLENGE,
        )


# ---------------------------------------------------------------------------
# Combined detection (detect_block)
# ---------------------------------------------------------------------------

class CombinedDetection(unittest.TestCase):

    def test_returns_headers_source_when_header_matches(self):
        reason, source = detect_block(
            {"Server": "cloudflare"},
            b"<html>normal content</html>",
        )
        self.assertEqual(reason, REASON_CLOUDFLARE)
        self.assertEqual(source, "headers")

    def test_returns_body_source_when_only_body_matches(self):
        reason, source = detect_block(
            {"Server": "nginx"},
            b"Please verify you are a human.",
        )
        self.assertEqual(reason, REASON_GENERIC_CHALLENGE)
        self.assertEqual(source, "body")

    def test_header_match_takes_precedence_over_body(self):
        # If headers and body BOTH match, the header reason wins (cheaper +
        # generally more reliable signal).
        reason, source = detect_block(
            {"Server": "cloudflare"},
            b"verify you are a human",
        )
        self.assertEqual(reason, REASON_CLOUDFLARE)
        self.assertEqual(source, "headers")

    def test_no_signals_returns_none(self):
        reason, source = detect_block({"Server": "nginx"}, b"<html>ok</html>")
        self.assertIsNone(reason)
        self.assertEqual(source, "")

    def test_none_headers_none_body(self):
        reason, source = detect_block(None, b"")
        self.assertIsNone(reason)
        self.assertEqual(source, "")


# ---------------------------------------------------------------------------
# Status-based reasons
# ---------------------------------------------------------------------------

class StatusReasons(unittest.TestCase):

    def test_403(self):
        self.assertEqual(reason_for_status(403), REASON_403)

    def test_429(self):
        self.assertEqual(reason_for_status(429), REASON_429)

    def test_503(self):
        self.assertEqual(reason_for_status(503), REASON_503)

    def test_200_returns_none(self):
        self.assertIsNone(reason_for_status(200))

    def test_404_returns_none(self):
        # 404 is BROKEN, not BLOCKED — no reason string here.
        self.assertIsNone(reason_for_status(404))

    def test_500_returns_none(self):
        self.assertIsNone(reason_for_status(500))


if __name__ == "__main__":
    unittest.main(verbosity=2)
