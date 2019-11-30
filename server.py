import json
from typing import (
    Any,
)
import os
import logging

import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.options import define, options

from draw.algorithms import draw_floor, draw_floor1, draw_bathroom
from draw.core import Size
from draw.utils import save_image, upload_image

DEBUG_MEDIA_ROOT = '/tmp/'
DEBUG_MEDIA_URL = '/media/'

SCHEMES = ('floor', 'walls')

FLOOR_LAYING_METHOD_DIRECT = 1
FLOOR_LAYING_METHOD_DIRECT_CENTER = 2
FLOOR_LAYING_METHOD_DIAGONAL = 3
FLOOR_LAYING_METHODS = (
    FLOOR_LAYING_METHOD_DIRECT,
    FLOOR_LAYING_METHOD_DIRECT_CENTER,
    FLOOR_LAYING_METHOD_DIAGONAL
)

define('port', default='5000', help='Listening port', type=str)
define('cookie_secret', default=os.environ.get('COOKIE_SECRET'), help='Secret cookie', type=str)
define('debug', default=False, help='Debug mode', type=bool)


class BadRequest(tornado.web.HTTPError):

    def __init__(
            self, log_message: str = None, *args: Any, ** kwargs: Any
    ) -> None:
        super().__init__(400, log_message, *args, **kwargs)


class BaseRequestHandler(tornado.web.RequestHandler):

    def write_error(self, status_code: int, **kwargs: Any):
        self.set_header('Content-Type', 'application/json')
        self.finish(json.dumps({
            'error': {
                'code': status_code,
                'message': self._reason
            }
        }))


class DrawHandler(BaseRequestHandler):
    """Create a new scheme of fitting the tiles"""

    def post(self):
        """
        Floor example:
        {
            "scheme": "floor",
            "tile": {
                "width": 500,
                "length": 500,
                "delimiter": 2
            },
            "width": 4000,
            "length": 5000,
            /* The scheme-specific options */
            "options": {
                "method": 1
            }
        }

        Bathroom example:
        {
            "scheme": "walls",
            "tile": {
                "width": 500,
                "length": 500,
                "delimiter": 2
            },
            "width": 4000,
            "length": 5000,
            /* The scheme-specific options */
            "options": {
                "height": 2500,
                "door": {
                    "width": 800,
                    "height": 2000
                }
            }
        }

        """
        args = json.loads(self.request.body)
        print(args)

        if 'scheme' not in args:
            raise BadRequest('Required argument: scheme')
        scheme = args['scheme']
        if scheme not in SCHEMES:
            raise BadRequest(f'Invalid scheme ({scheme}), expected: {",".join(SCHEMES)}')

        # validate common arguments
        if 'tile' not in args:
            raise BadRequest('Required argument: tile')
        tile = args['tile']
        tile_width = tile['width']
        tile_length = tile['length']
        delimiter = tile['delimiter']

        width_mm = args['width']
        length_mm = args['length']

        # validate scheme-specified arguments
        if scheme == 'floor':
            floor_method = args['options']['method']
            if floor_method not in FLOOR_LAYING_METHODS:
                raise BadRequest((
                    f'Invalid floor laying method ({floor_method}),'
                    f' expected: {",".join(FLOOR_LAYING_METHODS)}'
                ))
        elif scheme == 'walls':
            height_mm = args['options']['height']
            if 'door' in args['options']:
                door_size = Size(
                    args['options']['door']['width'],
                    args['options']['door']['height']
                )
            else:
                door_size = None

        # render picture
        if scheme == 'floor':
            if floor_method in (FLOOR_LAYING_METHOD_DIRECT, FLOOR_LAYING_METHOD_DIRECT_CENTER):
                canvas = draw_floor1(width_mm, length_mm, delimiter, tile_width, tile_length, floor_method)
                im = canvas.im
            else:
                im = draw_floor(width_mm, length_mm, tile_width, tile_length, floor_method)
        else:
            canvas = draw_bathroom(length_mm, width_mm, height_mm, delimiter, tile_width, tile_length, door_size)
            im = canvas.im

        filename = save_image(im, DEBUG_MEDIA_ROOT if options.debug else '/tmp')

        if options.debug:
            img_url = os.path.join(DEBUG_MEDIA_URL, os.path.basename(filename))
        else:
            img_url = upload_image(filename)
            os.remove(filename)

        result = {
            'ok': True,
            'url': img_url
        }

        self.write(json.dumps(result))


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/api/draw', DrawHandler),
        ]
        settings = dict(
            cookie_secret=options.cookie_secret,
            static_path=os.path.join(os.path.dirname(__file__), 'static'),
            debug=True
        )
        super().__init__(handlers, **settings)


def main():
    tornado.options.parse_command_line()
    logging.getLogger().setLevel(logging.DEBUG)
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
