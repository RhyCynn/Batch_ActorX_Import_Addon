# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 RhyCynn
#
# SPDX-License-Identifier: MIT
# --------------------------------------------------------------------------------------------------

"""build and add an actorx mesh (*.psk, *.pskx)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..properties import AxMeshProps, AxModelProps

import bmesh
import bpy
from bpy_extras.io_utils import axis_conversion
from mathutils import Vector

from ..core.logging import Echo, SectionHeader
from .blender import build_object_names, get_collection, link_object, set_active_object
from .udk_data import ModelData

axis_roll_from_matrix = bpy.types.Bone.AxisRollFromMatrix

echo = Echo()


# ----------------------------------------------------------------------------------------------
@SectionHeader()
def create_mesh(names: dict) -> tuple[bpy.types.Mesh_props, bpy.types.Object, bmesh.types.BMesh]:
    """create and return a new mesh."""

    mesh_data = bpy.data.meshes.new(names["mesh_data"])
    mesh_object = bpy.data.objects.new(names["mesh_object"], mesh_data)

    bmesh_data = bmesh.new()
    bmesh_data.from_mesh(mesh_data)

    return mesh_data, mesh_object, bmesh_data


# ----------------------------------------------------------------------------------------------
@SectionHeader()
def create_materials(names: dict, mesh_data: bpy.types.Mesh_props, materials: list):
    """create a blender material with some basic attributes."""

    for _ in materials:
        blender_material = bpy.data.materials.new(names["material"])
        blender_material.blend_method = "CLIP"
        # blender_material.shadow_method = "CLIP"
        if bpy.app.version < (4, 2, 0):
            blender_material.shadow_method = "CLIP"
        blender_material.use_nodes = True
        mesh_data.materials.append(blender_material)


# ----------------------------------------------------------------------------------------------
@SectionHeader()
def create_uv_and_deform_layers(
    names: dict, bmesh_data: bmesh.types.BMesh
) -> tuple[bmesh.types.BMLoopUV, bmesh.types.BMLayerAccessVert]:
    """create and return the groups, uv layers and deform layers."""

    uv_layer = bmesh_data.loops.layers.uv.new(names["uv_layer"])
    deform_layer = bmesh_data.verts.layers.deform.new("deform_layer")

    return uv_layer, deform_layer


# ----------------------------------------------------------------------------------------------
@SectionHeader()
def create_mesh_modifier(
    names: dict, mesh_object: bpy.types.Object, target_armature: bpy.types.Object
):
    """create and apply a modifier to attach the mesh to an armature."""

    mesh_object.modifiers.new(names["mesh_modifier"], "ARMATURE")
    mesh_object.parent = target_armature
    mesh_object.modifiers[names["mesh_modifier"]].object = target_armature


# ----------------------------------------------------------------------------------------------
@SectionHeader()
def finalize_mesh(mesh_data: bpy.types.Mesh_props, bmesh_data: bmesh.types.BMesh):
    """convert and free up the bmesh object."""

    bmesh_data.to_mesh(mesh_data)
    bmesh_data.free()


# ----------------------------------------------------------------------------------------------
@SectionHeader()
def run_remove_doubles(bmesh_data: bmesh.types.BMesh):
    """execute the bmesh command to merge vertices."""

    verts_before_remove = len(bmesh_data.verts)
    bmesh.ops.remove_doubles(bmesh_data, verts=bmesh_data.verts, dist=0.001)
    verts_after_remove = len(bmesh_data.verts)
    verts_removed = verts_before_remove - verts_after_remove
    if verts_removed > 0:
        echo.value(message="Doubles Removed", value=str(verts_removed))


# ----------------------------------------------------------------------------------------------
@SectionHeader()
def set_smooth_shading(mesh_object: bpy.types.Object):
    """set the entire mesh_props to smooth shading."""

    mesh_object.data.polygons.foreach_set("use_smooth", [True] * len(mesh_object.data.polygons))


# --------------------------------------------------------------------------------------------------
@SectionHeader(print_leading_line=True)
def build_mesh(
    context: bpy.types.Context,
    mesh_props: AxMeshProps,
    model_props: AxModelProps,
    armature_object: bpy.types.Armature,
    node_type: str,
):
    """build the mesh."""

    remove_doubles = mesh_props["remove_doubles"]
    smooth_shading = mesh_props["smooth_shading"]

    if model_props and node_type == "Model":
        remove_doubles = model_props["remove_doubles"]
        smooth_shading = model_props["smooth_shading"]

    echo.value(message="Importing Mesh", width=20, value=mesh_props["display_name"])
    mesh_data = ModelData(mesh_props["file_path"])
    mesh_data.parse_psk_file()

    points = mesh_data.points
    wedges = mesh_data.wedges
    faces = mesh_data.faces
    materials = mesh_data.materials
    bones = mesh_data.bones
    weights = mesh_data.weights

    names = build_object_names(mesh_props["display_name"])
    collection = get_collection(collection_name="actorx_import")

    props = model_props if model_props else mesh_props

    conversion_matrix = axis_conversion(
        from_forward=props["from_axis_forward"],
        from_up=props["from_axis_up"],
        to_forward=props["to_axis_forward"],
        to_up=props["to_axis_up"],
    ).to_4x4()

    mesh_data, mesh_object, bmesh_data = create_mesh(names=names)
    link_object(context=context, collection=collection, blender_object=mesh_object)
    set_active_object(context=context, blender_object=mesh_object)

    create_materials(names=names, mesh_data=mesh_data, materials=materials)

    for weight in weights:
        points[weight.point_index].weights.append([weight.weight, weight.bone_index])

    uv_layer, deform_layer = create_uv_and_deform_layers(names=names, bmesh_data=bmesh_data)

    for bone in bones:
        mesh_object.vertex_groups.new(name=bone.name)

    for wedge in wedges:
        root_correction = False
        # if driver.root_correction:
        if root_correction:
            wedge.bmesh_vertex = bmesh_data.verts.new(wedge.vertex @ conversion_matrix)
        else:
            wedge.bmesh_vertex = bmesh_data.verts.new(wedge.vertex)

        # apply the weights
        for weights in points[wedge.point_index].weights:
            weight_value = weights[0]
            bone_index = weights[1]
            bone_name = bones[bone_index].name

            group_index = mesh_object.vertex_groups[bone_name].index
            wedge.bmesh_vertex[deform_layer][group_index] = weight_value

    # avoid checking each face to see if it exists
    for face in faces:
        wedge_0 = wedges[face.wedge_0]
        wedge_1 = wedges[face.wedge_1]
        wedge_2 = wedges[face.wedge_2]

        try:
            bmesh_face = bmesh_data.faces.new(
                (wedge_1.bmesh_vertex, wedge_0.bmesh_vertex, wedge_2.bmesh_vertex)
            )
            bmesh_face.material_index = face.mat_index

            uv_0 = Vector((wedge_0.u, 1.0 - wedge_0.v))
            uv_1 = Vector((wedge_1.u, 1.0 - wedge_1.v))
            uv_2 = Vector((wedge_2.u, 1.0 - wedge_2.v))

            bmesh_face.loops[0][uv_layer].uv = uv_1
            bmesh_face.loops[1][uv_layer].uv = uv_0
            bmesh_face.loops[2][uv_layer].uv = uv_2

        except ValueError as e:
            echo.value("An error occurred during face creation and will be ignored", str(e))
            pass

    bmesh_data.faces.index_update()

    if remove_doubles:
        run_remove_doubles(bmesh_data=bmesh_data)

    finalize_mesh(mesh_data=mesh_data, bmesh_data=bmesh_data)

    if armature_object:
        create_mesh_modifier(names=names, mesh_object=mesh_object, target_armature=armature_object)

    if smooth_shading:
        set_smooth_shading(mesh_object=mesh_object)

    return mesh_object
