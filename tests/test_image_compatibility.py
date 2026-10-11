"""Exercise current Pillow with generated images and in-memory S3 controls."""

from io import BytesIO
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from PIL import Image

from kipp.images import (
    compress_image,
    generate_possible_thumbnails,
    generate_thumbnails,
    get_thumbnail,
    image_resize_and_compress,
    resize_compress_image,
)


def source_image(size=(800, 600)):
    image = Image.new("RGB", size)
    # Deterministic textured source makes the smaller-JPEG contract meaningful.
    image.putdata(
        [
            ((x * 17) % 256, (y * 31) % 256, (x * y) % 256)
            for y in range(size[1])
            for x in range(size[0])
        ]
    )
    data = BytesIO()
    image.save(data, format="JPEG", quality=100)
    data.seek(0)
    return data


class ImageCompatibilityTests(unittest.TestCase):
    def test_resize_preserves_aspect_and_returns_valid_jpeg(self):
        for function in (resize_compress_image, image_resize_and_compress):
            with self.subTest(function=function.__name__):
                data = function(source_image(), 320)
                image = Image.open(data)
                self.assertEqual(image.size, (320, 240))
                self.assertEqual(image.format, "JPEG")
                image.verify()

    def test_compression_does_not_inflate_source(self):
        source = source_image()
        data = compress_image(source)
        self.assertLessEqual(len(data.getvalue()), len(source.getvalue()))
        Image.open(data).verify()

    def test_thumbnail_is_smaller_and_preserves_explicit_dimensions(self):
        source = source_image()
        data = get_thumbnail(source, 320, 200)
        self.assertLessEqual(len(data.getvalue()), len(source.getvalue()))
        self.assertEqual(Image.open(data).size, (320, 200))
        Image.open(data).verify()

    def test_mocked_upload_and_copy_tiers_remain_compatible(self):
        client = Mock()
        uploads = []

        def upload(data, content_type, key):
            image = Image.open(data)
            uploads.append((key, image.size, content_type))
            image.verify()
            return SimpleNamespace(status=200)

        client.m_uploadImage.side_effect = upload
        self.assertEqual(generate_thumbnails(source_image(), "demo.jpg", client), 7)
        self.assertEqual(
            uploads,
            [
                ("demo_p.jpg", (480, 360), "image/jpeg"),
                ("demo_r.jpg", (800, 600), "image/jpeg"),
            ],
        )
        client.copy_file.assert_called_once_with("demo_r.jpg", "demo_l.jpg")

    def test_possible_thumbnails_do_not_upscale(self):
        client = Mock()
        client.m_uploadImage.return_value = SimpleNamespace(status=200)
        result = generate_possible_thumbnails(source_image(), "demo.jpg", client)
        self.assertEqual(result, [{"width": 480, "type": "p", "height": 360}])
        client.copy_file.assert_not_called()
        self.assertEqual(client.m_uploadImage.call_count, 1)

    def test_failed_mocked_upload_still_raises(self):
        client = Mock()
        client.m_uploadImage.return_value = SimpleNamespace(
            status=503, reason="offline fixture", msg="rejected"
        )
        with self.assertRaises(IOError):
            generate_thumbnails(source_image(), "demo.jpg", client)


if __name__ == "__main__":
    unittest.main()
