# move_files

This script is moving files from one path to another recursively.

It also verified (using md5sum) that the files moved correctly.

It uses a configuration file, with the DEFAULT section, and new sections can be added with
all or some of the variables in it, if the variable is not exist in the selected section
 it will be copied from the DEFAULT one.

## Before running

* Clone this repo to your host.
* Change to the script directory
* Update the configuration file with your variables

## Running

#### Notes:
The Script and the configuration file, must be in the same directory.

The Log file will be in this directory as well.

Run the script from its directory:

to use the default values:

        ./move_files.py

or, to use a different section in the configuration file:

        ./move_files.py --sec <section_name>

