# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 RhyCynn
#
# SPDX-License-Identifier: MIT
# --------------------------------------------------------------------------------------------------

"""common functions."""

from collections import OrderedDict
from json import dump, load
from time import localtime, strftime

from ruamel.yaml import YAML


# --------------------------------------------------------------------------------------------------
def load_json_file(file_name=None, ordered=False):
    """this loads a dict from a json file."""

    with open(str(file_name), "r") as input_file:
        if not ordered:
            data_dict = load(input_file)
        else:
            data_dict = load(input_file, object_pairs_hook=OrderedDict)

    return data_dict


# --------------------------------------------------------------------------------------------------
def dump_json_file(file_name=None, data_dict=None, sort_keys=False):
    """this dumps a dict to a json file."""

    with open(str(file_name), "w", encoding="utf-8") as output_file:
        dump(obj=data_dict, fp=output_file, sort_keys=sort_keys, indent=4)


# --------------------------------------------------------------------------------------------------
def load_yaml_file(yaml_file):
    """this loads a dict from a yaml file."""

    yaml = YAML(typ="safe")

    with open(str(yaml_file), "r") as input_file:
        data_dict = yaml.load(input_file)

    return data_dict


# --------------------------------------------------------------------------------------------------
def dump_yaml_file(yaml_file, data_dict):
    """this dumps a dict to a yaml file."""

    yaml = YAML()

    with open(str(yaml_file), "w", encoding="utf-8") as output_file:
        yaml.dump(data_dict, output_file)


# --------------------------------------------------------------------------------------------------
# def generate_asset_filenames(source_paths: list):
#     """this recursively generates a dict of file names from a list of paths."""

#     # ----------------------------------------------------------------------------------------------
#     def generate_asset_filenames_scandir(source_path=None):
#         # is_dir can fail with a permission error
#         try:
#             with os.scandir(source_path) as entries:
#                 for entry in entries:
#                     if entry.is_dir(follow_symlinks=False):
#                         generate_asset_filenames_scandir(source_path=entry.path)

#                     else:
#                         name, extension = os.path.splitext(entry.name)
#                         config.asset_filenames[name.lower()] = entry.path.lower()

#         except PermissionError:
#             pass
#         except Exception as e_error:
#             print("An Fatal exception occurred generating the assets file name list")
#             print(e_error)
#             sys.exit(1)

#     # ----------------------------------------------------------------------------------------------
#     for source_path in source_paths:
#         generate_asset_filenames_scandir(source_path=source_path)


# ------------------------------------------------------------------------------------------------------------
def timestamp_log_file(log_file=None, timestamp_format="%Y-%m-%d_%H-%M-%S"):
    """this adds a timestamp prefix to a file name."""

    return log_file.parent / f"{strftime(timestamp_format, localtime())}_{log_file.name}"
