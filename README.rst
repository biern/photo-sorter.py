About
=====

Python script for sorting and renaming / copying / updating date of
photos according to factors like time taken and camera model.

Installation
============

- requires python 2.7 or higher

::

        sudo python setup.py install

Examples:
=========

* Renaming photos ( -m --move)

::

        photo_sorter.py * -mp "name - {n}{model}" -o "../output_dir"
        photo_sorter.py * -p "name" # -m is default option and can be ommited
                                    # " {n}" is appended automatically if not found
                                    # -o defaults to each photo's own directory

* Seeing what changes would be done without performing them ( -d --dummy) ::

       photo_sorter.py -dp "photo - {n}{model}" *.png ../others/*

* Copying photos ( -c --copy) ::

       photo_sorter.py -c "name" * # works just like -m

* Updating photos date ( -u --update)
    This updates os' file modification time to that when the photo was taken.
    Note that -u can be combined with `-c` and `-m` ::

       photo_sorter.py -u *

* For full reference run ::

       photo-sorter.py --help


Copyright © 2012 Marcin Biernat <mb@marcinbiernat.pl>. Licensed under the GPLv3
