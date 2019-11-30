#!/usr/bin/env python

import copy
from math import ceil
import os

from abc import ABCMeta, abstractmethod, abstractstaticmethod
from PIL import Image, ImageDraw, ImageFont


# FIXME: real values
DRAWING_WATERMARK_TEXT = 'www.tcutter.ru'
DRAWING_WATERMARK_FONT = os.path.join('static', 'fonts', 'arial.ttf')

color = (120, 120, 120, 255)
color_cutted = (255, 0, 0, 255)


__WATERMARK_FONT_SIZE = 60


LAYING_METHOD_DIRECT = 1
LAYING_METHOD_DIRECT_CENTER = 2
LAYING_METHOD_DIAGONAL = 3


def get_font(size):
    return ImageFont.truetype(
        DRAWING_WATERMARK_FONT,
        size=size
    )


def add_text_watermark(text):

    def decorator(func):
        def wrapper(*args):
            image = func(*args)

            watermark = Image.new('RGBA', size=image.size, color=0)
            # watermark = Image.new('RGBA', size=(image.width, 64), color=0)
            draw = ImageDraw.Draw(watermark)
            font = get_font(60)
            tw = None
            th = None
            while True:
                tw, th = draw.textsize(text, font=font)
                if tw+10 < image.size[0] and th+10 < image.size[1]:
                    break
                font = get_font(font.size-2)

            draw.text(
                (image.width/2 - tw/2, image.height/2 - th/2),
                text,
                fill=(0, 0, 0, 128),
                font=font
            )

            # image.paste(watermark, box=(0, 15), mask=watermark)
            return Image.alpha_composite(image, watermark)
            # return image

        return wrapper
    return decorator


class Object(metaclass=ABCMeta):

    def __init__(self):
        self.offset = (0, 0)

    @abstractmethod
    def draw(self, canvas, start_pos, **kwargs): pass

    @staticmethod
    def _draw_line(d, x0, y0, x1, y1, color=None):
        """
        :param d:
        :type d: ImageDraw
        :param x0:
        :param y0:
        :param x1:
        :param y1:
        :return:
        """
        d.line((x0, y0, x1, y1), fill=color or (80, 80, 80, 255), width=1)

    @abstractmethod
    def draw_contour_out(self, canvas, start_pos, length): pass

    @abstractmethod
    def get_size(self):
        """
        :return:
        :rtype: Size
        """
        pass


class Size:
    def __init__(self, width, height):
        self.width = width
        self.height = height

    def __str__(self):
        return "{}x{}".format(self.width, self.height)


class Canvas:
    def __init__(self, w, h, scale_factor=None, max_size=None):
        """
        :param w:
        :param h:
        :param scale_factor:
        :param max_size:
        :type Size
        """
        self._width = w
        self._height = h
        if scale_factor:
            self._scale_factor = scale_factor
        elif max_size:
            sf = 1.0
            while True:
                change = False
                if max_size.width * sf > self._width or max_size.height * sf > self._height:
                    sf *= 0.9
                    change = True

                if max_size.width * (sf * 1.0625) <= self._width and max_size.height * (sf * 1.0625) <= self._height:
                    sf *= 1.0625
                    change = True

                if not change:
                    break

            self._scale_factor = sf
            print("Scale factor auto set to: %f" % sf)
        else:
            raise Exception("need scale_factor or max_size")

        self.im = Image.new(
            'RGBA',
            (self._width, self._height),
            (255, 255, 255, 255)
        )

    def get_draw(self):
        return ImageDraw.Draw(self.im)

    def save_to_file(self, filename):
        self.im.save(filename, "PNG")

    def to_pixels(self, value):
        """Convert mm in to pixels.
        :param value: value in mm
        :type value: float
        :return: scaled value in pixels of canvas
        :rtype: int
        """
        return int(self._scale_factor * value)


class Tile(Object):
    def __init__(self, w, h, start_x=None, start_y=None, max_x=None, max_y=None, diag=False):
        super(Tile, self).__init__()
        self.width = w
        self.height = h
        self.start_x = start_x
        self.start_y = start_y
        self.max_x = max_x
        self.max_y = max_y
        self.diag = diag

    def _direct_draw(self, canvas, start_pos, **kwargs):
        d = canvas.get_draw()
        wpix = canvas.to_pixels(self.width)
        hpix = canvas.to_pixels(self.height)

        sp = start_pos

        if self.max_x is not None:
            wpix = self.max_x
        if self.max_y is not None:
            hpix = self.max_y

        if self.start_x is not None:
            wpix = wpix - self.start_x
            sp.x += self.start_x
        if self.start_y is not None:
            hpix = hpix - self.start_y
            sp.y += self.start_y

        # if wpix <= 0:
        #     print("[WRN]: tile width <= 0")
        #     return

        # fill shape
        d.polygon([
            (sp.x, sp.y),
            (sp.x + wpix, sp.y),
            (sp.x + wpix, sp.y + hpix),
            (sp.x, sp.y + hpix)
        ], fill="#b9cbda")

        # top line
        self._draw_line(
            d, sp.x, sp.y, sp.x + wpix, sp.y,
            color=color if self.start_y is None else color_cutted
        )

        # left line
        self._draw_line(
            d, sp.x, sp.y + hpix, sp.x, sp.y,
            color=color if self.start_x is None else color_cutted
        )

        # right line
        self._draw_line(
            d, sp.x + wpix, sp.y, sp.x + wpix, sp.y + hpix,
            color=color if self.max_x is None else color_cutted
        )

        # bottom line
        self._draw_line(
            d, sp.x + wpix, sp.y + hpix, sp.x, sp.y + hpix,
            color=color if self.max_y is None else color_cutted
        )

    def _diag_draw(self, canvas, start_pos, **kwargs):
        pass

    def draw(self, canvas, start_pos, **kwargs):
        if self.diag:
            self._diag_draw(canvas, start_pos, **kwargs)
        else:
            self._direct_draw(canvas, start_pos, **kwargs)

    def draw_contour_out(self, canvas, start_pos, length): pass

    def get_size(self):
        return Size(self.width, self.height)


# class DrawSettings:
#     def __init__(self, cc):
#         self.contour_color = cc


class Position:
    def __init__(self, x=0, y=0):
        """
        :param x: offset by X-coord in pixels
        :param y: offset by Y-coord in pixels
        """
        self.x = x
        self.y = y


class WallTilesOptions:
    def __init__(self, w, h, d, sx=None, sy=None, mx=None, my=None):
        """
        :param w: tile width in mm
        :param h: tile height in mm
        :param d: delimiter in mm
        :param sx: start from by X-coord in mm
        :param sy: start from by Y-coord in mm
        :param mx:
        :param my:
        """
        self.width = w
        self.height = h
        self.delimiter = d
        self.start_x = sx
        self.start_y = sy
        self.max_x = mx
        self.max_y = my


class Wall(Object):
    def __init__(self, w, h, tile, options=None):
        """
        :param w:
        :param h:
        :param tile:
        :type tile: WallTilesOptions
        :param options:
        """
        super(Wall, self).__init__()

        # Validation

        if 'door_width' in options and options['door_width'] is not None:
            assert options['door_width'] <= w
        if 'door_height' in options and options['door_height'] is not None:
            assert options['door_height'] <= h

        if w <= 0:
            raise Exception("w: invalid value")
        if h <= 0:
            raise Exception("h: invalid value")

        # -----------------

        self.height = h
        self.width = w

        self._tile_opt = tile
        d = self._tile_opt.delimiter
        tw = self._tile_opt.width
        twd = tw+d  # длина плитки с последующим! разделителем
        th = self._tile_opt.height
        # thd = th+d
        tsx = (self._tile_opt.start_x or 0)
        clear_width = self.width - (tsx + d)

        self._tile_opt.max_x = None
        ceil_num = ceil(clear_width/twd)

        if ceil_num * twd > clear_width:
            self._tile_opt.max_x = tw - ((ceil_num * twd) - clear_width)

        self._tile_opt.max_y = None

        self._opt = (options or {})

    def get_tile_options(self):
        return self._tile_opt

    def get_size(self):
        return Size(self.width, self.height)

    def draw(self, canvas, start_pos, **kwargs):
        """
        :param canvas:
        :type canvas: Canvas
        :param start_pos:
        :type start_pos: Position
        :param y_direction:  1-сверху вниз/-1-снизу вверх
        :return:
        """
        y_direction = kwargs.get('y_direction', -1)

        d = canvas.get_draw()
        wpix = canvas.to_pixels(self.width)
        hpix = canvas.to_pixels(self.height)
        sp = start_pos

        # Рисуем общий контур стены
        self._draw_line(d, sp.x, sp.y, sp.x + wpix, sp.y)
        self._draw_line(d, sp.x + wpix, sp.y, sp.x + wpix, sp.y + hpix)
        self._draw_line(d, sp.x + wpix, sp.y + hpix, sp.x, sp.y + hpix)
        self._draw_line(d, sp.x, sp.y + hpix, sp.x, sp.y)

        # Рисуем внешний контур для размеров
        if 'contour_out' in self._opt:
            length = 15
            if 'length' in self._opt['contour_out']:
                length = int(self._opt['contour_out']['length'])
            self.draw_contour_out(canvas, start_pos, length)  # TODO: away from here...

        # Рисуем плитки
        tile_wpix = canvas.to_pixels(self._tile_opt.width)
        tile_hpix = canvas.to_pixels(self._tile_opt.height)
        tile_dpix = canvas.to_pixels(self._tile_opt.delimiter) or 1

        tile = Tile(self._tile_opt.width, self._tile_opt.height)

        local = Position()
        first_x = True
        first_y = True
        tiles_count = 0

        is_door_draw = 'door_width' in self._opt and 'door_height' in self._opt \
                       and self._opt['door_width'] is not None and self._opt['door_height'] is not None
        center = Position(sp.x + wpix // 2, sp.y + hpix // 2)  # цетр стены с учетом начального положения

        if is_door_draw:
            door_size = Size(
                canvas.to_pixels(self._opt['door_width']),
                canvas.to_pixels(self._opt['door_height'])
            )
            door_pos = Position(center.x - (door_size.width/2), sp.y + hpix - door_size.height)

        while True:
            local.y += tile_dpix  # ряд начинается с разделителя

            start_y = None
            max_y = None

            if local.y + tile_hpix > hpix - tile_dpix:  # целая плитка не входит
                if y_direction == 1:  # подрезка снизу
                    max_y = (hpix - tile_dpix) - local.y
                elif y_direction == -1:  # подрезка сверху
                    start_y = (local.y + tile_hpix) - (hpix - tile_dpix)
                else:
                    raise Exception("invalid y_direction")

            while True:
                sp1 = copy.copy(sp)
                local.x += tile_dpix  # ряд начинается с разделителя

                start_x = None
                max_x = None

                # если в настройках стены есть сдвиги добавляем их первому ряду плиток
                if self._tile_opt.start_x and first_x:
                    start_x = canvas.to_pixels(self._tile_opt.start_x)
                    sp1.x -= start_x

                if self._tile_opt.start_y and first_y:
                    start_y = canvas.to_pixels(self._tile_opt.start_y)

                if local.x + tile_wpix + tile_dpix > wpix:
                    max_x = (wpix - tile_dpix) - local.x

                tile.start_x = start_x
                tile.start_y = start_y
                tile.max_x = max_x
                tile.max_y = max_y

                if y_direction == 1:
                    pos = Position(
                        sp1.x + local.x,
                        sp1.y + local.y
                    )
                elif y_direction == -1:
                    pos = Position(
                        sp1.x + local.x,
                        sp1.y + hpix - (local.y + tile_hpix)
                    )
                else:
                    raise Exception("invalid y_direction")

                tile_pos = PositionalObject(tile, pos)
                if not is_door_draw or not tile_pos.is_in_area(door_pos, door_size, canvas):
                    tile_pos.draw(canvas)

                if tile.start_x is None:  # если плитка не подрезка с предыдущей стены
                    tiles_count += 1

                if max_x is not None and max_x > 0:
                    local.x += tile_dpix
                    local.x += max_x - (start_x or 0)
                    self._tile_opt.max_x = max_x / canvas._scale_factor  # запомним подрезку последней плитки
                else:
                    local.x += tile_wpix - (start_x or 0)

                # if tile_dpix > 2:
                #     x += tile_dpix-2
                if local.x >= wpix:
                    break

                first_x = False

            # ---------
            local.x = 0
            first_x = True

            if start_y is not None:
                local.y += tile_hpix  # -start_y
            else:
                local.y += tile_hpix

            if local.y >= hpix:
                break

        # Draw the door
        if 'door_width' in self._opt and 'door_height' in self._opt \
                and self._opt['door_width'] is not None and self._opt['door_height'] is not None:
            door_width_half_px = canvas.to_pixels(self._opt['door_width'])/2
            door_height_px = canvas.to_pixels(self._opt['door_height'])

            # Рисование двери заливкой
            # draw = canvas.get_draw()
            d.polygon([
                (center.x-door_width_half_px, sp.y+hpix),
                (center.x-door_width_half_px, sp.y+hpix-door_height_px),
                (center.x+door_width_half_px, sp.y+hpix-door_height_px),
                (center.x+door_width_half_px, sp.y+hpix),
            ], fill="#fff")

            # Рисование двери линиями
            self._draw_line(d, center.x - door_width_half_px, sp.y + hpix,
                            center.x - door_width_half_px, sp.y + hpix - door_height_px, color=color_cutted)
            self._draw_line(d, center.x + door_width_half_px, sp.y + hpix,
                            center.x + door_width_half_px, sp.y + hpix - door_height_px, color=color_cutted)
            self._draw_line(d, center.x - door_width_half_px, sp.y + hpix - door_height_px,
                            center.x + door_width_half_px, sp.y + hpix - door_height_px, color=color_cutted)

        # TODO: other objects ...

        bound_box_in_canvas = (
            sp.x,  # start X
            sp.y,  # start Y
            wpix,  # width
            hpix,  # height
        )
        print("tiles count=%d" % tiles_count)

        return bound_box_in_canvas

    def draw_contour_out(self, canvas, start_pos, length):
        d = canvas.get_draw()
        wpix = canvas.to_pixels(self.width)
        hpix = canvas.to_pixels(self.height)
        sp = start_pos

        self._draw_line(d, sp.x, sp.y, sp.x - length, sp.y)
        self._draw_line(d, sp.x, sp.y, sp.x, sp.y - length)

        self._draw_line(d, sp.x+wpix, sp.y, sp.x+wpix + length, sp.y)
        self._draw_line(d, sp.x+wpix, sp.y, sp.x+wpix, sp.y - length)

        self._draw_line(d, sp.x, sp.y+hpix, sp.x - length, sp.y + hpix)
        self._draw_line(d, sp.x, sp.y+hpix, sp.x, sp.y + hpix + length)

        self._draw_line(d, sp.x + wpix, sp.y + hpix, sp.x + wpix + length, sp.y + hpix)
        self._draw_line(d, sp.x + wpix, sp.y + hpix, sp.x + wpix, sp.y + hpix + length)


class AbstractFloorDrawingMethod(metaclass=ABCMeta):

    @abstractstaticmethod
    def draw_floor(canvas, start_pos, size_pix, tile_opt, y_dir):
        pass


class DirectFloorDrawingMethod(AbstractFloorDrawingMethod):

    @staticmethod
    def draw_floor(canvas, start_pos, size_pix, tile_opt, y_dir):
        tile_wpix = canvas.to_pixels(tile_opt.width)
        tile_hpix = canvas.to_pixels(tile_opt.height)
        tile_dpix = canvas.to_pixels(tile_opt.delimiter) or 1

        tile = Tile(tile_opt.width, tile_opt.height)

        local = Position()
        tiles_count = 0

        sp = copy.copy(start_pos)
        wpix, hpix = size_pix.width, size_pix.height

        while True:
            local.y += tile_dpix  # ряд начинается с разделителя

            start_y = None
            max_y = None

            if local.y + tile_hpix > hpix - tile_dpix:  # целая плитка не входит
                if y_dir == 1:  # подрезка снизу
                    max_y = (hpix - tile_dpix) - local.y
                elif y_dir == -1:  # подрезка сверху
                    start_y = (local.y + tile_hpix) - (hpix - tile_dpix)
                else:
                    raise Exception("invalid y_direction")

            while True:
                local.x += tile_dpix  # ряд начинается с разделителя

                start_x = None
                max_x = None

                tmp = (local.x + tile_wpix + tile_dpix) - wpix
                if tmp > 0:
                    max_x = tile_wpix - ((local.x + tile_wpix + tile_dpix) - wpix)

                tile.start_x = start_x
                tile.start_y = start_y
                tile.max_x = max_x
                tile.max_y = max_y

                if y_dir == 1:
                    pos = Position(
                        sp.x + local.x,
                        sp.y + local.y
                    )
                elif y_dir == -1:
                    pos = Position(
                        sp.x + local.x,
                        sp.y + hpix - (local.y + tile_hpix)
                    )
                else:
                    raise Exception("invalid y_direction")

                tile_pos = PositionalObject(tile, pos, {'y_direction': y_dir})
                tile_pos.draw(canvas)

                if tile.start_x is None:  # если плитка не подрезка с предыдущей стены
                    tiles_count += 1

                if max_x is not None and max_x > 0:
                    local.x += tile_dpix
                    local.x += max_x - (start_x or 0)
                    tile_opt.max_x = max_x / canvas._scale_factor  # запомним подрезку последней плитки
                else:
                    local.x += tile_wpix - (start_x or 0)

                # if tile_dpix > 2:
                #     x += tile_dpix-2
                if local.x >= wpix:
                    break

                # first_x = False

            # ---------
            local.x = 0
            # first_x = True

            if start_y is not None:
                local.y += tile_hpix  # -start_y
            else:
                local.y += tile_hpix

            if local.y >= hpix:
                break


class CenterFloorDrawingMethod(AbstractFloorDrawingMethod):

    @staticmethod
    def draw_floor(canvas, start_pos, size_pix, tile_opt, y_dir):
        tile_wpix = canvas.to_pixels(tile_opt.width)
        tile_hpix = canvas.to_pixels(tile_opt.height)
        tile_dpix = canvas.to_pixels(tile_opt.delimiter) or 1

        tile = Tile(tile_opt.width, tile_opt.height)

        sp = copy.copy(start_pos)
        wpix, hpix = size_pix.width, size_pix.height

        # находим центр
        center = Position(
            (wpix - tile_wpix) // 2,
            (hpix - tile_hpix) // 2
        )
        tiles_count = 0  # optional

        def draw_stip(center):
            nonlocal tiles_count

            local_center = copy.copy(center)  # начальная позиция

            # рисуем центр
            pos = Position(
                sp.x + local_center.x,
                sp.y + local_center.y
            )
            tile_pos = PositionalObject(tile, pos,  {'y_direction': y_dir})
            tile_pos.draw(canvas)
            tiles_count += 1

            local = copy.copy(local_center)
            local.y += tile_hpix - tile_dpix

            # вниз от центра
            while True:
                local.y += tile_dpix

                if local.y + tile_hpix > hpix - tile_hpix:  # целая плитка не входит
                    tile.start_y = None
                    tile.max_y = (hpix - tile_dpix) - local.y
                else:
                    tile.start_y = None
                    tile.max_y = None

                pos = Position(
                    sp.x + local.x,
                    sp.y + local.y
                )
                tile_pos = PositionalObject(tile, pos,  {'y_direction': y_dir})
                tile_pos.draw(canvas)
                tiles_count += 1

                local.y += tile_hpix
                if local.y > hpix:
                    break

            local = copy.copy(local_center)

            # вверх от центра
            while True:
                local.y -= tile_dpix
                if local.y < 0:  # целая плитка не входит
                    tile.start_y = local.y * -1
                    tile.max_y = None
                else:
                    tile.start_y = None
                    tile.max_y = None

                pos = Position(
                    sp.x + local.x,
                    sp.y + local.y
                )
                tile_pos = PositionalObject(tile, pos,  {'y_direction': y_dir})
                tile_pos.draw(canvas)
                tiles_count += 1

                local.y -= tile_hpix
                if local.y < -tile_hpix:
                    break

        local_center = copy.copy(center)
        draw_stip(local_center)  # центральная полоса
        local_center.x += tile_wpix

        # полосы справа
        while True:
            local_center.x += tile_dpix

            if local_center.x + tile_wpix > wpix - tile_wpix:  # целая плитка не входит
                tile.start_x = None
                tile.max_x = (wpix - tile_dpix) - local_center.x
            else:
                tile.start_x = None
                tile.max_x = None

            draw_stip(local_center)

            local_center.x += tile_wpix
            if local_center.x > wpix:
                break

        # полосы слева
        local_center = copy.copy(center)
        while True:
            local_center.x -= tile_wpix + tile_dpix

            if local_center.x < 0:  # целая плитка не входит
                tile.start_x = local_center.x * -1
                tile.max_x = None
            else:
                tile.start_x = None
                tile.max_x = None

            draw_stip(local_center)
            if local_center.x < 0:
                break


class DiagonalFloorDrawingMethod(AbstractFloorDrawingMethod):

    @staticmethod
    def draw_floor(canvas, start_pos, size_pix, tile_opt, y_dir):
        pass


FLOOR_DRAWING_METHODS = {
    LAYING_METHOD_DIRECT: DirectFloorDrawingMethod,
    LAYING_METHOD_DIRECT_CENTER: CenterFloorDrawingMethod,
    LAYING_METHOD_DIAGONAL: DiagonalFloorDrawingMethod
}


class Floor(Object):
    """Draw a floor object"""

    DEFAULT_DIRECTION = 1

    def __init__(self, w, l, tile, options=None):
        super(Floor, self).__init__()

        self.width = w
        self.length = l
        self._tile_opt = tile

        self._opt = options or {}

    def draw(self, canvas, start_pos, **kwargs):
        drawing_method = kwargs.get('method', LAYING_METHOD_DIRECT)
        assert drawing_method in FLOOR_DRAWING_METHODS, f'Unknown floor drawing method: {drawing_method}'

        y_dir = kwargs.get('y_direction', Floor.DEFAULT_DIRECTION)

        d = canvas.get_draw()
        wpix = canvas.to_pixels(self.length)
        hpix = canvas.to_pixels(self.width)
        sp = start_pos
        size_pix = Size(wpix, hpix)

        # Рисуем общий контур стены
        self._draw_line(d, sp.x, sp.y, sp.x + wpix, sp.y)
        self._draw_line(d, sp.x + wpix, sp.y, sp.x + wpix, sp.y + hpix)
        self._draw_line(d, sp.x + wpix, sp.y + hpix, sp.x, sp.y + hpix)
        self._draw_line(d, sp.x, sp.y + hpix, sp.x, sp.y)

        # Рисуем внешний контур для размеров
        if 'contour_out' in self._opt:
            length = 15
            if 'length' in self._opt['contour_out']:
                length = int(self._opt['contour_out']['length'])
            self.draw_contour_out(canvas, start_pos, length)  # TODO: away from here...

        # Рисуем плитки
        FLOOR_DRAWING_METHODS[drawing_method].draw_floor(canvas, start_pos, size_pix, self._tile_opt, y_dir)

        # TODO: other objects ...

        bound_box_in_canvas = (
            sp.x,  # start X
            sp.y,  # start Y
            wpix,  # width
            hpix,  # height
        )
        # print("tiles count=%d" % tiles_count)

        return bound_box_in_canvas

    def draw_contour_out(self, canvas, start_pos, length):
        d = canvas.get_draw()
        wpix = canvas.to_pixels(self.length)
        hpix = canvas.to_pixels(self.width)
        sp = start_pos

        self._draw_line(d, sp.x, sp.y, sp.x - length, sp.y)
        self._draw_line(d, sp.x, sp.y, sp.x, sp.y - length)

        self._draw_line(d, sp.x+wpix, sp.y, sp.x+wpix + length, sp.y)
        self._draw_line(d, sp.x+wpix, sp.y, sp.x+wpix, sp.y - length)

        self._draw_line(d, sp.x, sp.y+hpix, sp.x - length, sp.y + hpix)
        self._draw_line(d, sp.x, sp.y+hpix, sp.x, sp.y + hpix + length)

        self._draw_line(d, sp.x + wpix, sp.y + hpix, sp.x + wpix + length, sp.y + hpix)
        self._draw_line(d, sp.x + wpix, sp.y + hpix, sp.x + wpix, sp.y + hpix + length)

    def get_size(self):
        return Size(self.length, self.width)


class PositionalObject:
    def __init__(self, obj, pos, options=None):
        """
        :param obj:
        :type obj: Object
        :param pos:
        :type pos: Position
        """
        self._obj = obj
        if not isinstance(pos, Position):
            raise Exception("not Position type")
        self.pos = pos
        self.options = options

    def draw(self, canvas):
        self._obj.draw(canvas, self.pos, **(self.options or {}))

    def is_in_area(self, area_pos, area_size, canvas):
        """
        :param area_pos:
        :type area_pos: Position
        :param area_size:
        :type area_size: Size
        :param canvas:
        :type canvas: Canvas
        :return:
        """
        x0 = self.pos.x
        x1 = self.pos.x + canvas.to_pixels(self._obj.get_size().width)
        y0 = self.pos.y
        y1 = self.pos.y + canvas.to_pixels(self._obj.get_size().height)
        return (
                x0 > area_pos.x
                and x1 < area_pos.x + area_size.width
                and y0 > area_pos.y
                and y1 < area_pos.y + area_size.height
        )


class Draw:
    def draw(self, canvas, objects):
        """
        :param canvas:
        :param objects:
        :type objects: list of PositionalObject
        :return:
        """
        # canvas = None  # TODO: make canvas (PILLOW)
        for obj in objects:
            obj.draw(canvas)

    def draw_wm(self, canvas):
        image = canvas.im
        text = DRAWING_WATERMARK_TEXT

        watermark = Image.new('RGBA', size=image.size, color=0)
        # watermark = Image.new('RGBA', size=(image.width, 64), color=0)
        draw = ImageDraw.Draw(watermark)
        font = get_font(60)
        tw = None
        th = None
        while True:
            tw, th = draw.textsize(text, font=font)
            if tw + 10 < image.size[0] and th + 10 < image.size[1]:
                break
            font = get_font(font.size - 2)

        draw.text(
            (image.width / 2 - tw / 2, image.height / 2 - th / 2),
            text,
            fill=(0, 0, 0, 128),
            font=font
        )

        # image.paste(watermark, box=(0, 15), mask=watermark)
        canvas.im = Image.alpha_composite(image, watermark)
