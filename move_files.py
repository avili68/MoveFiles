#!/usr/bin/env python
from __future__ import print_function

# Builtin modules
import argparse
import configparser
import hashlib
import logging
import os
import platform
import shutil
import sys
import time

# 3ed party modules

# Local modules

# Some global constants
BASE_NAME = "move_files"
LOG_FILE = "{}.log".format(BASE_NAME)
CFG_FILE = "{}.cfg".format(BASE_NAME)
OS = platform.system()

SHARE_TYPES = ["source", "target"]

# Some global variables
total_files = 0

# Setting up the log file
log = logging.getLogger()
logging.basicConfig(
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
    filename=LOG_FILE,
)

# Setting the commandline arguments of the script
parser = argparse.ArgumentParser(description="Move files from one directory to another")
parser.add_argument("-v", "--verbose", action="store_true", help="Run in verbose mode")
parser.add_argument("-d", "--debug", action="store_true", help="Run in debug mode")
parser.add_argument(
    "-c", "--section", action="store", default="DEFAULT", help="Which section to use"
)
parser.add_argument(
    "--config", action="store", default=CFG_FILE, help="Use this configuration file"
)

args = parser.parse_args()

# Setting up and reading the configuration file
# Note: all default variables should be in this file
# and also optionally some operation specific variables
config = configparser.ConfigParser()
print(args.config)

print(f"Try to read configuration file : {args.config}")
dataset = config.read(args.config)
if not dataset:
    print("Cannot read configuration file")

print(dataset)
print(config["DEFAULT"])
for key in config["DEFAULT"]:
    print(f"{key} : {config['DEFAULT'][key]}")


def combine_args():
    """
    This function combine the configuration file arguments with cli args
    """
    pass


def md5(file_name):
    """
    Calculating the input file MD5

    Args:
        file_name (str): the filename to calculate its md5sum

    Return:
        hex : the file md5sum results
    """
    if not os.path.exists(file_name):
        print("The file '{}' does not exists !".format(file_name))
        return None

    hash_md5 = hashlib.md5()
    with open(file_name, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def make_connection(op="connect", share_type: str = "source"):
    """
    Mounting shared filesystem on Drive/MountPoint

    Args:
        op (str): which operation to use connect / disconnect
        share_type (str): the type of the share to connect/disconnect - source / target
    Return:
        bool : does the command succeed or not
    """

    if not config[args.section]["connect_{}".format(share_type)]:
        print("No Connection / Disconnecting is needed !")
        return True

    extra = "/d" if op == "disconnect" else ""

    # connection
    if extra != "":
        share = ""
    # disconnection
    else:
        share = config[args.section]["{}_share".format(share_type)]

    if OS == "Windows":
        net_cmd = "C:/Windows/System32/net.exe"
        cmd = "{} use {} {} {}".format(
            net_cmd, extra, config[args.section]["{}_drive".format(share_type)], share
        )
    else:
        cmd = "mount -t nfs {} {}".format(
            config[args.section]["{}_drive".format(share_type)], share
        )
        if op == "disconnect":
            cmd = "umount {}".format(
                config[args.section]["{}_drive".format(share_type)]
            )

    return os.system(cmd) == 0


def quit_prog():
    log.info("Operation finished")
    for share_type in SHARE_TYPES:
        make_connection(op="disconnect", share_type=share_type)

    log.info(
        "Finished moving of {} ".format(config[args.section]["batch_size"]),
        "from {} to {} at {}".format(
            config[args.section]["source_path"],
            config[args.section]["target_path"],
            time.ctime(),
        ),
    )
    print(
        "Finished moving of {} ".format(config[args.section]["batch_size"]),
        "from {} to {} at {}".format(
            config[args.section]["source_path"],
            config[args.section]["target_path"],
            time.ctime(),
        ),
    )
    exit()


def move_files(source_dir, target_dir):
    global total_files

    all_files = os.listdir(source_dir)

    for f in all_files:
        total_files += 1
        print(".", end="", flush=True)
        if int(config[args.section]["batch_size"]) > 0:
            if total_files > int(config[args.section]["batch_size"]):
                quit_prog()

        src = os.path.join(source_dir, f)
        trg = os.path.join(target_dir, f)
        ok = True
        if os.path.isdir(src):
            print(total_files, flush=True)
            try:
                os.mkdir(trg)
            except FileExistsError:
                pass
            log.info("{} is a Directory, The Target is {}".format(src, trg))
            move_files(src, trg)
            if len(os.listdir(src)) == 0:
                log.info("Source dir : {} is empty. Delete it...".format(src))
                try:
                    os.rmdir(src)
                except Exception as ex:
                    print("can not delete directory - {}".format(ex))
                    log.info("Delete of Directory {} Failed - {}".format(src, ex))
            else:
                log.info("Not all files in the directory {} was deleted !".format(src))

        else:
            log.info("Copying the file {} to {}".format(src, trg))
            try:
                shutil.copy2(src, trg)
                src_md5 = md5(src)
                trg_md5 = md5(trg)
                if src_md5 != trg_md5:
                    ok = False
                if ok:
                    try:
                        log.info("Deleting {}".format(src))
                        os.remove(src)
                    except Exception as ose:
                        log.error(
                            "Deleting of source file {} Failed - {}!".format(src, ose)
                        )
            except Exception as ex:
                log.error("Copy of {} failed - {}".format(src, ex))


if __name__ == "__main__":

    # Verify that all variables are defined.
    config_ok = True
    args.section = args.section.upper()

    try:
        int(config[args.section]["batch_size"])
    except Exception as e:
        print("Error : 'batch_size' must be Integer ! [{}]".format(e))
        config_ok = False

    # Check the source & target paths
    for sub_key in SHARE_TYPES:
        if not config.has_option(args.section, "{}_path".format(sub_key)):
            print("Error : The value of '{}_path' is missing !".format(sub_key))
            config_ok = False
        elif config[args.section]["{}_path".format(sub_key)] == "":
            print("Error : The value of '{}_path' cannot be empty !".format(sub_key))
            config_ok = False

    # Check if mount is needed
    for sub_key in SHARE_TYPES:
        if config.has_option(args.section, "connect_{}".format(sub_key)):
            if config[args.section]["connect_{}".format(sub_key)].lower() == "true":
                for key in ["target_drive", "share"]:
                    if config[args.section][key]:
                        if not config.has_option(args.section, key):
                            print("Error : The value of '{}' is missing !".format(key))
                            config_ok = False
                        elif config[args.section][key]:
                            print(
                                "Error : The value of '{}' cannot be empty !".format(
                                    key
                                )
                            )
                            config_ok = False

    if not config_ok:
        sys.exit(1)

    if args.verbose:
        print("Starting the script")
    log.info("Starting the script")

    if args.debug:
        print(
            "The List of sections in the configuration file is : {}".format(
                config.sections()
            )
        )
        print("Going to use {} as the variables values :".format(args.section))
        for key in config[args.section]:
            print("  {} = {}".format(key, config[args.section][key]))

    # Connecting the target path to the system - if needed
    if not make_connection():
        print("Cannot connect the target share to the system - Exiting !!!")
        sys.exit(1)

    move_files(config[args.section]["source_path"], config[args.section]["target_path"])

    # Dis-connecting the target path from the system - if needed
    for sub_key in SHARE_TYPES:
        if not make_connection(op="disconnect", share_type=sub_key):
            print("Cannot disconnect the {} share from the system".format(sub_key))
            print("You need to disconnect it manually !!!")

    if args.verbose:
        print("Ending the script")
    log.info("Ending the script")
