from unittest import TestCase
from kipp.utils import EmailSender

class SecurityEmailSenderTestCase(TestCase):
    def setUp(self):
        self.sender = EmailSender("fake_host", "fake_port")

    def test_parse_content_escaping(self):
        content = '<script>alert(1)</script>'
        result = self.sender.parse_content(content)
        self.assertNotIn('<script>', result)
        self.assertIn('&lt;script&gt;', result)

    def test_generate_table_escaping(self):
        heads = ['<img src=x onerror=alert(1)>']
        contents = [['<a href="javascript:alert(1)">click</a>']]
        result = self.sender.generate_table(heads, contents)
        self.assertNotIn('<img', result)
        self.assertNotIn('<a', result)
        self.assertIn('&lt;img', result)
        self.assertIn('&lt;a', result)
