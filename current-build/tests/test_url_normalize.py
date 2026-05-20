"""Behavioral tests for `urlcheck.url_normalize`.

These tests exercise the public functions as black boxes — input strings
go in, normalized URLs come out. There is intentionally NO inspection of
the module's source text; if the implementation is refactored, these
tests still pass as long as the contract holds.

Run with:
    python -m unittest tests.test_url_normalize -v
"""

from __future__ import annotations

import unittest

from urlcheck.url_normalize import (
    NormalizationOptions,
    _strip_edges,
    extract_urls_from_text,
    normalize_url,
    split_cell_into_tokens,
)


# ---------------------------------------------------------------------------
# _strip_edges
# ---------------------------------------------------------------------------

class StripEdgesPureCases(unittest.TestCase):
    """Whitespace and pure-punctuation peeling."""

    def test_strip_outer_whitespace(self):
        self.assertEqual(_strip_edges("  https://example.com  "),
                         "https://example.com")

    def test_strip_trailing_period(self):
        self.assertEqual(_strip_edges("https://example.com."),
                         "https://example.com")

    def test_strip_trailing_comma_and_semicolon(self):
        self.assertEqual(_strip_edges("https://example.com,"),
                         "https://example.com")
        self.assertEqual(_strip_edges("https://example.com;"),
                         "https://example.com")

    def test_strip_multiple_trailing_punctuation(self):
        self.assertEqual(_strip_edges("https://example.com.,;"),
                         "https://example.com")

    def test_strip_surrounding_quotes(self):
        self.assertEqual(_strip_edges('"https://example.com"'),
                         "https://example.com")
        self.assertEqual(_strip_edges("'https://example.com'"),
                         "https://example.com")
        self.assertEqual(_strip_edges("`https://example.com`"),
                         "https://example.com")

    def test_strip_paren_wrap_with_trailing_period(self):
        self.assertEqual(_strip_edges("(https://example.com)."),
                         "https://example.com")

    def test_strip_bracket_wrap(self):
        self.assertEqual(_strip_edges("[https://example.com]"),
                         "https://example.com")

    def test_strip_brace_wrap(self):
        self.assertEqual(_strip_edges("{https://example.com}"),
                         "https://example.com")

    def test_strip_angle_bracket_wrap(self):
        self.assertEqual(_strip_edges("<https://example.com>"),
                         "https://example.com")

    def test_strip_empty_input(self):
        self.assertEqual(_strip_edges(""), "")
        self.assertEqual(_strip_edges("   "), "")


class StripEdgesPreservesBalancedBrackets(unittest.TestCase):
    """The bracket-balance bug fix — these must NOT lose their inner brackets."""

    def test_wikipedia_paren_url_kept(self):
        url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
        self.assertEqual(_strip_edges(url), url)

    def test_ms_docs_paren_url_kept(self):
        url = ("https://learn.microsoft.com/en-us/dotnet/api/"
               "system.string.format(system.string,system.object)")
        self.assertEqual(_strip_edges(url), url)

    def test_paren_url_with_trailing_period_strips_only_period(self):
        self.assertEqual(
            _strip_edges("https://en.wikipedia.org/wiki/Foo_(bar)."),
            "https://en.wikipedia.org/wiki/Foo_(bar)",
        )

    def test_paren_url_wrapped_in_outer_parens(self):
        # Outer wrap peels, inner paren stays.
        self.assertEqual(
            _strip_edges("(https://x.org/wiki/Foo_(bar))"),
            "https://x.org/wiki/Foo_(bar)",
        )

    def test_paren_url_in_quotes(self):
        self.assertEqual(
            _strip_edges('"https://en.wikipedia.org/wiki/Foo_(bar)"'),
            "https://en.wikipedia.org/wiki/Foo_(bar)",
        )

    def test_url_with_balanced_inner_brackets(self):
        url = "https://example.com/path[index]"
        self.assertEqual(_strip_edges(url), url)


class StripEdgesPeelsOrphanedBrackets(unittest.TestCase):
    """Edge brackets without a partner should still peel."""

    def test_lone_trailing_close_paren(self):
        self.assertEqual(_strip_edges("https://example.com)"),
                         "https://example.com")

    def test_lone_leading_open_paren(self):
        self.assertEqual(_strip_edges("(https://example.com"),
                         "https://example.com")

    def test_mixed_quote_paren_punctuation(self):
        self.assertEqual(_strip_edges('("https://x.com").'),
                         "https://x.com")


# ---------------------------------------------------------------------------
# normalize_url
# ---------------------------------------------------------------------------

class NormalizeAcceptsValidUrls(unittest.TestCase):

    def test_plain_http_url(self):
        self.assertEqual(normalize_url("http://example.com"),
                         "http://example.com")

    def test_plain_https_url(self):
        self.assertEqual(normalize_url("https://example.com"),
                         "https://example.com")

    def test_https_with_path_and_query(self):
        url = "https://example.com/path/to/page?query=foo&other=bar"
        self.assertEqual(normalize_url(url), url)

    def test_paren_in_path_accepted(self):
        url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
        self.assertEqual(normalize_url(url), url)

    def test_trailing_period_is_stripped(self):
        self.assertEqual(normalize_url("https://example.com."),
                         "https://example.com")

    def test_wrapped_in_parens(self):
        self.assertEqual(normalize_url("(https://example.com)"),
                         "https://example.com")


class NormalizePromotesWwwToHttps(unittest.TestCase):

    def test_www_promoted_by_default(self):
        self.assertEqual(normalize_url("www.example.com"),
                         "https://www.example.com")

    def test_www_rejected_when_promotion_disabled(self):
        opts = NormalizationOptions(promote_www_to_https=False)
        self.assertIsNone(normalize_url("www.example.com", opts))


class NormalizeRejectsNonUrlInputs(unittest.TestCase):

    def test_rejects_none(self):
        self.assertIsNone(normalize_url(None))

    def test_rejects_empty(self):
        self.assertIsNone(normalize_url(""))
        self.assertIsNone(normalize_url("   "))

    def test_rejects_sentinel_no_value_tokens(self):
        for token in ("N/A", "n/a", "NA", "none", "null", "TBD", "todo",
                      "-", "—", "–", "#"):
            self.assertIsNone(normalize_url(token),
                              f"should reject {token!r}")

    def test_rejects_internal_anchor(self):
        self.assertIsNone(normalize_url("#section"))

    def test_rejects_mailto(self):
        self.assertIsNone(normalize_url("mailto:foo@example.com"))

    def test_rejects_tel(self):
        self.assertIsNone(normalize_url("tel:+15555551234"))

    def test_rejects_javascript(self):
        self.assertIsNone(normalize_url("javascript:alert(1)"))

    def test_rejects_ftp(self):
        self.assertIsNone(normalize_url("ftp://files.example.com"))

    def test_rejects_file(self):
        self.assertIsNone(normalize_url("file:///etc/passwd"))

    def test_rejects_bare_word(self):
        self.assertIsNone(normalize_url("hello"))

    def test_rejects_bare_domain_by_default(self):
        # auto_https off by default — bare domain text shouldn't become a URL.
        self.assertIsNone(normalize_url("example.com"))


# ---------------------------------------------------------------------------
# Structural validation of malformed hosts
# ---------------------------------------------------------------------------

class NormalizeRejectsMalformedHosts(unittest.TestCase):
    """The validator must reject hosts that are clearly garbage.

    Previously, the validation was a regex that focused on what couldn't
    appear at the START of the host, then permitted anything afterward.
    That let through obvious garbage like `*invalid*.com` and
    `example..com`. The new validator structurally inspects the netloc
    via urlparse and rejects chars that are never legal in a host.
    """

    def test_rejects_empty_host(self):
        # urlparse returns netloc="" for these.
        self.assertIsNone(normalize_url("https://"))
        self.assertIsNone(normalize_url("http://"))

    def test_rejects_host_with_asterisk(self):
        # Reserved-but-invalid in RFC 3986 host syntax.
        self.assertIsNone(normalize_url("https://*invalid*.com"))

    def test_rejects_host_with_angle_brackets(self):
        # Sometimes appears in spreadsheets as a template placeholder
        # like `<your-domain>.com` — not a real URL.
        self.assertIsNone(normalize_url("https://<host>.com"))

    def test_rejects_host_with_curly_braces(self):
        # Template placeholders like {API_HOST}.
        self.assertIsNone(normalize_url("https://{host}.com"))

    def test_rejects_host_with_backslash(self):
        self.assertIsNone(normalize_url("https://bad\\host.com"))

    def test_rejects_host_with_pipe(self):
        self.assertIsNone(normalize_url("https://a|b.com"))

    def test_rejects_host_with_only_punctuation(self):
        # Host with no alphanumeric content — degenerate.
        self.assertIsNone(normalize_url("https://..."))
        self.assertIsNone(normalize_url("https://:::"))

    def test_rejects_host_with_embedded_control_char(self):
        # \n in particular can sneak in via copy-paste from a multi-line
        # cell. The HTTP engine would otherwise try to send it raw and
        # break in ugly ways.
        self.assertIsNone(normalize_url("https://example.com\x00evil"))
        self.assertIsNone(normalize_url("https://example\x01.com"))


# ---------------------------------------------------------------------------
# Structural validation accepts legitimate-but-uncommon hosts
# ---------------------------------------------------------------------------

class NormalizeAcceptsUnusualButValidHosts(unittest.TestCase):
    """The validator must NOT reject hosts just because they look unusual.

    Dropping a legitimate URL is worse than including a borderline one:
    the user has no way to know their data was filtered, whereas a
    borderline URL just produces one extra row in the report that they
    can ignore.
    """

    def test_accepts_localhost(self):
        # Intranet / development URLs are common in vendor lists.
        self.assertEqual(normalize_url("http://localhost"),
                         "http://localhost")
        self.assertEqual(normalize_url("http://localhost:8080"),
                         "http://localhost:8080")

    def test_accepts_ipv4_address(self):
        self.assertEqual(normalize_url("http://192.168.1.1"),
                         "http://192.168.1.1")

    def test_accepts_ipv6_address(self):
        self.assertEqual(normalize_url("http://[::1]"),
                         "http://[::1]")

    def test_accepts_idn_punycode(self):
        # International domain names encoded as ASCII via punycode (RFC 3492).
        url = "https://xn--bcher-kva.example/path"
        self.assertEqual(normalize_url(url), url)

    def test_accepts_userinfo(self):
        # Uncommon in spreadsheets but RFC-valid.
        url = "http://user:pass@example.com/"
        self.assertEqual(normalize_url(url), url)

    def test_accepts_trailing_dot_fqdn(self):
        # Trailing dot signals an absolute FQDN — valid, sometimes used.
        # _strip_edges peels the trailing dot before validation, so the
        # effective input to the validator is "https://example.com".
        self.assertEqual(normalize_url("https://example.com."),
                         "https://example.com")

    def test_accepts_unusual_but_valid_port(self):
        self.assertEqual(normalize_url("http://example.com:8443"),
                         "http://example.com:8443")

    def test_accepts_typo_hosts_by_design(self):
        """Borderline-malformed hosts are accepted, not rejected.

        `example..com` (double-dot) and `-bad.com` (leading hyphen) are
        technically invalid per RFC 952/1123 hostname rules. We
        deliberately let them through because:
          1. The HTTP engine will fail them with DNS errors anyway,
             producing a clearly-labeled BROKEN row in the report.
          2. Silently dropping a typo from the report is worse than
             showing it as broken — the user can't tell their data was
             filtered.
          3. The shapes that absolutely won't appear in real spreadsheets
             (control chars, `*`, `<>`, etc.) are still rejected above.

        If a future change tightens this, update the test name to match
        the new policy — don't just delete this test.
        """
        # Accepts deliberately.
        self.assertEqual(normalize_url("https://example..com"),
                         "https://example..com")
        self.assertEqual(normalize_url("https://-bad.com"),
                         "https://-bad.com")


class NormalizeAutoHttpsForBareDomains(unittest.TestCase):
    """When opted in, bare domain-like tokens should be promoted."""

    def setUp(self):
        self.opts = NormalizationOptions(auto_https_for_bare_domains=True)

    def test_bare_domain_promoted(self):
        self.assertEqual(normalize_url("example.com", self.opts),
                         "https://example.com")

    def test_bare_domain_with_path_promoted(self):
        self.assertEqual(normalize_url("example.com/path", self.opts),
                         "https://example.com/path")

    def test_invalid_tld_rejected(self):
        # Single-letter "TLD" — not a real domain.
        self.assertIsNone(normalize_url("example.x", self.opts))

    def test_no_dot_rejected(self):
        self.assertIsNone(normalize_url("localhost", self.opts))

    def test_dot_start_rejected(self):
        self.assertIsNone(normalize_url(".example.com", self.opts))


# ---------------------------------------------------------------------------
# split_cell_into_tokens
# ---------------------------------------------------------------------------

class SplitTokens(unittest.TestCase):

    def test_single_url_returned_as_one_token(self):
        self.assertEqual(split_cell_into_tokens("https://example.com"),
                         ["https://example.com"])

    def test_two_urls_separated_by_space(self):
        tokens = split_cell_into_tokens("https://a.com https://b.com")
        self.assertEqual(tokens, ["https://a.com", "https://b.com"])

    def test_two_urls_separated_by_comma(self):
        tokens = split_cell_into_tokens("https://a.com, https://b.com")
        self.assertEqual(tokens, ["https://a.com", "https://b.com"])

    def test_two_urls_separated_by_semicolon(self):
        tokens = split_cell_into_tokens("https://a.com; https://b.com")
        self.assertEqual(tokens, ["https://a.com", "https://b.com"])

    def test_url_embedded_in_prose(self):
        tokens = split_cell_into_tokens("See https://example.com for info.")
        # Trailing period stays on the token; normalize_url peels it.
        self.assertEqual(len(tokens), 1)
        self.assertTrue(tokens[0].startswith("https://example.com"))

    def test_www_token_extracted(self):
        tokens = split_cell_into_tokens("visit www.example.com today")
        self.assertEqual(tokens, ["www.example.com"])

    def test_separator_fallback_with_bare_domains(self):
        # No http/www anchor → Pass 2 separator-split.
        tokens = split_cell_into_tokens("a.com; b.com, c.com")
        self.assertEqual(tokens, ["a.com", "b.com", "c.com"])

    def test_none_returns_empty(self):
        self.assertEqual(split_cell_into_tokens(None), [])

    def test_empty_returns_empty(self):
        self.assertEqual(split_cell_into_tokens(""), [])
        self.assertEqual(split_cell_into_tokens("   "), [])

    def test_paren_in_url_kept_during_split(self):
        # Confirms split doesn't truncate at "(" — the embedded URL stays whole.
        tokens = split_cell_into_tokens(
            "see https://en.wikipedia.org/wiki/Foo_(bar) and "
            "https://en.wikipedia.org/wiki/Baz."
        )
        self.assertEqual(len(tokens), 2)
        self.assertIn("Foo_(bar)", tokens[0])


# ---------------------------------------------------------------------------
# extract_urls_from_text (end-to-end)
# ---------------------------------------------------------------------------

class ExtractUrlsFromText(unittest.TestCase):

    def test_single_url(self):
        self.assertEqual(
            extract_urls_from_text("https://example.com"),
            ["https://example.com"],
        )

    def test_multiple_urls_comma_separated(self):
        self.assertEqual(
            extract_urls_from_text("https://a.com, https://b.com"),
            ["https://a.com", "https://b.com"],
        )

    def test_url_in_prose_with_trailing_period(self):
        self.assertEqual(
            extract_urls_from_text("Visit https://example.com. Thanks!"),
            ["https://example.com"],
        )

    def test_paren_url_in_prose_preserved(self):
        self.assertEqual(
            extract_urls_from_text(
                "See https://en.wikipedia.org/wiki/Python_(programming_language) for info."
            ),
            ["https://en.wikipedia.org/wiki/Python_(programming_language)"],
        )

    def test_www_promoted_to_https(self):
        self.assertEqual(
            extract_urls_from_text("www.example.com"),
            ["https://www.example.com"],
        )

    def test_no_urls_returns_empty(self):
        self.assertEqual(extract_urls_from_text("just some plain text"), [])

    def test_only_rejects_returns_empty(self):
        self.assertEqual(extract_urls_from_text("N/A"), [])
        self.assertEqual(extract_urls_from_text("mailto:foo@x.com"), [])

    def test_order_preserved(self):
        urls = extract_urls_from_text("https://c.com; https://a.com; https://b.com")
        self.assertEqual(urls, ["https://c.com", "https://a.com", "https://b.com"])

    def test_mixed_valid_and_invalid_tokens(self):
        # Only the valid URL should come through.
        urls = extract_urls_from_text("contact: mailto:x@y.com or https://example.com")
        self.assertEqual(urls, ["https://example.com"])

    def test_none_input(self):
        self.assertEqual(extract_urls_from_text(None), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
