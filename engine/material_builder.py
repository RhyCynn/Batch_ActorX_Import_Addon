# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 RhyCynn
#
# SPDX-License-Identifier: MIT
# --------------------------------------------------------------------------------------------------

"""read a ueviewer .mat file to get the diffuse, specular and normal maps
TODO: load all named textures in the file and add then as unconnected texture nodes."""

import os
from pathlib import Path

import bpy
from bpy.types import Context, Mesh, Object
from mathutils import Vector

from ..core.core import MatFileReadError
from ..core.logging import Echo

echo = Echo()


# --------------------------------------------------------------------------------------------------
def build_materials(context: Context, mesh_object: Mesh, prop: dict) -> None:
    ueviewer_mat = prop["ueviewer_mat"]["file_path"]
    texture_path = prop["texture_path"]["file_path"]
    diffuse_map = prop["diffuse_map"]["file_path"]
    specular_map = prop["specular_map"]["file_path"]
    normal_map = prop["normal_map"]["file_path"]

    # a mat file must be selected, even if all three texture maps are added
    if not ueviewer_mat:
        echo.message("A .mat file was not selected. Skipping Texture Import.")
        return

    mat_file_path = None

    if ueviewer_mat:
        ueviewer_mat = Path(ueviewer_mat).resolve()
        mat_file_path = Path(ueviewer_mat).parent
    if texture_path:
        texture_path = Path(texture_path).resolve()
    if diffuse_map:
        diffuse_map = Path(diffuse_map).resolve()
    if specular_map:
        specular_map = Path(specular_map).resolve()
    if normal_map:
        normal_map = Path(normal_map).resolve()

    # if a texture path was specified use it otherwise use the mat file path
    search_path = None
    if texture_path:
        search_path = texture_path
    else:
        search_path = mat_file_path

    uev_materials = read_mat_file(material_file=ueviewer_mat)
    texture_maps = {"diffuse": None, "specular": None, "normal": None}

    # if a texture map was set directly use it otherwise try to search for any
    # listed in the mat file
    if diffuse_map:
        texture_maps["diffuse"] = diffuse_map
    elif diffuse_name := uev_materials.get("Diffuse"):
        if texture_map := find_texture(search_path=search_path, texture_name=diffuse_name):
            texture_maps["diffuse"] = texture_map

    if specular_map:
        texture_maps["specular"] = specular_map
    elif specular_name := uev_materials.get("Specular"):
        if texture_map := find_texture(search_path=search_path, texture_name=specular_name):
            texture_maps["specular"] = texture_map

    if normal_map:
        texture_maps["normal"] = normal_map
    elif normal_name := uev_materials.get("Normal"):
        if texture_map := find_texture(search_path=search_path, texture_name=normal_name):
            texture_maps["normal"] = texture_map

    # build the shader node tree and position the nodes
    build_shader_node_tree(
        mesh_object=mesh_object,
        uev_materials=texture_maps,
        invert_green_channel=prop["invert_green_channel"],
    )
    position_nodes(mesh_object=mesh_object, invert_green_channel=True)


# --------------------------------------------------------------------------------------------------
def find_texture(search_path: Path, texture_name: str) -> Path | None:
    """locate a texture name with any valid extension in the specified folder and sub-folders."""

    extensions = {".tga", ".dds", ".png"}

    # stops at the first texture found
    return next(
        (
            x
            for x in search_path.rglob("*")
            if x.suffix in extensions and x.stem.lower() == texture_name.lower()
        ),
        None,
    )


# --------------------------------------------------------------------------------------------------
def read_mat_file(material_file: str) -> dict[str, str] | None:
    """read a ueviewer .mat file and parse the contents."""

    # ----------------------------------------------------------------------------------------------
    try:
        with open(material_file, "r") as data_file:
            uev_materials = {}

            for line in data_file:
                shader_type, texture_filename = line.strip().split("=")

                if shader_type in ["Diffuse", "Specular", "Normal"]:
                    uev_materials[shader_type] = texture_filename

            return uev_materials

    except OSError as e:
        echo.message("An OS exception occurred reading the material file", leading_line=True)
        echo.message(os.strerror(e.errno))
        echo.message("Aborting Import", leading_line=True)
        raise MatFileReadError from e
    except Exception as e:
        echo.message("An Fatal exception occurred reading the material file", leading_line=True)
        echo.message(e)
        echo.message("Aborting Import", leading_line=True)
        raise MatFileReadError from e


# --------------------------------------------------------------------------------------------------
def build_shader_node_tree(
    mesh_object: Object, uev_materials: dict[str, str], invert_green_channel: bool
) -> None:
    """set up the blender shaders from the ueviewer materials."""

    for blender_material in mesh_object.data.materials:
        # get the material node tree and principled bsdf
        node_tree = blender_material.node_tree
        principled_bsdf = node_tree.nodes.get("Principled BSDF")

        if not principled_bsdf:
            return

        principled_bsdf.name = "principled_bsdf"

        if texture_filename := uev_materials.get("diffuse"):
            texture_filename = texture_filename.as_posix()
            echo.message("Loading Diffuse", indent_step=-1)
            tex_diffuse = node_tree.nodes.new("ShaderNodeTexImage")
            tex_diffuse.name = "tex_diffuse"
            tex_diffuse.label = "Diffuse"
            diffuse_texture = bpy.data.images.load(str(texture_filename))
            tex_diffuse.image = diffuse_texture

        if texture_filename := uev_materials.get("specular"):
            echo.message("Loading Specular", indent_step=-1)
            tex_specular = node_tree.nodes.new("ShaderNodeTexImage")
            tex_specular.name = "tex_specular"
            tex_specular.label = "Specular"
            specular_texture = bpy.data.images.load(str(texture_filename))
            tex_specular.image = specular_texture

        if texture_filename := uev_materials.get("normal"):
            echo.message("Loading Normal", indent_step=-1)
            tex_normal = node_tree.nodes.new("ShaderNodeTexImage")
            tex_normal.name = "tex_normal"
            tex_normal.label = "Normal"
            normal_texture = bpy.data.images.load(str(texture_filename))
            tex_normal.image = normal_texture

            if invert_green_channel:
                echo.message("Invert Normal Green Channel", indent_step=-1)
                rgb_separate = node_tree.nodes.new("ShaderNodeSeparateRGB")
                rgb_separate.name = "rgb_separate"
                rgb_separate.label = "RGB Separate"

                rgb_combine = node_tree.nodes.new("ShaderNodeCombineRGB")
                rgb_combine.name = "rgb_combine"
                rgb_combine.label = "RGB Combine"

                invert_green = node_tree.nodes.new("ShaderNodeInvert")
                invert_green.name = "invert_green"
                invert_green.label = "Invert Green"

            normal_map = node_tree.nodes.new("ShaderNodeNormalMap")
            normal_map.name = "map_normal"
            normal_map.label = "Normal Map"

        if texture_filename := uev_materials.get("diffuse"):
            # diffuse texture color connection
            output_socket = tex_diffuse.outputs["Color"]
            input_socket = principled_bsdf.inputs["Base Color"]
            node_tree.links.new(input_socket, output_socket)

            # diffuse texture alpha connection
            output_socket = tex_diffuse.outputs["Alpha"]
            input_socket = principled_bsdf.inputs["Alpha"]
            node_tree.links.new(input_socket, output_socket)

        # TODO: find a way to add the specular map that works for most situations
        # specular texture color connection
        # output_socket = tex_specular.outputs["Color"]
        # input_socket = principled_bsdf.inputs["Specular Tint"]
        # node_tree.links.new(input_socket, output_socket)

        # specular texture alpha connection
        # output_socket = tex_specular.outputs["Alpha"]
        # input_socket = principled_bsdf.inputs["Roughness"]
        # node_tree.links.new(input_socket, output_socket)

        if texture_filename := uev_materials.get("normal"):
            if invert_green_channel:
                # normal texture color connection
                output_socket = tex_normal.outputs["Color"]
                input_socket = rgb_separate.inputs["Image"]
                node_tree.links.new(input_socket, output_socket)
                tex_normal.image.colorspace_settings.name = "Non-Color"

                # separate rgb connections
                output_socket = rgb_separate.outputs["R"]
                input_socket = rgb_combine.inputs["R"]
                node_tree.links.new(input_socket, output_socket)

                output_socket = rgb_separate.outputs["B"]
                input_socket = rgb_combine.inputs["B"]
                node_tree.links.new(input_socket, output_socket)

                output_socket = rgb_separate.outputs["G"]
                input_socket = invert_green.inputs["Color"]
                node_tree.links.new(input_socket, output_socket)

                # invert green connection
                output_socket = invert_green.outputs["Color"]
                input_socket = rgb_combine.inputs["G"]
                node_tree.links.new(input_socket, output_socket)

                # combine rgb connection
                output_socket = rgb_combine.outputs["Image"]
                input_socket = normal_map.inputs["Color"]
                node_tree.links.new(input_socket, output_socket)

                # normal map connection
                output_socket = normal_map.outputs["Normal"]
                input_socket = principled_bsdf.inputs["Normal"]
                node_tree.links.new(input_socket, output_socket)

            else:
                # normal texture color connection
                output_socket = tex_normal.outputs["Color"]
                input_socket = normal_map.inputs["Color"]
                node_tree.links.new(input_socket, output_socket)
                tex_normal.image.colorspace_settings.name = "Non-Color"

                # normal map connection
                output_socket = normal_map.outputs["Normal"]
                input_socket = principled_bsdf.inputs["Normal"]
                node_tree.links.new(input_socket, output_socket)


# --------------------------------------------------------------------------------------------------
def position_nodes(mesh_object: Object, invert_green_channel: bool) -> None:
    """position the nodes

    this is a hack using hard coded sizes for the nodes as dimensions are (0, 0)
    until the shader editor is opened

    the spacing will be off if the ui scale is anything other than 1.00."""

    bpy.context.area.tag_redraw()

    for blender_material in mesh_object.data.materials:
        # get the material node tree and nodes
        node_tree = blender_material.node_tree
        if material_output := node_tree.nodes.get("Material Output"):
            material_output.location = Vector((600.0, 200.0))
        if principled_bsdf := node_tree.nodes.get("principled_bsdf"):
            principled_bsdf.location = Vector((300.0, 200.0))
        if tex_diffuse := node_tree.nodes.get("tex_diffuse"):
            tex_diffuse.location = Vector((-100.0, 300.0))
        if map_normal := node_tree.nodes.get("map_normal"):
            map_normal.location = Vector((000.0, -100.0))
        if rgb_combine := node_tree.nodes.get("rgb_combine"):
            rgb_combine.location = Vector((-200.0, -100.0))
        if invert_green := node_tree.nodes.get("invert_green"):
            invert_green.location = Vector((-400.0, 000.0))
        if rgb_separate := node_tree.nodes.get("rgb_separate"):
            rgb_separate.location = Vector((-600.0, -100.0))
        if tex_normal := node_tree.nodes.get("tex_normal"):
            tex_normal.location = Vector((-900.0, 000.0))
        if tex_specular := node_tree.nodes.get("tex_specular"):
            tex_specular.location = Vector((-100.0, -300.0))

    bpy.context.area.tag_redraw()
