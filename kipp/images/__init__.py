#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
-------------------------
Image resize and compress
-------------------------

resize and compress images with width and quality.

Notify: You should run ``pip install "kipp[image]"`` to install requirements.

"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image

from kipp.decorator import retry


IMG_CONTENT_TYPE: str = "image/jpeg"

# Predefined thumbnail tiers: (suffix, max_width).
# Ordered by ascending width so generate_thumbnails can stop early
# once the source image is narrower than the current tier.
THUMBNAIL_TYPES: tuple[tuple[str, int], ...] = (("p", 480), ("r", 960), ("l", 1920))


def image_resize_and_compress(
    image_bytesIO: BytesIO, width: int, quality: int = 75, optimize: bool = True
) -> BytesIO:
    """Image resize and compress

    Relate to 'DATA-1205'.

    Args:
        image_bytesIO: origin image.
        width: if origin image is wider than width, resize to width.
        quality: quality of destination image.
        optimize: if True, return optimized image.
    """
    pil_image = Image.open(image_bytesIO)
    if pil_image.size[0] <= width:
        return compress_image(image_bytesIO, quality, optimize)

    return resize_compress_image(image_bytesIO, width, quality, optimize)


def compress_image(
    image_bytesIO: BytesIO, quality: int = 75, optimize: bool = True
) -> BytesIO:
    """Re-encode an image as JPEG with the given quality.

    Returns whichever is smaller -- the re-encoded version or the original --
    to avoid inflating already-well-compressed images.
    """
    pil_image = Image.open(image_bytesIO)
    img_data = BytesIO()
    pil_image.convert("RGB").save(
        img_data, format="JPEG", quality=quality, optimize=optimize
    )
    img_data.seek(0)
    image_bytesIO.seek(0)
    return (
        image_bytesIO if len(img_data.read()) > len(image_bytesIO.read()) else img_data
    )


def resize_compress_image(
    image_bytesIO: BytesIO, width: int, quality: int = 75, optimize: bool = True
) -> BytesIO:
    """Get the thumbnail image with input bytesIO and thumbnail width

    This function is deprecated, because new thumbnail image bytes may be more than original image.
    """
    pil_image = Image.open(image_bytesIO)
    (x, y) = pil_image.size
    new_size = (width, int(width * y / x))
    resized_img_bytesio = BytesIO()
    pil_image.resize(new_size, Image.LANCZOS).convert("RGB").save(
        resized_img_bytesio, format="JPEG", quality=quality, optimize=optimize
    )
    return resized_img_bytesio


def get_thumbnail(
    input_image_bytesIO: BytesIO,
    thumbnail_width: int,
    thumbnail_height: int = 0,
    quality_withdraw: int = 5,
    quality: int = 75,
    optimize: bool = True,
) -> BytesIO:
    """Generate a single thumbnail that is guaranteed to be no larger than the original.

    Iteratively lowers JPEG quality by ``quality_withdraw`` steps until the
    compressed thumbnail is smaller than the source.  This prevents the
    perverse case where a small high-entropy source produces a larger thumbnail.

    Args:
        input_image_bytesIO: input origin image bytesIO.
        thumbnail_width: thumbnail image width needed
        thumbnail_height: explicit height; auto-computed from aspect ratio if 0
        quality_withdraw: amount to reduce quality each iteration
        quality & optimize: see Pillow document.
    """
    input_image_bytesIO.seek(0)
    input_bytes = len(input_image_bytesIO.read())
    pimg = Image.open(input_image_bytesIO)

    if not thumbnail_height:
        thumbnail_height = int(thumbnail_width * pimg.size[1] / pimg.size[0])
    thm_size = (thumbnail_width, thumbnail_height)
    pimg = pimg.convert("RGB").resize(thm_size, Image.LANCZOS)
    q = quality
    while 1:
        thumbnail_data = BytesIO()
        pimg.save(thumbnail_data, format="JPEG", quality=q, optimize=optimize)
        thumbnail_data.seek(0)
        t_bytes = len(thumbnail_data.read())

        if t_bytes > input_bytes:
            q -= quality_withdraw
        else:
            thumbnail_data.seek(0)
            return thumbnail_data


def generate_thumbnails(image_bytesIO: BytesIO, img_s3_key: str, s3: Any) -> int:
    """Generate all thumbnail tiers for an image and upload them to S3.

    Once the source image is narrower than a tier width, the compressed-only
    version is uploaded and all subsequent (larger) tiers are created by
    copying that same S3 key -- avoiding redundant re-encoding.

    Args:
        image_bytesIO: origin image.
        img_s3_key: S3 object key for the original image.
        s3: S3 connected client (Utilities.movoto.s3_handler.S3_handler).

    Returns:
        A bitmask with one bit per tier, all set (e.g. 7 for 3 tiers).
    """
    pil_image = Image.open(image_bytesIO)
    key_slices = img_s3_key.split(".")
    copy_key = ""
    for tname, twidth in THUMBNAIL_TYPES:
        thumnail_s3_key = "{}_{}.{}".format(key_slices[0], tname, key_slices[1])
        if copy_key:
            s3.copy_file(copy_key, thumnail_s3_key)
            continue

        if pil_image.size[0] <= twidth:
            thm_data = compress_image(image_bytesIO)  # only do compress
            copy_key = thumnail_s3_key
        else:
            thm_data = get_thumbnail(image_bytesIO, twidth)
        thm_data.seek(0)
        resp = s3.m_uploadImage(thm_data, IMG_CONTENT_TYPE, thumnail_s3_key)
        if resp.status != 200:
            raise IOError(
                "UploadS3Error!! Key[%s] Response[status: %s, reason: %s, msg: %s]"
                % (thumnail_s3_key, resp.status, resp.reason, resp.msg)
            )

    flag = 2 ** len(THUMBNAIL_TYPES) - 1
    return flag


def generate_possible_thumbnails(
    image_bytesIO: BytesIO, img_s3_key: str, s3: Any
) -> list[dict[str, int | str]]:
    """Generate thumbnails only for tiers narrower than the source image.

    Unlike ``generate_thumbnails``, this skips tiers where the source is
    already smaller, so no upscaling or unnecessary copies occur.  Stops
    at the first tier that exceeds the source width (tiers are ascending).

    Args:
        image_bytesIO: origin image.
        img_s3_key: S3 object key for the original image.
        s3: S3 connected client (Utilities.movoto.s3_handler.S3_handler).
    """
    pil_image = Image.open(image_bytesIO)
    key_slices = img_s3_key.split(".")
    generated_thumbnail_list: list[dict[str, int | str]] = []
    for tname, twidth in THUMBNAIL_TYPES:
        if pil_image.size[0] > twidth:
            thumnail_s3_key = "{}_{}.{}".format(key_slices[0], tname, key_slices[1])
            theight = int(twidth * pil_image.size[1] / pil_image.size[0])
            thm_data = get_thumbnail(image_bytesIO, twidth, theight)
            thm_data.seek(0)
            resp = s3.m_uploadImage(thm_data, IMG_CONTENT_TYPE, thumnail_s3_key)
            if resp.status != 200:
                raise IOError(
                    "UploadS3Error!! Key[%s] Response[status: %s, reason: %s, msg: %s]"
                    % (thumnail_s3_key, resp.status, resp.reason, resp.msg)
                )
            generated_thumbnail_list.append(
                {"width": twidth, "type": tname, "height": theight}
            )
        else:
            break
    return generated_thumbnail_list


@retry(Exception, tries=3, delay=3, backoff=3)
def request_s3_image(url: str, http_session: Any) -> BytesIO:
    """Request image data by http session

    Args:
        url: request url
        http_session: you can get it yourself by requests.Session() or give requests.
    """
    res = http_session.get(url)
    assert res.status_code == 200, "request_s3_image error"
    bytesIO = BytesIO()
    bytesIO.write(res.content)
    bytesIO.seek(0)
    return bytesIO


if __name__ == "__main__":
    import requests as http

    # url = "http://staging-img.movoto.com.s3.amazonaws.com/p/404/9548575_0_nyyVEa.jpeg"
    key = "p/104/477149_0_iQyiAu.jpeg"
    #     origin_image_data = request_s3_image("http://staging-img.movoto.com.s3.amazonaws.com/"+key, http)
    #     with open("/tmp/"+key, 'w') as fobj:
    #         fobj.write(origin_image_data.read())
    #     origin_image_data.seek(0)
    import os

    origin_image_data = open("/tmp/" + key, "rb")

    img = Image.open(origin_image_data)
    print(img.size)
    origin_image_data.seek(0)
    import time

    t0 = time.time()
    thumbnail_img_data = get_thumbnail(origin_image_data, 960)
    print(time.time() - t0)
    save_path = "/tmp/p/104/477149_0_iQyiAu_960.jpeg"
    with open(save_path, "w") as fobj:
        fobj.write(thumbnail_img_data.read())

    print("/tmp/" + key, os.path.getsize("/tmp/" + key))
    print(save_path, os.path.getsize(save_path))
    quit()
