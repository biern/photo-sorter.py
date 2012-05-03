#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright 2012 Marcin Biernat
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# TODOS:
#   - Readme and docs
#   - switch and prompt for overriding existing files
#     (interactive mode)
#   - checking if selected file is an image.


import codecs
import pyexiv2
import logging
import argparse
import os
import time
import shutil


log = logging


def parse_options():
    def directory_type(string):
        if not os.path.isdir(string):
            raise argparse.ArgumentTypeError(
                u'"{0}" is not a directory'.format(options.output))

        return string

    parser = argparse.ArgumentParser()
    parser.add_argument('image_list', metavar='IMAGE', nargs='+',
                        help='images list')
    parser.add_argument("-o", "--output", dest="output", type=directory_type,
                        help="Use specified image output directory. If not set"
                            ", each image's original directory is preserved",
                        metavar="DIRECTORY")

    parser.add_argument("-v", "--verbose", action="count",
                        dest="verbose", default=0,
                        help="Print status messages other than "
                        "errors to stdout")

    parser.add_argument("-p", "--pattern", dest="pattern", default="{n}",
                        help="Specify filename pattern. variables:\n"\
                            " {n} - image number.\n "\
                            " {model} - camera model id "\
                            " Example: -p \"some name {n}{model}\"")

    parser.add_argument("-e", "--exif-date-field",
                        help="Exif's date field name to"
                        " use in first place")

    # Modes. Only one of the following can be choosen
    parser.add_argument("-m", "--move", dest="mode", action="store_const",
                        const="move",
                        help="Move / rename images. "
                        "this is the default action")

    parser.add_argument("-c", "--copy", dest="mode", action="store_const",
                        const="copy",
                        help="Copy images instead of renaming them")

    parser.add_argument("-u", "--update", dest="mode", action="store_const",
                        const="update",
                        help="Update system's image access and modification"\
                            " time to when the photo was taken. Comes handy"\
                            " after modifying (ie. rotating)"\
                            " photos that are already sorted / named."\
                            " Can also be used in conjuction "
                            "with other actions")

    parser.add_argument("-l", "--link", dest="mode", action="store_const",
                        const="link",
                        help="Like -m but also creates symbolic links for new"\
                            " images with old one's path and name")

    parser.add_argument("-d", "--dummy", dest="mode", action="store_const",
                        const="dummy",
                        help="Does not perform any changes,"
                        "just prints list of "
                        " sorted files with names and path they would get")

    options = parser.parse_args()
    options.image_list = \
        [codecs.decode(path, 'utf-8') for path in options.image_list]

    options.mode = options.mode or 'move'
    return options


def analize_photos(paths, exif_date_field=None):
    date_fields = ['Exif.Photo.DateTimeOriginal', 'Exif.Image.DateTime']
    photos = []
    if exif_date_field:
        date_fields.insert(0, exif_date_field)

    # Loading images and extracting their data
    for filename in paths:
        if os.path.isdir(filename):
            log.warning(u'"{0}" is a directory, skipping'.format(filename))
            continue
        try:
            data = pyexiv2.metadata.ImageMetadata(filename)
            data.read()
        except:
            log.warning(u'Unable to extract image data from "{0}", skipping'
                        .format(filename))
            continue

        for f in date_fields:
            try:
                date = data[f].value
                break
            except KeyError:
                if f == exif_date_field:
                    log.warning(u'Custom exif date field "{0}" not found'
                                'in "{1}"'.format(exif_date_field, filename))

        photos.append({
            'filename': os.path.abspath(filename),
            'date': date,
            'data': data
            })

        if not date:
            log.warning(u'Unable to recognize {0} date, skipping'\
                            .format(filename))

    return sorted(photos, key=lambda p: (p['date'], p['filename']))


def calc_destinations(pattern, output, photos):
    model_mapping = {None: "_"}

    def do_model(name, photo):
        if '{model}' not in name:
            return name

        try:
            model = photo['data']['Exif.Image.Model']
        except KeyError:
            model = None

        try:
            model_id = model_mapping[model]
        except KeyError:
            ids = sorted(model_mapping.values())
            ids.remove('_')
            model_id = 'A' if not len(ids) else chr(ord(ids[-1]) + 1)
            model_mapping[model] = model_id

        return name.replace('{model}', model_id)

    if '{n}' not in pattern:
        pattern += ' {n}'

    # Generating 'n' width
    l = len(photos)
    min_n_width = str(max(len(str(l)), 4))
    pattern = pattern.replace('{n}', '{n:0' + min_n_width + '}')

    # Performing desired operation on each of selected images
    for i, photo in enumerate(photos):
        src = photo['filename']
        name = pattern
        name = do_model(name, photo)
        name = name.format(n=i + 1)

        # Creating final output filename
        ext = os.path.splitext(src)[1]
        if ext:
            name += ext.lower()

        if output:
            dest = os.path.abspath(os.path.join(output, name))
        else:
            dest = os.path.abspath(
                os.path.join(os.path.split(src)[0], name))

        photo['dest'] = dest


def perform_operations(mode, update_time, photos):
    for photo in photos:
        src = photo['filename']
        dest = photo['dest']
        date = photo['date']

        if os.path.exists(dest):
            log.warning(u'File {0} already exists, skipping'.format(dest))
            continue

        if not mode and update_time:
            log.info(u'updating {0}'.format(src))
        else:
            log.info(u'"{0}" => "{1}"'.format(src, dest))

        if mode != "dummy":
            if mode in ("move", "link"):
                shutil.move(src, dest)
                if mode == "link":
                    os.symlink(dest, src)

            if mode == "copy":
                shutil.copy(src, dest)

            if update_time:
                f = dest if mode else src
                timestamp = int(time.mktime(date.timetuple()))
                os.utime(f, (timestamp, timestamp))


def process_images(pattern, mode, image_list, output, verbose=False,
                   exif_date_field=None, update=False):
    photos = analize_photos(image_list, exif_date_field)
    calc_destinations(pattern, output, photos)
    perform_operations(mode, update, photos)


def config_logging(level):
    logging.basicConfig(level=level)


if __name__ == "__main__":
    options = parse_options()
    config_logging(level=(30 - 10 * options.verbose or 0))
    process_images(**vars(options))
