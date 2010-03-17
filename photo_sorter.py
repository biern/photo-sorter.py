#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2010 Marcin Biernat
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
#   - more optional arguments for filename template
#   - switch and prompt for overriding existing files


import sys
import os
import shutil
from optparse import OptionParser
from datetime import datetime
import time
import pyexiv2

def parse_options():
    parser = OptionParser()
    modes = ('link', 'move', 'update', 'copy', 'dummy')
    parser.add_option("-o", "--output", dest="output",
                    help="Use specified image output directory. If not set"\
                    ", each image's original directory is preserved",
                    metavar="DIRECTORY")
    
    parser.add_option("-v", "--verbose",
                    action="store_true", dest="verbose", default=False,
                    help="Print status messages other than errors to stdout")

    parser.add_option("-p", "--pattern", dest="pattern", default="{n}",
                    help="Specify filename pattern. variables:\n"\
                    " {n} - image number (required).\n "\
                    " Example: -p \"some name {n}\"")

    parser.add_option("-e", "--exif-date", help="Exif's date field name to"\
                    " use in first place")
    
    #Modes. Only one of the following can be choosen
    parser.add_option("-m", "--move", dest="move", action="store_true",
                    default=False,
                    help="Move / rename images. this is the default action")

    parser.add_option("-c", "--copy", dest="copy", action="store_true",
                    default=False,
                    help="Copy images instead of renaming them")

    parser.add_option("-u", "--update", dest="update", action="store_true",
                    default=False,
                    help="Only update system's image access and modification"\
                        " date. Comes handy after modifying (ie. rotating)"\
                        " the photos that are already sorted / named.")

    parser.add_option("-l", "--link", dest="link", action="store_true",
                    default=False,
                    help="Like -m but also creates symbolic links for new"\
                    " images with old one's path and name")

    parser.add_option("-d", "--dummy", dest="dummy", action="store_true",
                    default=False,
                    help="Does not perform any changes, just prints list of"\
                        " sorted files with names and path they would get")

    if(len(sys.argv) == 1):
        parser.print_help()
        exit()
    
    options, img_list = parser.parse_args()
    num_modes = sum([getattr(options or False, name) for name in modes])
    if not num_modes:
        options.move = True

    if num_modes > 1:
        parser.error("only one action from "+ ",".join(modes) + \
            " can be choosen")

    #Create 'mode' option depending on action choosen
    for name in modes:
        if getattr(options, name, False):
            options.mode = name
            break

    result = {'image_list':img_list}
    for k, v in options.__dict__.items():
        if not k in modes:
            result[k] = v

    return result


def process_images(pattern, mode, image_list, output, verbose=False,
        exif_date=None, force=False, **kwargs):
    
    keygetter = lambda key: lambda d: d[key]
    date_fields = ['Exif.Photo.DateTimeOriginal', 'Exif.Image.DateTime']
    photos = []
    if exif_date:
        date_fields.insert(0, exif_date)
    
    if output and not os.path.isdir(output):
        print('ERROR: "{0}" is not a directory'.format(output))
        return False
    
    #Loading images and extracting their data
    for filename in image_list:
        if os.path.isdir(filename):
            print('WARNING: "{0}" is a directory, skipping'.format(filename))
            continue
        try:
            image = pyexiv2.Image(filename)
            image.readMetadata()
        except:
            print('WARNING: Unable to extract image data from "{0}", skipping'\
                .format(filename))
            continue

        for f in date_fields:
            try:
                date = image[f]
                break
            except KeyError:
                if f == exif_date:
                    print("WARNING: Custom exif date field \"{0}\" not found"\
                        "in \"{1}\"".format(exif_date, filename))

        photos.append({'filename':os.path.abspath(filename), 'date':date, 'image':image})
        if not date:
            print('WARNING: Unable to recognize {0} date, skipping'\
                .format(filename))

    # Replacing pattern with more sophisticated one
    l = len(photos)
    min_n_width = str(max(len(str(l)), 4))
    pattern = pattern.replace("{n}","{n:0"+min_n_width+"}")
    #sorting photos according to time taken and filename
    photos = sorted(photos, key=keygetter('filename'))
    photos = sorted(photos, key=keygetter('date'))
    # Initializing vars
    model_mapping = {None:"_"}
    next_model_id = "A"
    for i, p in enumerate(photos):
        src = p['filename']
        img = p['image']
        date = p['date']
        new_name = pattern
        # Formatting pattern. Since 'format' requires all arguments on one call,
        #   use 'replace' instead
        if pattern.find("{model}") >= 0:
            try:
                model = img['Exif.Image.Model']
            except KeyError:
                model = None
            
            try:
                model_id = model_mapping[model]
            except KeyError:
                model_mapping[model] = next_model_id
                model_id = next_model_id
                next_model_id = chr(ord(next_model_id)+1)

            new_name = new_name.replace("{model}", model_id)
        # Call 'format' in the end, since it requires all template vars to be
        #  filled.
        new_name = new_name.format(n=i+1)
        # Creating final output filename
        ext = os.path.splitext(src)[1]
        if ext: new_name += ext.lower()
        if output:
            dest = os.path.abspath(os.path.join(output, new_name))
        else:
            dest = os.path.abspath(os.path.join(os.path.split(src)[0],
                                    new_name))

        #Performing actual changes
        if not os.path.exists(dest):
            if verbose or mode == "dummy":
                if mode == "update":
                    print("updating " + src)
                else:
                    print('"' + src + '" => "' + dest + '"')
            
            if mode in ("move", "link"):
                shutil.move(src, dest)
                if mode == "link":
                    os.symlink(dest, src)
                    
            if mode == "copy":
                shutil.copy(src, dest)

            if mode == "update":
                timestamp = int(time.mktime(date.timetuple()))
                os.utime(src, (timestamp, timestamp))

        else:
            print('ERROR: File {0} already exists, skipping'.format(dest))

    
if __name__ == "__main__":
    options = parse_options()
    process_images(**options)
