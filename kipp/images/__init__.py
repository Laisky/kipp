#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
-------------------------
Image resize and compress
-------------------------

resize and compress images with width and quality.

Notify: You should run ``pip install "kipp[image]"`` to install requirements.

"""

from __future__ import unicode_literals
from io import BytesIO

from PIL import Image

from kipp.decorator import retry


IMG_CONTENT_TYPE = 'image/jpeg'
THUMBNAIL_TYPES = ((u'p', 480), (u'r', 960), (u'l', 1920))


def image_resize_and_compress(image_bytesIO, width, quality=75, optimize=True):
    """Image resize and compress

    Relate to 'DATA-1205'.

    Args:
        image_data (file handler): origin image.
        width (int): if origin image is wider than width, resize to width.
        quality (int, default=80): quality of destination image.
        optimize (bool, default=True): if True, return optimized image.
    """
    pil_image = Image.open(image_bytesIO)
    if pil_image.size[0] <= width:
        return compress_image(image_bytesIO, quality, optimize)

    return resize_compress_image(image_bytesIO, width, quality, optimize)


def compress_image(image_bytesIO, quality=75, optimize=True):
    pil_image = Image.open(image_bytesIO)
    img_data = BytesIO()
    pil_image.convert("RGB").save(img_data, format='JPEG', quality=quality, optimize=optimize)
    img_data.seek(0)
    image_bytesIO.seek(0)
    return image_bytesIO if len(img_data.read()) > len(image_bytesIO.read()) else img_data


def resize_compress_image(image_bytesIO, width, quality=75, optimize=True):
    """Get the thumbnail image with input bytesIO and thumbnail width

    This function is deprecated, because new thumbnail image bytes may be more than original image.
    """
    pil_image = Image.open(image_bytesIO)
    (x, y) = pil_image.size
    new_size = (width, int(width * y / x))
    resized_img_bytesio = BytesIO()
    pil_image.resize(new_size, Image.ANTIALIAS) \
        .convert("RGB") \
        .save(resized_img_bytesio, format='JPEG', quality=quality, optimize=optimize)
    return resized_img_bytesio


def get_thumbnail(input_image_bytesIO, thumbnail_width, thumbnail_height=0, quality_withdraw=5, quality=75, optimize=True):
    """Generate the image thumbnails for one input image

    Args:
        input_image_bytesIO (io.BytesIO): input origin image bytesIO.
        thumbnail_width (int): thumbnail image width needed
        quality_withdraw (int): quality_withdraw
        quality & optimize: see Pillow document.
    """
    input_image_bytesIO.seek(0)
    input_bytes = len(input_image_bytesIO.read())
    pimg = Image.open(input_image_bytesIO)

    if not thumbnail_height:
        thumbnail_height = int(thumbnail_width * pimg.size[1] / pimg.size[0])
    thm_size = (thumbnail_width, thumbnail_height)
    pimg = pimg.convert("RGB").resize(thm_size, Image.ANTIALIAS)
    q = quality
    while 1:
        thumbnail_data = BytesIO()
        pimg.save(thumbnail_data, format='JPEG', quality=q, optimize=optimize)
        thumbnail_data.seek(0)
        t_bytes = len(thumbnail_data.read())

        if t_bytes > input_bytes:
            q -= quality_withdraw
        else:
            thumbnail_data.seek(0)
            return thumbnail_data


def generate_thumbnails(image_bytesIO, img_s3_key, s3):
    """Generate the image thumbnails for one input image,
        and store the thumbnails in s3.

    Args:
        img_data (io.BytesIO): origin image.
        img_s3_key (str): img_s3_key
        s3 (Utilities.movoto.s3_handler.S3_handler): s3 connected client

    """
    pil_image = Image.open(image_bytesIO)
    key_slices = img_s3_key.split(".")
    copy_key = ''
    for tname, twidth in THUMBNAIL_TYPES:
        thumnail_s3_key = "{}_{}.{}".format(key_slices[0], tname, key_slices[1])
        if copy_key:
            s3.copy_file(copy_key, thumnail_s3_key)
            continue

        if pil_image.size[0] <= twidth:
            thm_data = compress_image(image_bytesIO) # only do compress
            copy_key = thumnail_s3_key
        else:
            thm_data = get_thumbnail(image_bytesIO, twidth)
        thm_data.seek(0)
        resp = s3.m_uploadImage(thm_data, IMG_CONTENT_TYPE, thumnail_s3_key)
        if resp.status != 200:
            raise IOError('UploadS3Error!! Key[%s] Response[status: %s, reason: %s, msg: %s]'
                            % (thumnail_s3_key, resp.status, resp.reason, resp.msg))

    flag = 2 ** len(THUMBNAIL_TYPES) - 1
    return flag


# def generate_thumbnails(image_bytesIO, img_s3_key, s3):
#     """ Generate the image thumbnails for one input image,
#         and store the thumbnails in s3.
#
#     Args:
#         img_data (io.BytesIO): origin image.
#         img_s3_key (str): img_s3_key
#         thumbnail_types : the thumbnails to generate, please make sure it is order by width ascend.
#                         Examples: ((u'p', 480),
#                                     (u'r', 960),
#                                     (u'l', 1920))
#
#         s3 (Utilities.movoto.s3_handler.S3_handler): s3 connected client
#
#     """
#     pil_image = Image.open(image_bytesIO)
#     key_slices = img_s3_key.split(".")
#     copy_key = ''
#     thum_o = None
#     for tname, twidth in THUMBNAIL_TYPES[::-1]:
#         thumnail_s3_key = "{}_{}.{}".format(key_slices[0], tname, key_slices[1])
#         if pil_image.size[0] <= twidth:
#             if copy_key:
#                 new_key = s3.copy_file(copy_key, thumnail_s3_key)
#                 if not new_key:
#                     raise Exception('Copy S3 key [%s] error!' % thumnail_s3_key)
#                 continue
#             else:
#                 thm_data = compress_image(image_bytesIO) # only do compress
#                 thum_o = thm_data
#                 copy_key = thumnail_s3_key
#         else:
#             thm_data = get_thumbnail(thum_o if thum_o else image_bytesIO, twidth)
#         thm_data.seek(0)
#         resp = s3.m_uploadImage(thm_data, IMG_CONTENT_TYPE, thumnail_s3_key)
#         if resp.status != 200:
#             raise Exception('Upload S3 key [%s] error!' % thumnail_s3_key)
#
#     flag = 2 ** len(THUMBNAIL_TYPES) - 1
#     return flag

def generate_possible_thumbnails(image_bytesIO, img_s3_key, s3):
    """Generate the image thumbnails for one input image,
        and store the thumbnails in s3.

    Args:
        img_data (io.BytesIO): origin image.
        img_s3_key (str): img_s3_key
        s3 (Utilities.movoto.s3_handler.S3_handler): s3 connected client

    """
    pil_image = Image.open(image_bytesIO)
    key_slices = img_s3_key.split(".")
    generated_thumbnail_list = []
    for tname, twidth in THUMBNAIL_TYPES:
        if pil_image.size[0] > twidth:
            thumnail_s3_key = "{}_{}.{}".format(key_slices[0], tname, key_slices[1])
            theight = int(twidth * pil_image.size[1] / pil_image.size[0])
            thm_data = get_thumbnail(image_bytesIO, twidth, theight)
            thm_data.seek(0)
            resp = s3.m_uploadImage(thm_data, IMG_CONTENT_TYPE, thumnail_s3_key)
            if resp.status != 200:
                raise IOError('UploadS3Error!! Key[%s] Response[status: %s, reason: %s, msg: %s]'
                                % (thumnail_s3_key, resp.status, resp.reason, resp.msg))
            generated_thumbnail_list.append({'width': twidth, 'type': tname, 'height': theight})
        else:
            break
    return generated_thumbnail_list


@retry(Exception, tries=3, delay=3, backoff=3)
def request_s3_image(url, http_session):
    """Request image data by http session

    Args:
        url (str): request url
        http_session: you can get it yourself by requests.Session() or give requests.
    """
    res = http_session.get(url)
    assert res.status_code == 200, 'request_s3_image error'
    bytesIO = BytesIO()
    bytesIO.write(res.content)
    bytesIO.seek(0)
    return bytesIO


if __name__ == '__main__':
    import requests as http
    #url = "http://staging-img.movoto.com.s3.amazonaws.com/p/404/9548575_0_nyyVEa.jpeg"
    key = "p/104/477149_0_iQyiAu.jpeg"
#     origin_image_data = request_s3_image("http://staging-img.movoto.com.s3.amazonaws.com/"+key, http)
#     with open("/tmp/"+key, 'w') as fobj:
#         fobj.write(origin_image_data.read())
#     origin_image_data.seek(0)
    import os
    origin_image_data = open("/tmp/"+key, 'rb')

    img = Image.open(origin_image_data)
    print(img.size)
    origin_image_data.seek(0)
    import time
    t0 = time.time()
    thumbnail_img_data = get_thumbnail(origin_image_data, 960)
    print(time.time() - t0)
    save_path = "/tmp/p/104/477149_0_iQyiAu_960.jpeg"
    with open(save_path, 'w') as fobj:
        fobj.write(thumbnail_img_data.read())

    print("/tmp/"+key, os.path.getsize("/tmp/"+key))
    print(save_path, os.path.getsize(save_path))
    quit()

