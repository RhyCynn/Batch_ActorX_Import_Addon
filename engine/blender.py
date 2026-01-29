# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 RhyCynn
#
# SPDX-License-Identifier: MIT
# --------------------------------------------------------------------------------------------------

"""TODO: move this code to common.py."""

import sys

import bpy
from bpy_extras.io_utils import axis_conversion
from mathutils import Matrix

from ..core.core import Configuration as config
from ..core.logging import Echo, SectionHeader

echo = Echo()


# --------------------------------------------------------------------------------------------------
def get_conversion_matrices(props) -> tuple[type[Matrix], type[Matrix]]:
    # TODO: move to a common module

    conversion_matrix = axis_conversion(
        from_forward=props["from_axis_forward"],
        from_up=props["from_axis_up"],
        to_forward=props["to_axis_forward"],
        to_up=props["to_axis_up"],
    ).to_4x4()

    return conversion_matrix, conversion_matrix.to_quaternion().conjugated().to_matrix().to_4x4()


# --------------------------------------------------------------------------------------------------
@SectionHeader()
def build_object_names(display_name: str) -> dict:
    names: dict = {}
    prefixes = config.prefixes

    for key, value in prefixes.items():
        names[key] = f"{value}{display_name}"

    return names


# --------------------------------------------------------------------------------------------------
def link_object(
    context: bpy.types.Context,
    collection: bpy.types.Collection,
    blender_object: bpy.types.Object,
) -> None:
    """link an object to the current collection."""

    if collection:
        collection.objects.link(blender_object)

    elif context:
        context.scene.collection.objects.link(blender_object)


# --------------------------------------------------------------------------------------------------
@SectionHeader()
def get_collection(collection_name: str) -> bpy.types.Collection:
    """this returns a collection, creating one if it doesn't exist."""

    # ----------------------------------------------------------------------------------------------
    def new_collection(collection_name: str) -> bpy.types.Collection:
        """create a new collection."""

        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)

        return collection

    # ----------------------------------------------------------------------------------------------
    if collection_name is None:
        return

    return (
        new_collection(collection_name)
        if collection_name not in bpy.data.collections
        else bpy.data.collections.get(collection_name)
    )


# --------------------------------------------------------------------------------------------------
def set_active_object(context: bpy.context, blender_object: bpy.types.Object):
    """this sets a blender object to active."""

    if context and blender_object:
        context.view_layer.objects.active = blender_object


# --------------------------------------------------------------------------------------------------
def get_armature_object(target) -> bpy.types.Object | None:
    """this attempts to get an armature object by context or name
    the context can be an armature or a mesh with a parent armature."""

    # NOTE: this is a mess. "There must be a better way!" /pound fist on table

    armature_object = None
    # message = None

    if target is None:
        # message = "The target is None"
        return

    # if the target is a string try to get the armature by name
    if isinstance(target, str):
        if not (armature_object := bpy.data.objects.get(target)):
            pass
            # message = f"The armature was not found: {target}"

        return armature_object

    # if the target is an object with a data type of armature, return the targets armature
    if (
        isinstance(target, bpy.types.Object)
        and target.data
        and isinstance(target.data, bpy.types.Armature)
    ):
        # message = f"Found armature: {target.object.data.name}"
        return target

    # if the target is a context object with a data type of armature, return the target armature
    if (
        isinstance(target, bpy.types.Context)
        and target.object
        and target.object.data
        and isinstance(target.object.data, bpy.types.Armature)
    ):
        # message = f"Found armature: {target.object.name}"
        return target.object

    # otherwise, the target is not a valid armature or does not have an armature
    if target.object and target.object.data:
        target = target.object.data
    elif target.object:
        target = target.object

    # message = f"The Target is not an Armature or has no Armature: {target}, type:  {type(target)}"
    return None


# --------------------------------------------------------------------------------------------------
@SectionHeader(print_leading_line=True)
def link_armatures(
    source_armature: bpy.types.Object,
    target_armature: bpy.types.Object,
    source_bone: str,
    target_bone: str,
):
    """link two armatures by a copy transformations bone constraint."""

    try:
        echo.value(message="Source Armature", value=source_armature, align_padding=True)
        echo.value(message="Target Armature", value=target_armature, align_padding=True)
        echo.value(message="Source Bone", value=source_bone, align_padding=True)
        echo.value(message="Target Bone", value=target_bone, align_padding=True)

        source_bone_object = source_armature.pose.bones.get(source_bone)
        target_bone_object = target_armature.pose.bones.get(target_bone)

        new_constraint = (
            bpy.data.objects[source_armature.name]
            .pose.bones[source_bone_object.name]
            .constraints.new("COPY_TRANSFORMS")
        )
        new_constraint.name = "".join(["copy_trans_", target_bone_object.name])
        new_constraint.target = bpy.data.objects[target_armature.name]
        new_constraint.subtarget = target_bone_object.name

    except Exception as e_error:
        print("An Fatal exception occurred linking the armatures")
        print(e_error)
        print("")
        sys.exit(1)


# --------------------------------------------------------------------------------------------------
def stop_playback(scene):
    """stop the animation playback loop."""

    if scene.frame_current == scene.frame_end:
        bpy.ops.screen.animation_cancel(restore_frame=False)


# --------------------------------------------------------------------------------------------------
def is_backwards_bone(orientation_matrix: Matrix, bone_name: str, use_column: False) -> bool:
    # bones with no children are backward in some cases. this attempts to detect them using
    # code derived from https://github.com/Befzz/blender3d_import_psk_psa in vec_to_axis_vec

    if use_column:
        x, y, z = orientation_matrix.col[0]
    else:
        x, y, z = orientation_matrix.row[0]

    rx = round(abs(x), 6)
    ry = round(abs(y), 6)
    rz = round(abs(z), 6)

    is_backwards_bone: bool = False
    messages = []

    messages.append(f"bone_name: {bone_name}")
    messages.append(f"abs(x): {rx}")
    messages.append(f"abs(y): {ry}")
    messages.append(f"abs(z): {rz}")

    if abs(x) > abs(y):
        messages.append(f"x: {rx} > y: {ry}")

        if abs(x) > abs(z):
            messages.append(f"  x: {rx} > z: {rz}")
            if x < 0:
                messages.append(f"  x: {round(x, 6)} < 0: {bone_name} reversed")
                is_backwards_bone = True

            # return [True, messages] if x < 0 else [False, None]

        else:
            messages.append(f"  x: {rx} < z: {rz}")
            if z < 0:
                messages.append(f"  z: {round(z, 6)} < 0: {bone_name} reversed")
                is_backwards_bone = True

            # return [True, messages] if z < 0 else [False, None]

    else:
        if abs(y) > abs(z):
            messages.append(f"y: {ry} > z: {rz}")
            if y < 0:
                messages.append(f"  y: {round(y, 6)} < 0: {bone_name} reversed")
                is_backwards_bone = True

            # return [True, messages] if y < 0 else [False, None]

        else:
            messages.append(f"y: {ry} < z: {rz}")
            if z < 0:
                messages.append(f"  z: {round(z, 6)} < 0: {bone_name} reversed")
                is_backwards_bone = True

            # return [True, messages] if z < 0 else [False, None]

    # echo.message("")
    # for message in messages:
    #     echo.message(message)

    return is_backwards_bone
