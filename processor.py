# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 RhyCynn
#
# SPDX-License-Identifier: MIT
# --------------------------------------------------------------------------------------------------

import bpy
from bpy.types import Context

from .core.core import Configuration as config
from .core.core import MissingImportFileName
from .core.logging import Echo
from .engine.common import (
    dump_json_file,
    dump_yaml_file,
    timestamp_log_file,
)
from .engine.processor import walk_import_dict

echo = Echo()

"""convert the node properties to an import driver dict."""


# --------------------------------------------------------------------------------------------------
# def dump_asset_paths(driver_object):
#     asset_folders = []
#     for asset_folder in driver_object.asset_folder_list:
#         list_item = {
#             key: getattr(asset_folder, key)
#             for key in asset_folder.bl_rna.properties.keys()
#             if key not in ["name", "rna_type"]
#         }
#         asset_folders.append(list_item)
#     return asset_folders


# --------------------------------------------------------------------------------------------------
def walk_import_nodes(context: Context, source_repr: str):
    """traverse the nodes and import the files."""

    # ----------------------------------------------------------------------------------------------
    def walk_animation_node(animation_socket, model_item):
        """process an animation node. chained nodes are processed recursively."""

        animation_node = animation_socket.links[0].from_node
        ax_animation_props = animation_node.ax_animation_props

        if not ax_animation_props["file_path"]:
            echo.message("No filename was set for the animation node", leading_line=True)
            echo.message("Aborting Import", leading_line=True)
            raise MissingImportFileName

        animation_item = {
            key: getattr(ax_animation_props, key)
            for key in ax_animation_props.keys()
            if key
            not in [
                "bl_rna",
                "rna_type",
                "name",
            ]
        }
        model_item["animation_list"].append(animation_item)

        if (
            animation_socket := animation_node.inputs.get("animation_socket")
        ) and animation_socket.is_linked:
            walk_animation_node(animation_socket, model_item)

    # ----------------------------------------------------------------------------------------------
    def walk_mesh_node(mesh_socket, model_item, import_drivers):
        """process a mesh node. chained nodes are processed recursively."""

        mesh_node = mesh_socket.links[0].from_node
        ax_mesh_props = mesh_node.ax_mesh_props

        # if no filename was set then brute force exit the script
        if not ax_mesh_props["file_path"]:
            echo.message("No filename was set for the mesh node", leading_line=True)
            echo.message("Aborting Import", leading_line=True)
            raise MissingImportFileName

        mesh_item = {
            key: getattr(ax_mesh_props, key)
            for key in ax_mesh_props.keys()
            if key
            not in [
                "bl_rna",
                "rna_type",
                "name",
                "ueviewer_mat",
                "diffuse_map",
                "specular_map",
                "normal_map",
            ]
        }

        mesh_item["ueviewer_mat"] = {k: v for k, v in ax_mesh_props["ueviewer_mat"].items()}
        mesh_item["texture_path"] = {k: v for k, v in ax_mesh_props["texture_path"].items()}
        mesh_item["diffuse_map"] = {k: v for k, v in ax_mesh_props["diffuse_map"].items()}
        mesh_item["specular_map"] = {k: v for k, v in ax_mesh_props["specular_map"].items()}
        mesh_item["normal_map"] = {k: v for k, v in ax_mesh_props["normal_map"].items()}

        if model_item:
            model_item["mesh_list"].append(mesh_item)
        else:
            import_drivers["mesh_list"].append(mesh_item)

        if (mesh_socket := mesh_node.inputs.get("mesh_socket")) and mesh_socket.is_linked:
            walk_mesh_node(mesh_socket, model_item, import_drivers)

    # ----------------------------------------------------------------------------------------------
    def walk_model_node(model_socket, import_drivers, parent=None):
        """process a model node. chained nodes are processed recursively."""

        model_node = model_socket.links[0].from_node

        ax_model_props = model_node.ax_model_props

        # if no filename was set then brute force exit the script
        if not ax_model_props["file_path"]:
            echo.message("No filename was set for the model node", leading_line=True)
            echo.message("Aborting Import", leading_line=True)
            raise MissingImportFileName

        model_item = {
            key: getattr(ax_model_props, key)
            for key in ax_model_props.keys()
            if key
            not in [
                "bl_rna",
                "rna_type",
                "name",
                "ueviewer_mat",
                "diffuse_map",
                "specular_map",
                "normal_map",
            ]
        }

        if parent:
            model_item["parent_name"] = parent["ax_model_props"]["display_name"]
            model_item["parent_model"] = parent["ax_model_props"]["display_name"]

        model_item["ueviewer_mat"] = {k: v for k, v in ax_model_props["ueviewer_mat"].items()}
        model_item["texture_path"] = {k: v for k, v in ax_model_props["texture_path"].items()}
        model_item["diffuse_map"] = {k: v for k, v in ax_model_props["diffuse_map"].items()}
        model_item["specular_map"] = {k: v for k, v in ax_model_props["specular_map"].items()}
        model_item["normal_map"] = {k: v for k, v in ax_model_props["normal_map"].items()}

        import_drivers["model_list"].append(model_item)

        model_item["mesh_list"] = []

        if (mesh_socket := model_node.inputs.get("mesh_socket")) and mesh_socket.is_linked:
            walk_mesh_node(mesh_socket, model_item, None)

        model_item["animation_list"] = []

        animation_sockets = [
            x for x in model_node.inputs if x.is_linked and x.name == "animation_socket"
        ]

        for animation_socket in animation_sockets:
            walk_animation_node(animation_socket, model_item)

        if (
            child_model_socket := model_node.inputs.get("model_socket")
        ) and child_model_socket.is_linked:
            walk_model_node(child_model_socket, import_drivers, parent=model_node)

    # ----------------------------------------------------------------------------------------------
    def walk_tree(actorx_import_node):
        """process all linked model sockets on the import node."""

        import_drivers = {}

        model_sockets = [
            x for x in actorx_import_node.inputs if x.is_linked and x.name == "model_socket"
        ]

        import_drivers["model_list"] = []

        for model_socket in model_sockets:
            walk_model_node(model_socket, import_drivers)

        mesh_sockets = [
            x for x in actorx_import_node.inputs if x.is_linked and x.name == "mesh_socket"
        ]

        import_drivers["mesh_list"] = []

        for mesh_socket in mesh_sockets:
            walk_mesh_node(mesh_socket, None, import_drivers)

        print(list(import_drivers))

        return import_drivers

    # ----------------------------------------------------------------------------------------------
    from magicattr import get

    actorx_import_node = get(bpy, source_repr)

    import_drivers = walk_tree(actorx_import_node)

    import_driver = {}
    import_driver["model_list"] = import_drivers["model_list"]
    import_driver["mesh_list"] = import_drivers["mesh_list"]

    walk_import_dict(context, import_driver)

    if config.user_settings["options"]["dump_configuration"]:
        json_file_name = timestamp_log_file(config.user_drivers / "uilist.json")
        yaml_file_name = timestamp_log_file(config.user_drivers / "uilist.yaml")
        dump_json_file(json_file_name, import_driver)
        dump_yaml_file(yaml_file_name, import_driver)
