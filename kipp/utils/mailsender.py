#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
------------
Email Sender
------------

Sends HTML-formatted emails via SMTP with optional TLS and authentication.

Usage::

    from kipp.utils import EmailSender

    sender = EmailSender(host="smtp.example.com")
    receivers = ','.join(["alice@example.com", "bob@example.com"])

    sender.send_email(
        mail_from='noreply@example.com',
        mail_to=receivers,
        subject='Email Title',
        content='Email content'
    )

"""

from __future__ import annotations

import html
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from textwrap import dedent
from typing import Iterable

from .logger import get_logger as get_kipp_logger


HOST: str = "smtp.internal.ng.movoto.net"
FROM_ADDRESS: str = "mls-normalizer-ng@movoto.com"


class EmailSender:
    """SMTP email sender that wraps content in a consistent HTML template.

    Supports both plain-text content (auto-wrapped in HTML paragraphs with
    escaped characters) and raw HTML body injection.
    """

    def __init__(
        self,
        host: str = HOST,
        port: int | None = None,
        username: str | None = None,
        passwd: str | None = None,
        logger: logging.Logger | None = None,
        use_tls: bool = True,
    ) -> None:
        """Initialize EmailSender.

        Args:
            host: SMTP server hostname.
            port: SMTP server port. None lets smtplib use its default (25).
            username: SMTP auth username. Skipped if None.
            passwd: SMTP auth password. Skipped if None.
            logger: Logger instance; falls back to kipp's internal logger.
            use_tls: Whether to upgrade the connection with STARTTLS.
        """
        self._host = host
        self._port = port
        self._user = username
        self._passwd = passwd
        self._logger = logger
        self._use_tls = use_tls

    def set_smtp_host(self, host: str) -> None:
        """Replace the SMTP server hostname after construction."""
        if not host or not isinstance(host, str):
            raise ValueError("SMTP host must be a non-empty string, got {!r}".format(host))
        self._host = host

    def set_smtp_port(self, port: int) -> None:
        """Replace the SMTP server port after construction."""
        if not isinstance(port, int) or port <= 0:
            raise ValueError("SMTP port must be a positive integer, got {!r}".format(port))
        self._port = port

    def get_logger(self) -> logging.Logger:
        return self._logger or get_kipp_logger().getChild("email")

    # def setup_by_utilities(self):
    #     try:
    #         from Utilities.movoto import settings
    #     except ImportError:
    #         return

    #     self._host = settings.HOST
    #     self._mail_from = settings.FROM_ADDRESS

    def parse_content(self, content: str) -> str:
        """Convert plain text to HTML paragraphs with escaped special characters.

        Each line becomes a ``<p>`` element so line breaks are preserved
        in email clients that strip whitespace.
        """
        escaped_lines = [html.escape(line) for line in content.splitlines()]
        return '<font face="Microsoft YaHei, Helvetica Neue, Helvetica">{}</font>'.format(
            "<p>{}</p>".format("</p><p>".join(escaped_lines))
        )

    def get_html(self, body: str) -> str:
        """Wrap an HTML body fragment in a full HTML document with base styles."""
        return """
            <head>
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
            <title>html title</title>
            <style type="text/css" media="screen">
                table{{
                    background-color: #f9f9f9;
                    empty-cells: hide;
                }}
            </style>
            </head>
            <body>
                {body}
            </body>
            """.format(
            body=body
        )

    def _filter_mail_to(self, mail_to: str) -> str:
        """Deduplicate comma-separated recipient addresses for the To header."""
        return ",".join(set(mail_to.split(",")))

    def send_email(
        self,
        mail_to: str,
        subject: str,
        content: str | None = None,
        html: str | None = None,
        mail_from: str = FROM_ADDRESS,
    ) -> bool:
        """Send an email, returning True on success and False on failure.

        Both ``content`` (plain text auto-converted to HTML) and ``html``
        (raw HTML body) can be provided; they are attached as separate
        MIME alternatives so the mail client picks the best one.

        Args:
            mail_to: Comma-separated recipient addresses.
            subject: Email subject line.
            content: Plain text content (will be HTML-escaped and wrapped).
            html: Raw HTML body fragment (will be wrapped in a document template).
            mail_from: Sender address.

        Returns:
            True if the email was sent successfully, False otherwise.
        """
        msg = MIMEMultipart("alternative")
        msg.set_charset("utf-8")
        if content:
            msg.attach(MIMEText(self.parse_content(content), "html"))

        if html:
            msg.attach(MIMEText(self.get_html(html), "html"))

        msg["Subject"] = subject
        msg["From"] = mail_from
        msg["To"] = self._filter_mail_to(mail_to)

        try:
            s = smtplib.SMTP(self._host, self._port)
            if self._use_tls:
                s.starttls()

            if self._user and self._passwd:
                s.login(self._user, self._passwd)

            s.sendmail(mail_from, mail_to.split(","), msg.as_string())
            s.quit()
            self.get_logger().info(
                "send email successfully to {} with subject {}".format(mail_to, subject)
            )
            return True
        except Exception:
            self.get_logger().exception(
                "fail to send email to {} with subject {} for error:".format(
                    mail_to, subject
                )
            )
            return False

    def generate_table(
        self,
        heads: Iterable[object],
        contents: Iterable[Iterable[object]],
    ) -> str:
        """Build an HTML table string suitable for embedding in an email body.

        All cell values are HTML-escaped to prevent injection. The table
        uses fixed layout for consistent column widths across mail clients.

        Args:
            heads: Column header values (converted to str).
            contents: Rows of cell values (each row is an iterable of values).

        Returns:
            An HTML ``<table>`` string ready to pass to ``send_email(html=...)``.

        Examples::

            heads = ('head 1', 'head 2', 'head 3')
            contents = (
                ('cell 1-1', 'cell 1-2', 'cell 1-3'),
                ('cell 2-1', 'cell 2-2', 'cell 2-3')
            )

            table_html = sender.generate_table(heads, contents)
        """
        thead = "".join(["<th><p>{}</p></th>\n".format(html.escape(str(h))) for h in heads])
        tbody = ""
        for cnt in contents:
            tbody += "<tr>{}</tr>\n".format(
                "".join(["<td><p>{}</p></td>".format(html.escape(str(h))) for h in cnt])
            )

        return dedent(
            """
            <table style="table-layout:fixed;" cellspacing="0" cellpadding="10">
                <thead><tr>{thead}</tr></thead>
                <tbody>{tbody}</tbody>
            </table>
            """
        ).format(thead=thead, tbody=tbody)


if __name__ == "__main__":
    sender = EmailSender()
    assert sender.send_email(
        mail_to="lcai@movoto.com,lcai@movoto.com",
        subject="test: kipp.utils.EmailSender",
        content="fake-content\n\nline 2",
        mail_from="kipp@movoto.com",
    )
