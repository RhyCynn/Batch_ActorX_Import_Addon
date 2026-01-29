# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 RhyCynn
#
# SPDX-License-Identifier: MIT
# --------------------------------------------------------------------------------------------------

from collections import OrderedDict
from dataclasses import dataclass
from json import load
from pathlib import Path
from typing import ClassVar

from bpy.types import Context, Scene


# --------------------------------------------------------------------------------------------------
class MissingImportFileName(Exception):
    pass


# --------------------------------------------------------------------------------------------------
class MatFileReadError(Exception):
    pass


# --------------------------------------------------------------------------------------------------
def hex_to_rgba(hex_color: str):
    """this changes a hex color to an rgba color for node sockets."""

    hex_color = hex_color[1:]
    if len(hex_color) not in [6, 8]:
        return

    srgba_red = int(hex_color[0:2], base=16) / 255
    srgba_green = int(hex_color[2:4], base=16) / 255
    srgba_blue = int(hex_color[4:6], base=16) / 255

    if len(hex_color) == 8:
        srgba_alpha = int(hex_color[6:8], base=16) / 255
    else:
        srgba_alpha = None

    if len(hex_color) == 6:
        srgba_color = tuple([srgba_red, srgba_green, srgba_blue])
    else:
        srgba_color = tuple([srgba_red, srgba_green, srgba_blue, srgba_alpha])

    return srgba_color


# --------------------------------------------------------------------------------------------------
def set_defaults(driver, template_key):
    """this loads the default settings for a driver from a json file."""

    defaults = Configuration.driver_template[template_key]
    # print()
    # print(template_key)

    for key, value in defaults.items():
        # print(key, value)
        setattr(driver, key, value)


# --------------------------------------------------------------------------------------------------
def update_parent_name(self, context):
    """this updates the static parent name from the dropdown. it is required due to getting the
    wrong value directly from the dropdown when the last model in the list is not selected."""

    self.parent_name = self.parent_model


# --------------------------------------------------------------------------------------------------
def get_actorx_models(context: Context, scene: Scene):
    """this sets the parent model enum to a static list as the nodes do not need to get a list."""

    parent_model = [("no_parent", "No Parent", "")]

    return parent_model


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
@dataclass
class Configuration:
    """this is a 'global' configuration that loads common settings used by different
    parts of the addon."""

    # used by the various axis enum properties
    axis_list = [
        ("X", "X", "X"),
        ("-X", "-X", "-X"),
        ("Y", "Y", "Y"),
        ("-Y", "-Y", "-Y"),
        ("Z", "Z", "Z"),
        ("-Z", "-Z", "-Z"),
    ]

    script_path: Path = Path(__file__).resolve().parent.parent
    configuration_path: Path = script_path / "configuration"

    # definitions and enum property settings for linking armatures by pose bones
    armature_links: ClassVar[dict] = {}
    parent_link: ClassVar[list] = [("no_link", "No Link", "")]

    # list of texture maps
    asset_filenames: ClassVar[dict] = {}

    # folder that contains import driver dumps
    user_drivers: Path = script_path / "user_drivers"

    # user preferences
    user_settings: ClassVar[dict] = {}

    # action filters
    action_filters: ClassVar[dict] = {}

    # ----------------------------------------------------------------------------------------------
    @classmethod
    def load_configuration(cls):
        # default settings for each property group
        cls.driver_template = load_json_file(cls.configuration_path / "driver_template.json")

        # blender object name prefixes
        cls.prefixes = load_json_file(cls.configuration_path / "prefixes.json")

        # armature linking definitions
        cls.armature_links = load_json_file(cls.configuration_path / "armature_links.json")

        for link_id, link_settings in cls.armature_links.items():
            cls.parent_link.append((link_id, link_settings["name"], link_settings["description"]))

        # user preferences
        cls.user_settings = load_json_file(cls.configuration_path / "user_settings.json")

        # blender object name prefixes
        cls.action_filters = load_json_file(cls.configuration_path / "action_filters.json")
