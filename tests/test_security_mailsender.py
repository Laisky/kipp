#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from unittest import TestCase
from kipp.utils import EmailSender

class SecurityEmailSenderTestCase(TestCase):
    def setUp(self):
        self.sender = EmailSender("fake_host")

    def test_parse_content_injection(self):
        malicious_content = "Safe content</p><script>alert('XSS')</script><p>"
        result = self.sender.parse_content(malicious_content)
        # Check that the script tag is NOT present in its raw form
        self.assertNotIn("<script>alert('XSS')</script>", result)
        # Check that it IS present in its escaped form
        self.assertIn("&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;", result.replace("'", "&#x27;"))

    def test_generate_table_injection(self):
        heads = ("head1", "head2<script>alert('XSS')</script>")
        contents = [("cell1", "cell2<img src=x onerror=alert(1)>")]
        result = self.sender.generate_table(heads, contents)
        self.assertNotIn("<script>alert('XSS')</script>", result)
        self.assertNotIn("<img src=x onerror=alert(1)>", result)
        self.assertIn("&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;", result.replace("'", "&#x27;"))
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", result)

if __name__ == '__main__':
    import unittest
    unittest.main()
