## 2025-03-17 - HTML Injection in Email Templates
**Vulnerability:** User-provided content was directly concatenated into HTML email templates in `kipp/utils/mailsender.py`, leading to potential HTML injection and phishing risks.
**Learning:** Utilities that generate HTML content from plain text inputs must always escape special characters to ensure the final output is safe for rendering in mail clients.
**Prevention:** Use `html.escape` (Python 3) or `cgi.escape` (Python 2) for all user-controllable data before embedding it into HTML templates.
