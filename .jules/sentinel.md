## 2026-02-09 - HTML Injection in EmailSender
**Vulnerability:** The `EmailSender` utility in `kipp/utils/mailsender.py` was vulnerable to HTML injection because `parse_content` and `generate_table` methods were constructing HTML by direct string interpolation of user-provided content without escaping.
**Learning:** Utilities that convert text to HTML are common vectors for injection if developers assume the input is safe. Even if the output is an email, mail clients can be vulnerable to XSS or phishing if the HTML is not properly sanitized.
**Prevention:** Always escape user-controlled text before inserting it into HTML templates. Use standard library functions like `html.escape` for this purpose.
