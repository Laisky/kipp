#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
------------------------------
Asynchronous HTTPSessionClient
------------------------------

Examples:
::
    from kipp.aio.http import get_http_client_session


    @coroutine2
    def demo():
        with get_http_client_session() as client:
            resp = yield client.get(url)
            resp.headers  # get response's headers as dict
            resp.cookies  # get response's cookies as dict
            resp.json()   # get response's body as dict
            resp.body     # get response's body as str

"""

from __future__ import unicode_literals
from contextlib import contextmanager

from tornado.httpclient import AsyncHTTPClient
from tornado.httputil import parse_cookie, url_concat
from tornado.escape import json_encode, json_decode
from future.standard_library import hooks
with hooks():
    from urllib.parse import urlencode

from kipp.libs.aio import return_in_coroutine
from kipp.utils import get_logger
from .base import coroutine


@contextmanager
def get_http_client_session(*args, **kw):
    """HTTPSessionClient contextmanager"""
    client = HTTPSessionClient(*args, **kw)
    try:
        yield client
    finally:
        client.close()


class HTTPResponse:
    """HTTPResponse Wrapper

    you can get the raw response by ``self.response``
    """

    def __init__(self, resp):
        self.response = resp

    def json(self):
        """Get json format body as dict"""
        return json_decode(self.response.body)

    def __repr__(self):
        return 'HTTPResponse({})'.format(repr(self.response))

    def __str__(self):
        return 'HTTPResponse({})'.format(str(self.response))

    @property
    def cookies(self):
        """Get cookies as dict"""
        cookies = {}
        for new_cookie in self.response.headers.get_list('Set-Cookie'):
            for n, v in parse_cookie(new_cookie).items():
                cookies[n] = v

        return cookies

    def __getattr__(self, name):
        return getattr(self.response, name)


class HTTPSessionClient:
    """HTTPClient with permanent cookies"""

    def __init__(self, *args, **kw):
        self._cookies_dict = {}
        self.httpclient = AsyncHTTPClient(*args, **kw)

    def close(self):
        self.httpclient.close()

    def __exit__(self):
        self.close()

    def get(self, *args, **kw):
        """Request HTTP via GET"""
        kw.update({'method': 'GET'})
        return self.fetch(*args, **kw)

    def delete(self, *args, **kw):
        """Request HTTP via DELETE"""
        kw.update({'method': 'DELETE'})
        return self.fetch(*args, **kw)

    def post(self, *args, **kw):
        """Request HTTP via POST"""
        kw.update({'method': 'POST'})
        return self.fetch(*args, **kw)

    def patch(self, *args, **kw):
        """Request HTTP via PATCH"""
        kw.update({'method': 'PATCH'})
        return self.fetch(*args, **kw)

    def head(self, *args, **kw):
        """Request HTTP via HEAD"""
        kw.update({'method': 'HEAD'})
        return self.fetch(*args, **kw)

    @coroutine
    def fetch(self, *args, **kw):
        """Generate HTTP Request

        Args:
            request (str): url
            method (str): ``GET`` / ``POST``
            params (dict): url parameters
            data (dict): form
            json (dict): form for json
            cookies (dict):
            headers (dict):
        """
        args = self._parse_url(args, kw)
        self._parse_headers(kw)
        self._parse_body(kw)

        get_logger().debug('HTTPSessionClient fetch for args %s, kw %s', args, kw)
        resp = yield self.httpclient.fetch(*args, **kw)
        resp = HTTPResponse(resp)
        self._load_cookies_fr_resp(resp)
        return_in_coroutine(resp)

    def _parse_url(self, args, kw):
        """Add parameters to url"""
        params = kw.pop('params', {})
        url = kw.pop('request', '') or args[0]
        url = url_concat(url, params)
        return (url,) + args[1:]

    def _parse_body(self, kw):
        """Convert body into suitable format"""
        body = kw.get('body')
        data = kw.pop('data', {})
        djson = kw.pop('json', {})
        assert not (body and (data or djson)), 'you should not specified body with data/json'
        assert not (data and djson), 'you should not specified both data and json'
        if data:
            kw['body'] = str(urlencode(data))
            kw['headers']['Content-Type'] = 'application/x-www-form-urlencoded'

        if djson:
            kw['body'] = json_encode(djson)
            kw['headers']['Content-Type'] = 'application/javascript'

    def _parse_headers(self, kw):
        """Add ``Connection`` & ``Cookie`` into headers"""
        kw['headers'] = kw.get('headers', {})
        kw['headers']['Connection'] = 'keep-alive'
        self._parse_cookies(kw)

    def _parse_cookies(self, kw):
        """Add user custom cookies into headers"""
        user_cookies = kw.pop('cookies', {})
        user_cookies.update(kw['headers'].get('Cookie', {}))
        cookies = self._get_cookies(user_cookies)
        if cookies:
            kw['headers']['Cookie'] = cookies

    def _get_cookies(self, user_cookies=None):
        """Concatenate legacy cookies with user cookies"""
        cookies = self._parse_cookies_to_str(self._cookies_dict)
        if user_cookies:
            cookies = self._parse_cookies_to_str(user_cookies)

        get_logger().debug('_get_cookies return cookies: %s', cookies)
        return cookies

    def _load_cookies_fr_resp(self, resp):
        """Load cookies from response"""
        for new_cookie in resp.cookies:
            for n, v in parse_cookie(new_cookie).items():
                self._cookies_dict[n] = v

    def _parse_cookies_to_str(self, cookies):
        """Parse dict of cookies into string"""
        return ';'.join(['{}={}'.format(n, v) for n, v in cookies.items()])
