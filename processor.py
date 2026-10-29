# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 RhyCynn
#
# SPDX-License-Identifier: MIT
# --------------------------------------------------------------------------------------------------

import bpy
from bpy.types import Context

from .core.core import Configuration as config
from .core.core import MissingImportFileName
from .core.logging import Echo, SectionHeader
from .engine.common import (
    dump_json_file,
    dump_yaml_file,
    timestamp_log_file,
)

# from .engine.processor import walk_import_dict
from .engine.animation_builder import build_animation
from .engine.blender import link_armatures
from .engine.material_builder import build_materials
from .engine.mesh_builder import build_mesh
from .engine.model_builder import build_model

echo = Echo()

"""convert the node properties to an import driver dict."""


# --------------------------------------------------------------------------------------------------
@SectionHeader()
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
            model_item["parent_name"] = parent.ax_model_props.display_name
            model_item["parent_model"] = parent.ax_model_props.display_name

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
            walk_model_node(model_socket, import_drivers, parent=None)

        mesh_sockets = [
            x for x in actorx_import_node.inputs if x.is_linked and x.name == "mesh_socket"
        ]

        import_drivers["mesh_list"] = []

        for mesh_socket in mesh_sockets:
            walk_mesh_node(mesh_socket, None, import_drivers)

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


# --------------------------------------------------------------------------------------------------
def walk_import_dict(context, import_dict: dict):
    """traverse the import dictionary and load the models, meshes and animations."""

    # models are in a flat list due to the way blenders pointer properties and collections work
    # linked / nested models are connected by names
    for model in import_dict["model_list"]:
        armature_object = build_model(context, model)
        mesh_object = build_mesh(
            context=context,
            mesh_props=model,
            model_props=model,
            armature_object=armature_object,
            node_type="Model",
        )
        build_materials(context=context, mesh_object=mesh_object, prop=model)

        # if the model has another model as it's parent then link them together
        # the current linking is limited and creates a copy transforms between two bones

        # try to link models if linking is enabled and the parent link is not no_link
        if not config.user_settings["model_node"]["hide_model_linking"]:
            if model["parent_link"] != "no_link":
                if model["parent_model"] != "no_parent":
                    parent_name = f"{config.prefixes['armature_object']}{model['parent_name']}"

                    link = config.armature_links[model["parent_link"]]
                    # source_armature = armature_object
                    # target_armature = bpy.data.objects.get(parent_name)
                    # source_bone = link["source_bone"]
                    # target_bone = link["target_bone"]

                    link_armatures(
                        source_armature=armature_object,
                        target_armature=bpy.data.objects.get(parent_name),
                        source_bone=link["source_bone"],
                        target_bone=link["target_bone"],
                    )
                    # link_armatures(source_armature, target_armature, source_bone, target_bone)

        # child meshes are parented without building their armatures
        for mesh in model["mesh_list"]:
            mesh_object = build_mesh(
                context=context,
                mesh_props=mesh,
                model_props=model,
                armature_object=armature_object,
                node_type="Mesh",
            )
            build_materials(context=context, mesh_object=mesh_object, prop=mesh)

        # adding multiple animations to the same model is experimental
        for animation in model["animation_list"]:
            build_animation(context, animation, armature_object)

    for mesh in import_dict["mesh_list"]:
        mesh_object = build_mesh(
            context=context,
            mesh_props=mesh,
            model_props=None,
            armature_object=None,
            node_type="Mesh",
        )
        build_materials(context=context, mesh_object=mesh_object, prop=mesh)
