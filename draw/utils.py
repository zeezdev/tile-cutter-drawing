import os
import uuid

import cloudinary
import cloudinary.uploader
import cloudinary.api


def save_image(image, path):
    filename = str(uuid.uuid4()) + ".png"
    fullname = os.path.join(path, filename)
    image.save(fullname, "PNG")

    return fullname


def upload_image(filename):
    """
    https://res.cloudinary.com/hndb3kzlx/image/upload/v1574079318/fgpbnms77h9xrm9mmalf.png
    """
    uploaded = cloudinary.uploader.upload(filename)
    # FIXME: process bad request
    return uploaded['secure_url']
