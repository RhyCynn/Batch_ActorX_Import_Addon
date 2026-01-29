# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 RhyCynn
#
# SPDX-License-Identifier: MIT
# --------------------------------------------------------------------------------------------------

"""build and add an actorx mesh (*.psk, *.pskx)
the math here was created largely by trial and error."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..properties import AxModel

import bpy
from mathutils import Matrix, Vector

from ..core.logging import Echo, SectionHeader
from .blender import (
    build_object_names,
    get_collection,
    get_conversion_matrices,
    is_backwards_bone,
    link_object,
    set_active_object,
)
from .udk_data import ModelData

axis_roll_from_matrix = bpy.types.Bone.AxisRollFromMatrix

echo = Echo()


# --------------------------------------------------------------------------------------------------
@SectionHeader()
def create_actorx_custom_joint() -> AxModel:
    """create a collection containing a sphere to use for the setting show bones as joints."""
    # TODO: move to a common module

    # ----------------------------------------------------------------------------------------------
    def new_collection(collection_name: str) -> bpy.types.Collection:
        """create a new collection."""

        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)
        collection.hide_viewport = True
        collection.hide_render = True

        return collection

    # ----------------------------------------------------------------------------------------------
    actorx_custom_joint_collection = (
        new_collection("actorx_custom_joint_collection")
        if "actorx_custom_joint_collection" not in bpy.data.collections
        else bpy.data.collections.get("actorx_custom_joint_collection")
    )

    if not (actorx_custom_joint := bpy.data.objects.get("actorx_custom_joint")):
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=2,
            radius=1.0,
            calc_uvs=True,
            enter_editmode=False,
            align="WORLD",
            location=(0.0, 0.0, 0.0),
            rotation=(0.0, 0.0, 0.0),
            scale=(1.0, 1.0, 1.0),
        )
        actorx_custom_joint = bpy.context.object
        actorx_custom_joint_collection.objects.link(actorx_custom_joint)
        actorx_custom_joint.name = "actorx_custom_joint"
        bpy.context.collection.objects.unlink(actorx_custom_joint)
        bpy.data.collections.remove(actorx_custom_joint_collection)

    return actorx_custom_joint


# --------------------------------------------------------------------------------------------------
@SectionHeader()
def create_armature(names: dict) -> tuple[bpy.types.Object, bpy.types.Armature]:
    """create and return a new armature."""

    armature_data = bpy.data.armatures.new(names["armature_data"])
    armature_object = bpy.data.objects.new(names["armature_object"], armature_data)

    return armature_object, armature_data


# --------------------------------------------------------------------------------------------------
@SectionHeader(print_leading_line=True)
def build_model(context: bpy.types.Context, model_props: AxModel):
    """build the model."""

    echo.value(message="Importing Model", width=20, value=model_props["display_name"])
    model_data = ModelData(model_props["file_path"])
    model_data.parse_psk_file()
    create_actorx_custom_joint()

    names = build_object_names(model_props["display_name"])
    collection = get_collection(collection_name="actorx_import")
    conversion_matrix, conversion_matrix_conjugated = get_conversion_matrices(model_props)

    armature_object, armature_data = create_armature(names=names)

    link_object(
        context=context,
        collection=collection,
        blender_object=armature_object,
    )
    set_active_object(context=context, blender_object=armature_object)

    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode="EDIT", toggle=False)

    for index, psk_bone in enumerate(model_data.bones):
        axis_conversion_matrix = conversion_matrix.copy()
        translation_matrix = Matrix.Translation(psk_bone.position)
        rotation_matrix = psk_bone.orientation.to_matrix().to_4x4()
        rotation_matrix_conjugated = psk_bone.orientation.conjugated().to_matrix().to_4x4()

        edit_bone = armature_data.edit_bones.new(psk_bone.name)
        edit_bone["reversed"] = False

        if index == 0 and psk_bone.parent_index == 0:
            world_matrix = (
                translation_matrix @ rotation_matrix_conjugated
                if model_props["conjugate_root"]
                else translation_matrix @ rotation_matrix
            )
        else:
            parent_bone = model_data.bones[psk_bone.parent_index]
            edit_bone.parent = armature_data.edit_bones[psk_bone.parent_index]

            local_matrix = (
                translation_matrix @ rotation_matrix_conjugated
                if model_props["conjugate_non_root"]
                else translation_matrix @ rotation_matrix
            )
            world_matrix = parent_bone.world_matrix @ local_matrix

            if model_props["detect_reversed_bones"] and psk_bone.num_children == 0:
                if is_backwards_bone(
                    orientation_matrix=psk_bone.orientation.to_matrix().to_3x3(),
                    bone_name=psk_bone.name,
                    use_column=False,
                ):
                    axis_conversion_matrix = conversion_matrix_conjugated
                    edit_bone["reversed"] = True

        psk_bone.world_matrix = world_matrix
        edit_bone.head = world_matrix.to_translation()
        axis_conversion_world_matrix = world_matrix @ axis_conversion_matrix

        plus_vector = {
            "100": Vector((1, 0, 0)),
            "010": Vector((0, 1, 0)),
            "001": Vector((0, 0, 1)),
        }.get(model_props["plus_vector"])

        if model_props["builder"] == "direct_matrix":
            edit_bone.tail = edit_bone.head + plus_vector * 0.6
            edit_bone.matrix = axis_conversion_world_matrix

        elif model_props["builder"] == "axis_roll":
            (_, rot, _) = axis_conversion_world_matrix.decompose()
            axis, roll_angle = axis_roll_from_matrix(rot.to_matrix().to_3x3())
            edit_bone.tail = axis + edit_bone.head
            edit_bone.roll = roll_angle

        elif model_props["builder"] == "align_roll":
            (_, rot, _) = world_matrix.decompose()
            edit_bone.tail = (
                edit_bone.head
                + rot.to_matrix().to_4x4() @ conversion_matrix @ Vector((0, 1, 0)) * 0.6
            )
            roll_vec = rot @ Vector((0, 0, 1))
            edit_bone.align_roll(roll_vec)

    bpy.ops.object.mode_set(mode="OBJECT")
    context.view_layer.objects.active = armature_object

    pose_bones = armature_object.pose.bones
    if model_props["show_bones_as_joints"]:
        for pose_bone in pose_bones:
            pose_bone.custom_shape = bpy.data.objects.get("actorx_custom_joint")

            pose_bone.custom_shape_scale_xyz = Vector(
                [pose_bone.length * 0.3, pose_bone.length * 0.3, pose_bone.length * 0.3]
            )

    return armature_object
