#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from unittest import TestCase
from textwrap import dedent

from mock import patch, MagicMock

from kipp.utils import EmailSender


class EmailSenderTestCase(TestCase):
    def setUp(self):
        self.sender = EmailSender("fake_smtp_server_host", "fake_smtp_server_port")

    def test_email_sender(self):
        self.assertEqual(self.sender._host, "fake_smtp_server_host")
        self.assertEqual(self.sender._port, "fake_smtp_server_port")

        with patch("smtplib.SMTP") as m:
            sendmail_mock = MagicMock()
            m().sendmail = sendmail_mock
            self.sender.send_email(
                "fake_receiver",
                "fake_subject",
                "fake_content",
                mail_from="fake_from_address",
            )
            self.assertEqual(len(sendmail_mock.call_args_list), 1)
            args = sendmail_mock.call_args_list[0][0]
            self.assertEqual(args[0], "fake_from_address")
            self.assertEqual(args[1], ["fake_receiver"])

    def test_table(self):
        heads = ("head 1", "head 2", "head 3")
        contents = (
            ("cell 1-1", "cell 1-2", "cell 1-3"),
            ("cell 2-1", "cell 2-2", "cell 2-3"),
        )
        expect = dedent(
            """
            <table style="table-layout:fixed;" cellspacing="0" cellpadding="10">
                <thead><tr><th><p>head 1</p></th>
            <th><p>head 2</p></th>
            <th><p>head 3</p></th>
            </tr></thead>
                <tbody><tr><td><p>cell 1-1</p></td><td><p>cell 1-2</p></td><td><p>cell 1-3</p></td></tr>
            <tr><td><p>cell 2-1</p></td><td><p>cell 2-2</p></td><td><p>cell 2-3</p></td></tr>
            </tbody>
            </table>
            """
        )
        r = self.sender.generate_table(heads, contents)
        self.assertEqual(r, expect)
