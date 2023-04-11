#!/usr/bin/env python

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
LOG_FILE = f"{BASE_NAME}.log"
CFG_FILE = f"{BASE_NAME}.cfg"
OS = platform.system()

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

# Setting up and reading the configuration file
# Note: all default variables should be in this file
# and also optionally some operation specific variables
config = configparser.ConfigParser()
config.read(CFG_FILE)

# Setting the commandline arguments of the script
parser = argparse.ArgumentParser(description="Move files from one directory to another")
parser.add_argument("-v", "--verbose", action="store_true", help="Run in verbose mode")
parser.add_argument("-d", "--debug", action="store_true", help="Run in debug mode")
parser.add_argument(
    "-c", "--section", action="store", default="DEFAULT", help="Which section to use"
)

args = parser.parse_args()


def md5(file_name):
    """
    Calculating the input file MD5

    Args:
        file_name (str): the filename to calculate its md5sum

    Return:
        hex : the file md5sum results
    """
    if not os.path.exists(file_name):
        print(f"The file '{file_name}' does not exists !")
        return None

    hash_md5 = hashlib.md5()
    with open(file_name, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def make_connection(op="connect"):
    """
    Mounting shared filesystem on Drive/MountPoint

    Args:
        op (str): which operation to use connect / disconnect

    Return:
        bool : does the command succeed or not
    """

    if not config[args.section]["connect"]:
        print("No Connection / Disconnecting is needed !")
        return True

    extra = "/d" if op == "disconnect" else ""
    if extra != "":
        share = ""
    else:
        share = config[args.section]["share"]

    if OS == "Windows":
        net_cmd = "C:/Windows/System32/net.exe"
        cmd = f"{net_cmd} use {extra} {config[args.section]['target_drive']} {share}"
    else:
        cmd = f"mount -t nfs {config[args.section]['target_drive']} {share}"
        if op == "disconnect":
            cmd = f"umount {config[args.section]['target_drive']}"

    return os.system(cmd) == 0


def quit_prog():
    log.info("Operation finished")
    make_connection(op="disconnect")
    log.info(
        f"Finished moving of {config[args.section]['batch_size']} "
        f"from {config[args.section]['source_path']} to {config[args.section]['target_path']} at {time.ctime()}"
    )
    print(
        f"Finished moving of {config[args.section]['batch_size']} "
        f"from {config[args.section]['source_path']} to {config[args.section]['target_path']} at {time.ctime()}"
    )
    exit()


def move_files(source_dir, target_dir):
    global total_files

    all_files = os.listdir(source_dir)

    for f in all_files:
        # For debugging purpose
        total_files += 1
        # print (f"{total_files}")
        print(".", end="", flush=True)
        if int(config[args.section]["batch_size"]) > 0:
            if total_files > int(config[args.section]["batch_size"]):
                quit_prog()

        src = os.path.join(source_dir, f)
        trg = os.path.join(target_dir, f)
        OK = True
        if os.path.isdir(src):
            print("", flush=True)
            try:
                os.mkdir(trg)
            except FileExistsError:
                pass
            log.info(f"{src} is a Directory, The Target is {trg}")
            move_files(src, trg)
            if len(os.listdir(src)) == 0:
                log.info(f"Source dir : {src} is empty. Delete it...")
                try:
                    os.rmdir(src)
                except Exception as ex:
                    print(f"can not delete directory - {ex}")
                    log.info(f"Delete of Directory {src} Failed - {ex}")
            else:
                log.info(f"Not all files in the directory {src} was deleted !")

        else:
            log.info(f"Copying the file {src} to {trg}")
            try:
                shutil.copy2(src, trg)
                src_md5 = md5(src)
                trg_md5 = md5(trg)
                if src_md5 != trg_md5:
                    OK = False
                if OK:
                    try:
                        log.info(f"Deleting {src}")
                        os.remove(src)
                    except Exception as ose:
                        log.error(f"Deleting of source file {src} Failed - {ose}!")
            except Exception as e:
                log.error(f"Copy of {src} failed - {e}")


if __name__ == "__main__":

    # Verify that all variables are defined.
    config_ok = True
    args.section = args.section.upper()

    try:
        int(config[args.section]["batch_size"])
    except Exception as e:
        print(f"Error : 'batch_size' must be Integer ! [{e}]")
        config_ok = False

    # Check the source & target paths
    for sub_key in ["source", "target"]:
        if not config.has_option(args.section, f"{sub_key}_path"):
            print(f"Error : The value of '{sub_key}_path' is missing !")
            config_ok = False
        elif config[args.section][f"{sub_key}_path"] == "":
            print(f"Error : The value of '{sub_key}_path' cannot be empty !")
            config_ok = False

    # Check if mount is needed
    if config.has_option(args.section, "connect"):
        if config[args.section]["connect"].lower() == "true":
            for key in ["target_drive", "share"]:
                if config[args.section][key]:
                    if not config.has_option(args.section, key):
                        print(f"Error : The value of '{key}' is missing !")
                        config_ok = False
                    elif config[args.section][key]:
                        print(f"Error : The value of '{key}' cannot be empty !")
                        config_ok = False

    if not config_ok:
        sys.exit(1)

    if args.verbose:
        print("Starting the script")
    log.info("Starting the script")

    if args.debug:
        print(
            f"The List of sections in the configuration file is : {config.sections()}"
        )
        print(f"Going to use {args.section} as the variables values :")
        for key in config[args.section]:
            print(f"  {key} = {config[args.section][key]}")

    # Connecting the target path to the system - if needed
    if not make_connection():
        print("Cannot connect the target share to the system - Exiting !!!")
        sys.exit(1)

    move_files(config[args.section]["source_path"], config[args.section]["target_path"])

    # Dis-connecting the target path from the system - if needed
    if not make_connection(op="disconnect"):
        print("Cannot disconnect the target share from the system")
        print("You need to disconnect it manually !!!")

    if args.verbose:
        print("Ending the script")
    log.info("Ending the script")
