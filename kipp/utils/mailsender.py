#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
------------
Email Sender
------------

Usage
::
    from kipp.utils import EmailSender

    sender = EmailSender(opt.SMTP_HOST)  # SMTP_HOST is different between NOVA and PRD
    receivers = ','.join([xxx, xxx, xxx])

    sender.send_email(
        mail_from='data@movoto.com',
        mail_to=receivers,
        subject='Email Title',
        content='Email content'
    )

"""


from __future__ import unicode_literals
import smtplib
from textwrap import dedent
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .logger import get_logger as get_kipp_logger


HOST = 'smtp.internal.ng.movoto.net'
FROM_ADDRESS = 'mls-normalizer-ng@movoto.com'


class EmailSender(object):
    def __init__(self, host=HOST, port=None, username=None, passwd=None, logger=None, use_tls=True):
        """Initiallize EmailSender

        Args:
            host (str, default movoto): SMTP server host
            port (int, default=None): SMTP server port
            logger (logging.logger, default=kipp_internal_logger):
            use_tls (bool, default=True)
        """
        self._host = host
        self._port = port
        self._user = username
        self._passwd = passwd
        self._logger = logger
        self._use_tls = use_tls

    def set_smtp_host(self, host):
        assert host, 'smtp host should not be empty'
        assert isinstance(host, str), 'smtp host should be string'
        self._host = host

    def set_smtp_port(self, port):
        assert port, 'smtp port should not be empty'
        assert isinstance(port, int), 'smtp port should be string'
        self._port = port

    def get_logger(self):
        return self._logger or get_kipp_logger().getChild('email')

    # def setup_by_utilities(self):
    #     try:
    #         from Utilities.movoto import settings
    #     except ImportError:
    #         return

    #     self._host = settings.HOST
    #     self._mail_from = settings.FROM_ADDRESS

    def parse_content(self, content):
        return '<font face="Microsoft YaHei, Helvetica Neue, Helvetica">{}</font>'.format(
            '<p>{}</p>'.format('</p><p>'.join(content.splitlines()))
        )

    def get_html(self, body):
        return '''
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
            '''.format(body=body)

    def _filter_mail_to(self, mail_to):
        return ','.join(set(mail_to.split(',')))

    def send_email(self, mail_to, subject, content=None, html=None, mail_from=FROM_ADDRESS):
        """Send email

        Args:
            mail_from (str, default to Utilities' setting): address that send from
            mail_to (str): address that send to, use `,` to split multiply receivers
            subject (str):
            content (str):

        Returns:
            bool: is successed
        """
        msg = MIMEMultipart('alternative')
        msg.set_charset("utf-8")
        if content:
            msg.attach(MIMEText(self.parse_content(content), 'html'))

        if html:
            msg.attach(MIMEText(self.get_html(html), 'html'))

        msg['Subject'] = subject
        msg['From'] = mail_from
        msg['To'] = self._filter_mail_to(mail_to)

        try:
            s = smtplib.SMTP(self._host, self._port)
            if self._use_tls:
                s.starttls()

            if self._user and self._passwd:
                s.login(self._user, self._passwd)

            s.sendmail(mail_from, mail_to.split(','), msg.as_string())
            s.quit()
            self.get_logger().info("send email successfully to {} with subject {}".format(mail_to, subject))
            return True
        except Exception:
            self.get_logger().error('fail to send email to {} with subject {} for error:'
                        .format(mail_to, subject), exc_info=True)
            return False

    def generate_table(self, heads, contents):
        """Generate the html of table in email

        Args:
            heads (list): Table head
            contents (list of lists): Table contents

        Returns:
            str:

        Examples:
        ::
            heads = ('head 1', 'head 2', 'head 3')
            contents = (
                ('cell 1-1', 'cell 1-2', 'cell 1-3'),
                ('cell 2-1', 'cell 2-2', 'cell 2-3')
            )

            table_html = sender.generate_table(heads, contents)
        """
        thead = ''.join(['<th><p>{}</p></th>\n'.format(str(h)) for h in heads])
        tbody = ''
        for cnt in contents:
            tbody += '<tr>{}</tr>\n'.format(''.join(['<td><p>{}</p></td>'.format(str(h)) for h in cnt]))

        return dedent('''
            <table style="table-layout:fixed;" cellspacing="0" cellpadding="10">
                <thead><tr>{thead}</tr></thead>
                <tbody>{tbody}</tbody>
            </table>
            ''').format(thead=thead, tbody=tbody)


if __name__ == '__main__':
    sender = EmailSender()
    assert sender.send_email(
        mail_to='lcai@movoto.com,lcai@movoto.com',
        subject='test: kipp.utils.EmailSender',
        content='fake-content\n\nline 2',
        mail_from='kipp@movoto.com')
