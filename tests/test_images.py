#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os
import time
from io import BytesIO
from unittest import TestCase, skipIf
from collections import namedtuple

from PIL import Image
from mock import MagicMock

from kipp.images import (
    compress_image,
    image_resize_and_compress,
    resize_compress_image,
    get_thumbnail,
    generate_thumbnails,
    request_s3_image,
    generate_possible_thumbnails,
)


@skipIf(True, "useless")
class ImagesTestCase(TestCase):
    def setUp(self):
        self.img = Image.new("RGB", (1000, 1000))
        self.img_bio = BytesIO()

        self.img.save(self.img_bio, format="JPEG", quality=100)
        self.img_bio.seek(0, os.SEEK_END)
        self.img_size = self.img_bio.tell()

    def test_image_resize_and_compress(self):
        width = 20
        bio = image_resize_and_compress(self.img_bio, width)
        img = Image.open(bio)
        self.assertEqual(img.size[0], width)
        self.assertEqual(img.size[1], int(self.img.size[1] * 20.0 / self.img.size[0]))
        self.assertIsNone(img.verify())

    def test_compress_image(self):
        bio = compress_image(self.img_bio)
        img = Image.open(bio)
        self.assertIsNone(img.verify())

    def test_resize_compress_image(self):
        width = 20
        bio = resize_compress_image(self.img_bio, width)
        img = Image.open(bio)
        self.assertEqual(img.size[0], width)
        self.assertEqual(img.size[1], int(self.img.size[1] * 20.0 / self.img.size[0]))
        self.assertIsNone(img.verify())

    def test_get_thumbnail(self):
        width = 20
        bio = get_thumbnail(self.img_bio, width)
        img = Image.open(bio)
        self.assertLess(bio.tell(), self.img_size)
        self.assertEqual(img.size[0], width)
        self.assertEqual(img.size[1], int(self.img.size[1] * 20.0 / self.img.size[0]))
        self.assertIsNone(img.verify())

    def test_generate_thumbnails(self):
        key = "abcdefg.poiuy"
        resp = namedtuple("resp", ["status"])(200)
        fail_resp = namedtuple("resp", ["status", "reason", "msg"])(
            500, "fake_reson", "fake_msg"
        )

        def _copy_file(copy_key, thumnail_s3_key):
            self.assertEqual(thumnail_s3_key.split(".")[-1], key.split(".")[-1])

        def generate_m_uploadImage(resp):
            def _m_uploadImage(thm_data, IMG_CONTENT_TYPE, thumnail_s3_key):
                im = Image.open(thm_data)
                self.assertIsNone(im.verify())
                self.assertIsNone(_copy_file("", thumnail_s3_key))
                return resp

            return _m_uploadImage

        s3 = MagicMock()
        s3.m_uploadImage.side_effect = generate_m_uploadImage(resp)
        s3.copy_file.side_effect = _copy_file
        flag = generate_thumbnails(self.img_bio, key, s3)
        self.assertEqual(flag, 7)

        s3.m_uploadImage.side_effect = generate_m_uploadImage(fail_resp)
        self.assertRaises(IOError, generate_thumbnails, self.img_bio, key, s3)

    def test_request_s3_image(self):
        self.img_bio.seek(0)
        data = self.img_bio.read()
        resp = namedtuple("resp", ["status_code", "content"])(200, data)
        fail_resp = namedtuple("resp", ["status_code", "content"])(400, data)
        fake_url = "fake_url"

        def generate_get(resp):
            def _get(url):
                self.assertEqual(url, fake_url)
                return resp

        http_session = MagicMock()
        http_session.get.return_value = resp
        bio = request_s3_image(fake_url, http_session)
        self.assertEqual(bio.read(), data)
        self.assertEqual(http_session.get.call_args_list[0][0], (fake_url,))

        http_session.get.return_value = fail_resp
        start_at = time.time()
        self.assertRaises(AssertionError, request_s3_image, fake_url, http_session)
        self.assertEqual(http_session.get.call_args_list[1][0], (fake_url,))
        self.assertGreater(time.time() - start_at, 9)

    def test_generate_possible_thumbnails(self):
        key = "abcdefg.poiuy"
        resp = namedtuple("resp", ["status"])(200)
        fail_resp = namedtuple("resp", ["status", "reason", "msg"])(
            500, "fake_reason", "fake_msg"
        )

        def _copy_file(copy_key, thumnail_s3_key):
            self.assertEqual(thumnail_s3_key.split(".")[-1], key.split(".")[-1])

        def generate_m_uploadImage(resp):
            def _m_uploadImage(thm_data, IMG_CONTENT_TYPE, thumnail_s3_key):
                im = Image.open(thm_data)
                self.assertIsNone(im.verify())
                self.assertIsNone(_copy_file("", thumnail_s3_key))
                return resp

            return _m_uploadImage

        s3 = MagicMock()
        s3.m_uploadImage.side_effect = generate_m_uploadImage(resp)
        s3.copy_file.side_effect = _copy_file
        expect_result = [
            {"width": 480, "type": "p", "height": 480},
            {"width": 960, "type": "r", "height": 960},
        ]
        flag = generate_possible_thumbnails(self.img_bio, key, s3)
        self.assertEqual(flag, expect_result)

        s3.m_uploadImage.side_effect = generate_m_uploadImage(fail_resp)
        self.assertRaises(IOError, generate_possible_thumbnails, self.img_bio, key, s3)
