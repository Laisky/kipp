#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock, patch

from kipp.utils.mailsender import EmailSender, FROM_ADDRESS, HOST


class ParseContentTestCase(TestCase):
    """Tests for EmailSender.parse_content."""

    def setUp(self):
        self.sender = EmailSender("localhost")

    def test_escapes_ampersand(self):
        result = self.sender.parse_content("A & B")
        self.assertIn("A &amp; B", result)

    def test_escapes_less_than(self):
        result = self.sender.parse_content("a < b")
        self.assertIn("a &lt; b", result)

    def test_escapes_greater_than(self):
        result = self.sender.parse_content("a > b")
        self.assertIn("a &gt; b", result)

    def test_escapes_double_quotes(self):
        result = self.sender.parse_content('say "hello"')
        self.assertIn("say &quot;hello&quot;", result)

    def test_escapes_single_quotes(self):
        result = self.sender.parse_content("it's")
        self.assertIn("it&#x27;s", result)

    def test_escapes_all_special_chars_combined(self):
        result = self.sender.parse_content('<a href="x">&\'test\'</a>')
        self.assertNotIn("<a", result)
        self.assertIn("&amp;", result)
        self.assertIn("&lt;", result)
        self.assertIn("&gt;", result)
        self.assertIn("&quot;", result)
        self.assertIn("&#x27;", result)

    def test_multiline_content_wraps_each_line_in_p(self):
        result = self.sender.parse_content("line1\nline2\nline3")
        self.assertIn("<p>line1</p>", result)
        self.assertIn("<p>line2</p>", result)
        self.assertIn("<p>line3</p>", result)

    def test_multiline_structure(self):
        result = self.sender.parse_content("a\nb")
        self.assertIn("<p>a</p><p>b</p>", result)

    def test_wraps_in_font_tag(self):
        result = self.sender.parse_content("text")
        self.assertTrue(result.startswith('<font face="Microsoft YaHei'))
        self.assertTrue(result.endswith("</font>"))

    def test_empty_content(self):
        result = self.sender.parse_content("")
        self.assertIn("<p>", result)
        self.assertIn("</p>", result)
        self.assertIn("<font", result)

    def test_single_line_no_newline(self):
        result = self.sender.parse_content("single line")
        self.assertIn("<p>single line</p>", result)
        self.assertEqual(result.count("<p>"), 1)

    def test_preserves_whitespace_within_lines(self):
        result = self.sender.parse_content("  hello  world  ")
        self.assertIn("  hello  world  ", result)

    def test_blank_lines_produce_empty_paragraphs(self):
        result = self.sender.parse_content("a\n\nb")
        self.assertIn("<p></p>", result)


class GenerateTableTestCase(TestCase):
    """Tests for EmailSender.generate_table."""

    def setUp(self):
        self.sender = EmailSender("localhost")

    def test_produces_valid_html_table(self):
        heads = ("H1", "H2")
        contents = (("A", "B"),)
        result = self.sender.generate_table(heads, contents)
        self.assertIn("<table", result)
        self.assertIn("</table>", result)
        self.assertIn("<thead>", result)
        self.assertIn("</thead>", result)
        self.assertIn("<tbody>", result)
        self.assertIn("</tbody>", result)

    def test_table_layout_fixed(self):
        result = self.sender.generate_table(("H",), ())
        self.assertIn('table-layout:fixed', result)

    def test_headers_present(self):
        heads = ("Name", "Age")
        contents = ()
        result = self.sender.generate_table(heads, contents)
        self.assertIn("<th><p>Name</p></th>", result)
        self.assertIn("<th><p>Age</p></th>", result)

    def test_cells_present(self):
        heads = ("X",)
        contents = (("val1",), ("val2",))
        result = self.sender.generate_table(heads, contents)
        self.assertIn("<td><p>val1</p></td>", result)
        self.assertIn("<td><p>val2</p></td>", result)

    def test_escapes_special_chars_in_headers(self):
        heads = ("<script>",)
        contents = ()
        result = self.sender.generate_table(heads, contents)
        self.assertIn("&lt;script&gt;", result)
        self.assertNotIn("<script>", result)

    def test_escapes_special_chars_in_cells(self):
        heads = ("H",)
        contents = (("a & b",),)
        result = self.sender.generate_table(heads, contents)
        self.assertIn("a &amp; b", result)

    def test_escapes_quotes_in_cells(self):
        heads = ("H",)
        contents = (('say "hi"',),)
        result = self.sender.generate_table(heads, contents)
        self.assertIn("say &quot;hi&quot;", result)

    def test_empty_contents(self):
        heads = ("H1",)
        contents = ()
        result = self.sender.generate_table(heads, contents)
        self.assertIn("<tbody>", result)
        self.assertIn("</tbody>", result)

    def test_multiple_rows_and_columns(self):
        heads = ("A", "B", "C")
        contents = (("1", "2", "3"), ("4", "5", "6"))
        result = self.sender.generate_table(heads, contents)
        self.assertIn("<td><p>1</p></td>", result)
        self.assertIn("<td><p>6</p></td>", result)
        # 1 header <tr> + 2 body <tr>
        self.assertEqual(result.count("<tr>"), 3)

    def test_non_string_values_converted(self):
        heads = (1, 2)
        contents = ((3.14, True),)
        result = self.sender.generate_table(heads, contents)
        self.assertIn("<th><p>1</p></th>", result)
        self.assertIn("<th><p>2</p></th>", result)
        self.assertIn("<td><p>3.14</p></td>", result)
        self.assertIn("<td><p>True</p></td>", result)

    def test_single_cell_table(self):
        result = self.sender.generate_table(("H",), (("V",),))
        self.assertIn("<th><p>H</p></th>", result)
        self.assertIn("<td><p>V</p></td>", result)


class SendEmailTestCase(TestCase):
    """Tests for EmailSender.send_email."""

    def setUp(self):
        self.sender = EmailSender("smtp.test.com", port=587)

    def _make_mock_smtp(self):
        mock_instance = MagicMock()
        patcher = patch("kipp.utils.mailsender.smtplib.SMTP", return_value=mock_instance)
        mock_cls = patcher.start()
        self.addCleanup(patcher.stop)
        return mock_cls, mock_instance

    def test_send_email_returns_true_on_success(self):
        mock_cls, mock_inst = self._make_mock_smtp()
        result = self.sender.send_email(
            mail_to="user@test.com",
            subject="Test Subject",
            content="Test body",
            mail_from="sender@test.com",
        )
        self.assertTrue(result)

    def test_send_email_connects_with_correct_host_port(self):
        mock_cls, mock_inst = self._make_mock_smtp()
        self.sender.send_email(
            mail_to="user@test.com", subject="sub", content="body"
        )
        mock_cls.assert_called_once_with("smtp.test.com", 587)

    def test_send_email_calls_sendmail_with_correct_args(self):
        mock_cls, mock_inst = self._make_mock_smtp()
        self.sender.send_email(
            mail_to="user@test.com",
            subject="sub",
            content="body",
            mail_from="sender@test.com",
        )
        args = mock_inst.sendmail.call_args[0]
        self.assertEqual(args[0], "sender@test.com")
        self.assertEqual(args[1], ["user@test.com"])

    def test_send_email_calls_quit(self):
        mock_cls, mock_inst = self._make_mock_smtp()
        self.sender.send_email(mail_to="to@x.com", subject="sub", content="body")
        mock_inst.quit.assert_called_once()

    def test_send_email_tls_enabled(self):
        sender = EmailSender("smtp.test.com", use_tls=True)
        mock_cls, mock_inst = self._make_mock_smtp()
        sender.send_email("to@x.com", "sub", content="body")
        mock_inst.starttls.assert_called_once()

    def test_send_email_tls_disabled(self):
        sender = EmailSender("smtp.test.com", use_tls=False)
        mock_cls, mock_inst = self._make_mock_smtp()
        sender.send_email("to@x.com", "sub", content="body")
        mock_inst.starttls.assert_not_called()

    def test_send_email_with_authentication(self):
        sender = EmailSender("smtp.test.com", username="user", passwd="pass")
        mock_cls, mock_inst = self._make_mock_smtp()
        sender.send_email("to@x.com", "sub", content="body")
        mock_inst.login.assert_called_once_with("user", "pass")

    def test_send_email_no_authentication_when_no_user(self):
        sender = EmailSender("smtp.test.com", username=None, passwd=None)
        mock_cls, mock_inst = self._make_mock_smtp()
        sender.send_email("to@x.com", "sub", content="body")
        mock_inst.login.assert_not_called()

    def test_send_email_no_authentication_when_only_user(self):
        sender = EmailSender("smtp.test.com", username="user", passwd=None)
        mock_cls, mock_inst = self._make_mock_smtp()
        sender.send_email("to@x.com", "sub", content="body")
        mock_inst.login.assert_not_called()

    def test_send_email_returns_false_on_smtp_error(self):
        with patch("kipp.utils.mailsender.smtplib.SMTP") as MockSMTP:
            MockSMTP.side_effect = Exception("Connection refused")
            result = self.sender.send_email("to@x.com", "sub", content="body")
        self.assertFalse(result)

    def test_send_email_returns_false_on_sendmail_error(self):
        mock_cls, mock_inst = self._make_mock_smtp()
        mock_inst.sendmail.side_effect = Exception("rejected")
        result = self.sender.send_email("to@x.com", "sub", content="body")
        self.assertFalse(result)

    def test_send_email_multiple_recipients(self):
        mock_cls, mock_inst = self._make_mock_smtp()
        self.sender.send_email(
            mail_to="a@x.com,b@x.com", subject="sub", content="body"
        )
        args = mock_inst.sendmail.call_args[0]
        self.assertEqual(args[1], ["a@x.com", "b@x.com"])

    def test_send_email_with_html_only(self):
        mock_cls, mock_inst = self._make_mock_smtp()
        result = self.sender.send_email(
            mail_to="to@x.com", subject="sub", html="<b>Bold</b>"
        )
        self.assertTrue(result)
        mock_inst.sendmail.assert_called_once()

    def test_send_email_with_content_only(self):
        mock_cls, mock_inst = self._make_mock_smtp()
        result = self.sender.send_email(
            mail_to="to@x.com", subject="sub", content="plain text"
        )
        self.assertTrue(result)
        mock_inst.sendmail.assert_called_once()

    def test_send_email_with_both_content_and_html(self):
        mock_cls, mock_inst = self._make_mock_smtp()
        result = self.sender.send_email(
            mail_to="to@x.com",
            subject="sub",
            content="plain text",
            html="<b>html</b>",
        )
        self.assertTrue(result)

    def test_send_email_uses_default_mail_from(self):
        mock_cls, mock_inst = self._make_mock_smtp()
        self.sender.send_email(mail_to="to@x.com", subject="sub", content="body")
        args = mock_inst.sendmail.call_args[0]
        self.assertEqual(args[0], FROM_ADDRESS)

    def test_send_email_message_contains_subject(self):
        mock_cls, mock_inst = self._make_mock_smtp()
        self.sender.send_email(
            mail_to="to@x.com", subject="Important Subject", content="body"
        )
        raw_msg = mock_inst.sendmail.call_args[0][2]
        self.assertIn("Important Subject", raw_msg)

    def test_send_email_deduplicates_to_header(self):
        mock_cls, mock_inst = self._make_mock_smtp()
        self.sender.send_email(
            mail_to="a@x.com,a@x.com", subject="sub", content="body"
        )
        raw_msg = mock_inst.sendmail.call_args[0][2]
        # The To header should have deduplicated recipients
        self.assertIn("a@x.com", raw_msg)


class FilterMailToTestCase(TestCase):
    """Tests for EmailSender._filter_mail_to."""

    def setUp(self):
        self.sender = EmailSender("localhost")

    def test_deduplicates_recipients(self):
        result = self.sender._filter_mail_to("a@x.com,a@x.com,b@x.com")
        recipients = set(result.split(","))
        self.assertEqual(recipients, {"a@x.com", "b@x.com"})

    def test_single_recipient(self):
        result = self.sender._filter_mail_to("a@x.com")
        self.assertEqual(result, "a@x.com")

    def test_multiple_unique_recipients(self):
        result = self.sender._filter_mail_to("a@x.com,b@x.com,c@x.com")
        recipients = set(result.split(","))
        self.assertEqual(recipients, {"a@x.com", "b@x.com", "c@x.com"})

    def test_all_duplicates_collapsed_to_one(self):
        result = self.sender._filter_mail_to("a@x.com,a@x.com,a@x.com")
        self.assertEqual(result, "a@x.com")


class EmailSenderInitTestCase(TestCase):
    """Tests for EmailSender initialization."""

    def test_default_values(self):
        sender = EmailSender()
        self.assertEqual(sender._host, HOST)
        self.assertIsNone(sender._port)
        self.assertIsNone(sender._user)
        self.assertIsNone(sender._passwd)
        self.assertIsNone(sender._logger)
        self.assertTrue(sender._use_tls)

    def test_custom_values(self):
        sender = EmailSender(
            host="custom.smtp",
            port=465,
            username="myuser",
            passwd="mypass",
            use_tls=False,
        )
        self.assertEqual(sender._host, "custom.smtp")
        self.assertEqual(sender._port, 465)
        self.assertEqual(sender._user, "myuser")
        self.assertEqual(sender._passwd, "mypass")
        self.assertFalse(sender._use_tls)

    def test_custom_logger(self):
        import logging
        logger = logging.getLogger("test")
        sender = EmailSender(logger=logger)
        self.assertIs(sender._logger, logger)


class SetSmtpHostTestCase(TestCase):
    """Tests for EmailSender.set_smtp_host."""

    def setUp(self):
        self.sender = EmailSender()

    def test_set_valid_host(self):
        self.sender.set_smtp_host("new.host.com")
        self.assertEqual(self.sender._host, "new.host.com")

    def test_set_empty_host_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.sender.set_smtp_host("")

    def test_set_none_host_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.sender.set_smtp_host(None)

    def test_set_non_string_host_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.sender.set_smtp_host(123)


class SetSmtpPortTestCase(TestCase):
    """Tests for EmailSender.set_smtp_port."""

    def setUp(self):
        self.sender = EmailSender()

    def test_set_valid_port(self):
        self.sender.set_smtp_port(587)
        self.assertEqual(self.sender._port, 587)

    def test_set_port_25(self):
        self.sender.set_smtp_port(25)
        self.assertEqual(self.sender._port, 25)

    def test_set_zero_port_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.sender.set_smtp_port(0)

    def test_set_negative_port_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.sender.set_smtp_port(-1)

    def test_set_non_int_port_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.sender.set_smtp_port("587")

    def test_set_float_port_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.sender.set_smtp_port(587.0)


class GetHtmlTestCase(TestCase):
    """Tests for EmailSender.get_html."""

    def setUp(self):
        self.sender = EmailSender("localhost")

    def test_wraps_body_in_html_document(self):
        result = self.sender.get_html("<p>Hello</p>")
        self.assertIn("<head>", result)
        self.assertIn("<body>", result)
        self.assertIn("</body>", result)
        self.assertIn("<p>Hello</p>", result)

    def test_includes_charset_meta(self):
        result = self.sender.get_html("")
        self.assertIn("charset=utf-8", result)

    def test_includes_table_style(self):
        result = self.sender.get_html("")
        self.assertIn("background-color: #f9f9f9", result)


class GetLoggerTestCase(TestCase):
    """Tests for EmailSender.get_logger."""

    def test_returns_custom_logger_when_set(self):
        import logging
        logger = logging.getLogger("custom")
        sender = EmailSender(logger=logger)
        self.assertIs(sender.get_logger(), logger)

    def test_returns_fallback_logger_when_none(self):
        import logging
        sender = EmailSender()
        result = sender.get_logger()
        self.assertIsInstance(result, logging.Logger)
