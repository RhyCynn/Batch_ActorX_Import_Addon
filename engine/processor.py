# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 RhyCynn
#
# SPDX-License-Identifier: MIT
# --------------------------------------------------------------------------------------------------

import bpy

from ..core.core import Configuration as config
from ..core.logging import Echo
from .animation_builder import build_animation
from .blender import link_armatures
from .material_builder import build_materials
from .mesh_builder import build_mesh
from .model_builder import build_model

echo = Echo()


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
        if not config.user_settings["model_node"]["hide_model_linking"]:
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
