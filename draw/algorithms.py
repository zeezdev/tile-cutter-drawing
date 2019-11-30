from math import tanh, sqrt, ceil
import sys
import uuid
import os

# from django.conf import settings
from PIL import Image, ImageDraw

from .core import (
    add_text_watermark, Size, Position, Canvas, Draw,
    WallTilesOptions, PositionalObject, Wall, Floor,
    color, color_cutted,
    LAYING_METHOD_DIRECT, LAYING_METHOD_DIRECT_CENTER, LAYING_METHOD_DIAGONAL,
    DRAWING_WATERMARK_TEXT
)


def check_with_delimiters(l, tl, d, c):
    """ Уточняет необходимое количество плитки
    после добавления межплиточных разделителей.
    Если после добавления межплиточных рсстояний
    суммарная длина больше покрываемой на целую плитку
    + 1 разделитель, то эта плитка не нужна.

    :param l: длина покрываемая плитками (mm).
    :param tl: размер плитки (mm).
    :param d: межплиточное расстояние (mm).
    :param c: количество необходимой плитки без разделителей.
    :return: Уточненное количество необходимой плитки для длины (l).
    """
    count = c
    if ((c * tl) + (d * c-1)) - l >= (tl + d):
        count -= 1

    return count


def add_background(color):
    def decorator(func):
        def wrapper(*args):
            image = func(*args)
            bg = Image.new('RGBA', (image.width, image.height), color)
            bg.paste(image, mask=image)

            return bg
        return wrapper

    return decorator


def draw_floor1(width, length, d, tw, th, method=LAYING_METHOD_DIRECT):
    """X=length, Y=width"""
    draw = Draw()

    WIDTH_HD = 1280
    HEIGHT_HD = 720

    contour_length = length/100.0 * 1.0  # 3% размеры контуров

    # найдем ожидаемые размеры (в мм) которые может занять схема
    max_size = Size(
        width=length + (contour_length * 2),
        height=width + (contour_length * 2)
    )

    print(max_size)

    canvas = Canvas(
        WIDTH_HD, HEIGHT_HD,
        max_size=max_size
    )

    draw_offset = Position(canvas.to_pixels(contour_length), canvas.to_pixels(contour_length))

    options = {
        'contour_out': {
            'length': canvas.to_pixels(contour_length)
        }
    }

    floor = Floor(
        width, length,
        WallTilesOptions(tw, th, d),
        options=options
    )
    draw.draw(
        canvas,
        [PositionalObject(floor, draw_offset, {'method': method})]
    )

    lpx, wpx = (
        canvas.to_pixels(length) + canvas.to_pixels(contour_length * 2),
        canvas.to_pixels(width) + canvas.to_pixels(contour_length * 2)
    )
    canvas.im = canvas.im.crop((0, 0, lpx, wpx))

    sf = lpx / wpx
    if sf <= 16/9:  # 1.777...
        # scale by height
        canvas.im.resize((int(HEIGHT_HD * sf), HEIGHT_HD))
    else:
        # scale by width
        canvas.im.resize((WIDTH_HD, int(WIDTH_HD * sf)))

    im_w, im_h = canvas.im.size
    canvas1 = Canvas(
        WIDTH_HD, HEIGHT_HD,
        scale_factor=1.0
    )
    canvas1.im.paste(
        canvas.im,
        ((WIDTH_HD - im_w) // 2, (HEIGHT_HD - im_h) // 2)
    )

    draw.draw_wm(canvas1)

    return canvas1


# @add_background(color=(255, 255, 255, 255))
@add_text_watermark(DRAWING_WATERMARK_TEXT)
def draw_floor(width, length, tile_width, tile_length, method=LAYING_METHOD_DIRECT):
    """X=length, Y=width
    :param width: width of floor (mm)
    :param length: length of floor (mm)
    :param method: mothod of tile laying.
    :return: PIL.Image
    """
    scale_factor = 9  # TODO: need compute this

    size = (sys.maxsize, sys.maxsize)
    while any(s > 1000 for s in size):
        scale_factor += 1
        size = (int(length/scale_factor), int(width/scale_factor))  # scale 10sm=100mm : 1px.

    tile_size = (int(tile_length/scale_factor), int(tile_width/scale_factor))

    center_x = size[0] / 2
    center_y = size[1] / 2

    image = Image.new('RGBA', size, "#b9cbda")
    draw = ImageDraw.Draw(image)

    line_color = color
    line_width = 1

    if method == LAYING_METHOD_DIRECT:
        # рисуем плитки по length
        curr_x = 0
        while curr_x < size[0]:
            draw.line((curr_x, 0, curr_x, size[1]-1), fill=line_color, width=line_width)
            curr_x += tile_size[0]
        # рисуем плитки по width
        curr_y = 0
        while curr_y < size[1]:
            draw.line((0, curr_y, size[0]-1, curr_y), fill=line_color, width=line_width)
            curr_y += tile_size[1]
    elif method == LAYING_METHOD_DIRECT_CENTER:  # TODO: simplify - start from outside.
        # рисуем полосы по length (x)
        curr_x = size[0]/2 + tile_size[0]/2
        draw.line((curr_x, 0, curr_x, size[1]-1), fill=line_color, width=line_width)
        while curr_x >= 0:
            curr_x -= tile_size[0]
            draw.line((curr_x, 0, curr_x, size[1] - 1), fill=line_color, width=line_width)

        curr_x = size[0]/2 + tile_size[0]/2
        draw.line((curr_x, 0, curr_x, size[1] - 1), fill=line_color, width=line_width)
        while curr_x <= size[0]:
            curr_x += tile_size[0]
            draw.line((curr_x, 0, curr_x, size[1] - 1), fill=line_color, width=line_width)

        # рисуем полосы по width (y)
        curr_y = size[1] / 2 + tile_size[1] / 2
        draw.line((0, curr_y, size[0] - 1, curr_y), fill=line_color, width=line_width)
        while curr_y >= 0:
            curr_y -= tile_size[1]
            draw.line((0, curr_y, size[0] - 1, curr_y), fill=line_color, width=line_width)

        curr_y = size[1] / 2 + tile_size[1] / 2
        draw.line((0, curr_y, size[0] - 1, curr_y), fill=line_color, width=line_width)
        while curr_y <= size[1]:
            curr_y += tile_size[0]
            draw.line((0, curr_y, size[0] - 1, curr_y), fill=line_color, width=line_width)
    elif method == LAYING_METHOD_DIAGONAL:
        # представим наклонную грань плитки гипотенузой прамоугольного треугольника.
        # находим длину прилежащего катета через угол (45) и длину противолежащего.
        b = center_y
        alpha = 45.0
        a = b * tanh(alpha)

        # находим диагональ плитки
        if tile_width == tile_length:
            d = sqrt(2) * tile_width
        else:
            d = sqrt(tile_length**2 + tile_width**2)
        d /= scale_factor
        d05 = d/2

        # находим выступ за границами объекта для начала рисования наклонных линий:
        # сдвигаемся от центра на полплитки + суммарную длину диагоналей целых плиток,
        # добавляем длину прилежащего катета (a).
        m = ((ceil((center_x-d05)/d) * d) + d05) - center_x
        m = -(m+d*2)
        curr_x = m

        while curr_x < size[0] or curr_x-a < size[0]:
            draw.line((curr_x-a, 0, curr_x+a, size[1]-1), fill=line_color, width=line_width)
            draw.line((curr_x + a, 0, curr_x - a, size[1] - 1), fill=line_color, width=line_width)
            curr_x += d

        # curr_x = m
        # while curr_x < size[0] or curr_x - a < size[0]:
        #     draw.line((curr_x + a, 0, curr_x - a, size[1] - 1), fill=line_color, width=line_width)
        #     curr_x += d
    else:
        raise Exception("Unknown drawing method")

    # рисуем периметр
    if method == LAYING_METHOD_DIAGONAL:
        line_color = color_cutted  # весь периметр - гарантировано обрезан
    draw.line((0, 0, size[0] - 1, 0), fill=line_color, width=line_width)
    draw.line((0, size[1] - 1, size[0] - 1, size[1] - 1), fill=line_color, width=line_width)
    draw.line((0, 0, 0, size[1] - 1), fill=line_color, width=line_width)
    draw.line((size[0] - 1, 0, size[0] - 1, size[1] - 1), fill=line_color, width=line_width)

    return image


@add_text_watermark(DRAWING_WATERMARK_TEXT)
def draw_walls(width, length, height, tile_length, tile_height, door_width=None, door_height=None):
    """DEPRECATED: use draw_bathroom instead"""

    scale_factor = 9.0  # TODO: need compute this
    perimetr = (length+width)*2

    size = (sys.maxsize, sys.maxsize)
    while any(s > 1000 for s in size):
        scale_factor += 1.0
        size = (int(perimetr/scale_factor), int(height/scale_factor))  # scale 10sm=100mm : 1px.

    d_length = int(length/scale_factor)
    d_width = int(width/scale_factor)
    d_height = int(height/scale_factor)

    tile_size = (int(tile_length/scale_factor), int(tile_height/scale_factor))

    if door_width and door_height:
        d_door_width = int(door_width/scale_factor)
        d_door_height = int(door_height/scale_factor)

    image = Image.new('RGBA', size, (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)

    # single method
    line_color = (255, 0, 0, 255)
    side_color = (0, 0, 255, 255)
    door_color = (0, 255, 0, 255)
    line_width = 1


    # draw door on the third wall
    if door_width and door_height:
        start_door_x = length + width + length/2 - door_width/2
        d_start_door_x = int(start_door_x/scale_factor)

        draw.rectangle((d_start_door_x, d_height, d_start_door_x + d_door_width, d_height-d_door_height), fill=door_color)

        # draw.line((d_start_door_x, d_height, d_start_door_x, d_height-d_door_height), fill=door_color, width=2)
        # draw.line((d_start_door_x+d_door_width, d_height, d_start_door_x+d_door_width, d_height - d_door_height), fill=door_color, width=2)
        #
        # draw.line((d_start_door_x, d_height-d_door_height, d_start_door_x+d_door_width, d_height - d_door_height), fill=door_color, width=2)
        # draw.line((d_start_door_x, d_height-1, d_start_door_x+d_door_width, d_height-1), fill=door_color, width=2)

        # tile_in_door_x = ceil(start_door_x/tile_length) * tile_length
        # draw.ellipse((tile_in_door_x/scale_factor - 5, d_height - 5, tile_in_door_x/scale_factor + 5, d_height + 5), fill=(255, 45, 33, 255))

    # рисуем контур развертки всех стенок
    draw.line((0, 0, size[0] - 1, 0), fill=line_color, width=line_width)
    draw.line((0, size[1]-1, size[0] - 1, size[1] - 1), fill=line_color, width=line_width)

    draw.line((0, 0, 0, size[1] - 1), fill=line_color, width=line_width)
    draw.line((size[0]-1, 0, size[0] - 1, size[1] - 1), fill=line_color, width=line_width)

    laying_direction_y = -1  # TODO: need to use

    # рисуем плитки по length
    curr_x = 0
    while curr_x < size[0]:
        draw.line((curr_x, 0, curr_x, size[1]-1), fill=line_color, width=line_width)
        curr_x += tile_size[0]

    # рисуем плитки по height
    curr_y = 0
    while curr_y < size[1]:
        draw.line((0, size[1] - curr_y, size[0]-1, size[1] - curr_y), fill=line_color, width=line_width)

        curr_y += tile_size[1]

    # рисуем стыки стен
    draw.line((d_length, 0, d_length, size[1]-1), fill=side_color, width=2)
    draw.line((d_length+d_width, 0, d_length+d_width, size[1] - 1), fill=side_color, width=2)
    draw.line((2*d_length+d_width, 0, 2*d_length+d_width, size[1] - 1), fill=side_color, width=2)

    return image


def draw_bathroom(l, w, h, d, tw, th, door_size=None):
    """ Возможно следует добавить расчет "максимум целых плиток"
    :param l:
    :param w:
    :param h:
    :param d:
    :param tw:
    :param th:
    :return:
    """
    draw = Draw()

    WIDTH_HD = 1280
    HEIGHT_HD = 720

    contour_length = l/100.0 * 3.0  # 3%
    wall_del_px = contour_length * 3  # расстояние между краями схем стен
    padding_px = l/100.0 * 8.0

    # найдем ожидаемые размеры (в мм) которые может занять схема
    max_size = Size(
        width=((w+l)*2) + (wall_del_px * 3) + (padding_px * 2),
        height=h + (contour_length*2)
    )

    print(max_size)

    canvas = Canvas(
        WIDTH_HD, HEIGHT_HD,
        max_size=max_size
    )

    options = {
        'contour_out': {
            'length': canvas.to_pixels(contour_length)
        }
    }

    wall_del_px = canvas.to_pixels(wall_del_px)
    # print("wall del px=", wall_del_px)
    padding_px = canvas.to_pixels(padding_px)
    # print("padding px=", padding_px)

    draw_offset = Position(
        # WIDTH_HD/2 - canvas.to_pixels(max_size.width)/2,
        padding_px,
        HEIGHT_HD/2 - canvas.to_pixels(max_size.height)/2
    )

    # print(canvas.to_pixels(max_size.width) + padding_px)

    wall = Wall(l, h, tile=WallTilesOptions(tw, th, d, sx=None), options=options)
    draw.draw(canvas, [PositionalObject(wall, draw_offset)])
    wo = wall.get_tile_options()
    # print("Wall#1:\n\tsx={} sy={} mx={} my={}".format(wo.start_x, wo.start_y, wo.max_x, wo.max_y))

    tile_start_from_x = wall.get_tile_options().max_x
    draw_offset.x += canvas.to_pixels(wall.width) + wall_del_px
    wall = Wall(w, h, tile=WallTilesOptions(tw, th, d, sx=tile_start_from_x), options=options)
    draw.draw(canvas, [PositionalObject(wall, draw_offset)])
    wo = wall.get_tile_options()
    # print("Wall#2:\n\tsx={} sy={} mx={} my={}".format(wo.start_x, wo.start_y, wo.max_x, wo.max_y))

    tile_start_from_x = wall.get_tile_options().max_x
    draw_offset.x += canvas.to_pixels(wall.width) + wall_del_px
    if door_size is not None:
        options['door_width'] = door_size.width
        options['door_height'] = door_size.height
    wall = Wall(l, h, tile=WallTilesOptions(tw, th, d, sx=tile_start_from_x), options=options)
    draw.draw(canvas, [PositionalObject(wall, draw_offset)])
    wo = wall.get_tile_options()
    # print("Wall#3:\n\tsx={} sy={} mx={} my={}".format(wo.start_x, wo.start_y, wo.max_x, wo.max_y))

    tile_start_from_x = wall.get_tile_options().max_x
    draw_offset.x += canvas.to_pixels(wall.width) + wall_del_px
    options['door_width'] = None
    options['door_height'] = None
    wall = Wall(w, h, tile=WallTilesOptions(tw, th, d, sx=tile_start_from_x), options=options)
    draw.draw(canvas, [PositionalObject(wall, draw_offset)])
    wo = wall.get_tile_options()
    # print("Wall#4:\n\tsx={} sy={} mx={} my={}".format(wo.start_x, wo.start_y, wo.max_x, wo.max_y))

    # FIXME: little hack!!!
    real_width = draw_offset.x + canvas.to_pixels(wall.width) + padding_px
    if real_width < max_size.width:
        canvas.im = canvas.im.crop((0, 0, real_width, HEIGHT_HD))
    canvas.im.resize((WIDTH_HD, HEIGHT_HD))

    # print(real_width)

    draw.draw_wm(canvas)

    return canvas


def calc_cost(count, price):
    """Вычисляет необходимую стоимость простым умножением.
    Точность 2 знака.
    :param count:
    :param price: price of one tile.
    :return:
    """
    return round(count * price, 2)
