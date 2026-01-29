# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 RhyCynn
#
# SPDX-License-Identifier: MIT
# --------------------------------------------------------------------------------------------------

"""build and add an actorx animation (*.psa).
the math here was created largely by trial and error."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..properties import AxAnimationProps
from dataclasses import dataclass

import bpy
from mathutils import Matrix

from ..core.core import Configuration as config
from ..core.logging import Echo, SectionHeader
from .blender import get_conversion_matrices, stop_playback
from .udk_data import AnimData, UBone

axis_roll_from_matrix = bpy.types.Bone.AxisRollFromMatrix

echo = Echo()


@dataclass
class PreviousAnimation:
    """this is a hack to keep shorter animations from setting the frame end"""
    frame_end: int = 0


# --------------------------------------------------------------------------------------------------------
@SectionHeader()
def preprocess_psa_bones(target_armature, psa_bones: dict[str, UBone]) -> dict[str, UBone]:
    """preprocess the list of imported bones (psa_bones) to get blender's pose bone and pose bone parent."""

    for bone_name, psa_bone in psa_bones.items():
        pose_bone: bpy.types.PoseBone = target_armature.pose.bones.get(bone_name)

        # set the pose bone for this psa bone
        # if pose_bone is None:
        if not pose_bone:
            echo.value("Pose bone not found for psa bone", value=bone_name, width=46)

        else:
            psa_bone.pose_bone = pose_bone
            psa_bone.data_bone = pose_bone.bone

            # if pose_bone.parent is None:
            if not pose_bone.parent:
                echo.value("Parent pose bone not found for psa bone", value=bone_name, width=46)
            else:
                # if the pose bone's parent's name is in psa_bones,
                # set the pose bone parent for this psa bone
                if pose_bone.parent.name in psa_bones:
                    psa_bone.parent = psa_bones[pose_bone.parent.name]

                else:
                    echo.value(
                        "Parent pose bone name not found for psa bone", value=bone_name, width=46
                    )
                    # experimental partial animation import. does it even make sense?
                    psa_bone.parent = psa_bone
                    psa_bone.parent.world_matrix = psa_bone.pose_bone.parent.matrix_basis

    return psa_bones


# --------------------------------------------------------------------------------------------------------
def create_fcurves(
    psa_bones: dict[str, UBone], blender_action: bpy.types.Action
) -> dict[str, UBone]:
    """add the f-curves to the pose bones."""

    for _, psa_bone in psa_bones.items():
        if psa_bone.pose_bone is not None:
            data_path = psa_bone.pose_bone.path_from_id("location")
            psa_bone.fcurves_location = []

            for index in range(3):
                psa_bone.fcurves_location.append(blender_action.fcurves.new(data_path, index=index))

            data_path = psa_bone.pose_bone.path_from_id("rotation_quaternion")
            psa_bone.fcurves_rotation = []

            for index in range(4):
                psa_bone.fcurves_rotation.append(blender_action.fcurves.new(data_path, index=index))

    return psa_bones


# --------------------------------------------------------------------------------------------------
@SectionHeader(print_leading_line=True)
def build_animation(
    context: bpy.context,
    anim_props: AxAnimationProps,
    armature_object: bpy.types.Armature,
):
    """build the animation and parent it to an armature."""

    echo.value(message="Importing Animation", width=20, value=anim_props["display_name"])

    anim_data = AnimData(anim_props["file_path"])
    anim_data.parse_psa_file()
    conversion_matrix, conversion_matrix_conjugated = get_conversion_matrices(anim_props)

    psa_bones = anim_data.psa_bones
    actions = anim_data.actions

    # if armature_object.animation_data is None:
    if not armature_object.animation_data:
        armature_object.animation_data_create()

    nla_track = armature_object.animation_data.nla_tracks.new()
    nla_track.name = anim_props["display_name"]
    # nla_strip_start = 1

    psa_bones = preprocess_psa_bones(armature_object, psa_bones)

    total_max_raw_frames = 0

    total_actions = len(actions)

    # for action_name, action in sorted(actions):
    for index, [action_name, action] in enumerate(actions):
        echo.message(f"Current action {index + 1} of {total_actions}: {action_name}")
        if action_name in config.action_filters["ignore"]:
            echo.message(f"Ignoring action: {action_name}", indent_step=1)
            continue

        # action_name = f"{armature_object.name}_{action_name}"

        blender_action = bpy.data.actions.new(action_name)
        armature_object.animation_data.action = blender_action

        psa_bones = create_fcurves(psa_bones=psa_bones, blender_action=blender_action)

        keyframe_index = 0
        nla_strip_start_frame = total_max_raw_frames
        total_max_raw_frames += action.num_raw_frames

        # create the keyframe points
        for raw_frame_index in range(action.num_raw_frames):
            for bone_index, [bone_name, psa_bone] in enumerate(psa_bones.items()):
                axis_conversion_matrix = conversion_matrix.copy()

                if psa_bone.pose_bone is not None:
                    # if the custom property for reversed bones is set then use the conjugated matrix
                    if psa_bone.pose_bone.bone["reversed"]:
                        axis_conversion_matrix = conversion_matrix_conjugated

                    data_bone = psa_bone.data_bone
                    anim_key_frame = action.anim_key_frames[keyframe_index]

                    translation_matrix = Matrix.Translation(anim_key_frame.position)
                    rotation_matrix = anim_key_frame.orientation.to_matrix().to_4x4()
                    rotation_matrix_conjugated = (
                        anim_key_frame.orientation.conjugated().to_matrix().to_4x4()
                    )

                    if psa_bone.pose_bone.parent is not None:
                        if not anim_props["conjugate_non_root"]:
                            rotation_matrix = (
                                action.anim_key_frames[keyframe_index]
                                .orientation.to_matrix()
                                .to_4x4()
                            )
                        else:
                            rotation_matrix = (
                                action.anim_key_frames[keyframe_index]
                                .orientation.conjugated()
                                .to_matrix()
                                .to_4x4()
                            )

                        local_matrix = translation_matrix @ rotation_matrix

                        offset_data_bone_matrix = (
                            data_bone.parent.matrix_local.inverted() @ data_bone.matrix_local
                        ).inverted() @ conversion_matrix.inverted()

                        keyframe_matrix = (
                            offset_data_bone_matrix @ local_matrix @ axis_conversion_matrix
                        )

                    else:
                        world_matrix = (
                            translation_matrix @ rotation_matrix_conjugated
                            if anim_props["conjugate_root"]
                            else translation_matrix @ rotation_matrix
                        )

                        offset_data_bone_matrix = data_bone.matrix_local.inverted() @ world_matrix

                        keyframe_matrix = offset_data_bone_matrix @ conversion_matrix

                    # split the transformation for the location and rotation fcurves
                    pos, rot, _ = keyframe_matrix.decompose()

                    if anim_props["use_translation"]:
                        for index in range(3):
                            psa_bone.fcurves_location[index].keyframe_points.insert(
                                raw_frame_index, pos[index]
                            ).interpolation = "LINEAR"

                    for index in range(4):
                        psa_bone.fcurves_rotation[index].keyframe_points.insert(
                            raw_frame_index, rot[index]
                        ).interpolation = "LINEAR"

                # advance the keyframe index for "skipped" bones as there is a 1:1 relationship
                # between the psa bone list and the keyframe list
                keyframe_index += 1

        # set the nla track
        nla_track.strips.new(
            armature_object.animation_data.action.name,
            int(nla_strip_start_frame),
            # int(nla_strip_start),
            armature_object.animation_data.action,
        )
        # nla_strip_start += blender_action.frame_range[1]

        armature_object.animation_data.action = None

    nla_track.mute = True

    if total_max_raw_frames > PreviousAnimation.frame_end:
        context.scene.frame_end = total_max_raw_frames
        PreviousAnimation.frame_end = total_max_raw_frames

    context.scene.frame_current = 0

    bpy.app.handlers.frame_change_pre.append(stop_playback)
