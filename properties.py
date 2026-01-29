# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 RhyCynn
#
# SPDX-License-Identifier: MIT
# --------------------------------------------------------------------------------------------------

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import PropertyGroup

from .core.core import Configuration as config
from .core.core import get_actorx_models, update_parent_name


# --------------------------------------------------------------------------------------------------
class AxUITabs(PropertyGroup):
    """this is the main panel tabs."""

    # items format: ID, Name (Shown in panel), Description (Shown on hover)

    ui_tabs: EnumProperty(
        name="Tabs",
        description="UI Tabs",
        items=[
            ("id_Import", "Import", "Asset List"),
            ("id_Model", "Model", "Model List"),
            ("id_Mesh", "Mesh", "Mesh List"),
            ("id_Animation", "Animation", "Animation List"),
        ],
    )


# --------------------------------------------------------------------------------------------------
class AxFileBase(PropertyGroup):
    """these are properties common to most of the other groups."""

    file_path: StringProperty(name="File Path", default="")
    display_name: StringProperty(name="Display Name", default="")


# --------------------------------------------------------------------------------------------------
class AxUEViewerMat(AxFileBase, PropertyGroup):
    """these are the ueviewer material file options."""

    import_what: StringProperty(default="ueviewer_mat")
    filter_glob: StringProperty(name="Filter Glob", default="*.mat")


# --------------------------------------------------------------------------------------------------
class AxTexturePath(AxFileBase, PropertyGroup):
    """these are the ueviewer material file options."""

    import_what: StringProperty(default="texture_path")
    filter_glob: StringProperty(name="Filter Glob", default="")


# --------------------------------------------------------------------------------------------------
class AxDiffuseMap(AxFileBase, PropertyGroup):
    """these are the diffuse texture map file options."""

    import_what: StringProperty(default="diffuse_map")
    filter_glob: StringProperty(name="Filter Glob", default="*.tga;*.dds;*.png")


# --------------------------------------------------------------------------------------------------
class AxSpecularMap(AxFileBase, PropertyGroup):
    """these are the specular texture map file options."""

    import_what: StringProperty(default="specular_map")
    filter_glob: StringProperty(name="Filter Glob", default="*.tga;*.dds;*.png")


# --------------------------------------------------------------------------------------------------
class AxNormalMap(AxFileBase, PropertyGroup):
    """these are the normal texture map file options."""

    import_what: StringProperty(default="normal_map")
    filter_glob: StringProperty(name="Filter Glob", default="*.tga;*.dds;*.png")


# --------------------------------------------------------------------------------------------------
class AxModelAndMeshBase(PropertyGroup):
    """these are common model and mesh options."""

    ueviewer_mat: PointerProperty(type=AxUEViewerMat)
    texture_path: PointerProperty(type=AxTexturePath)
    diffuse_map: PointerProperty(type=AxDiffuseMap)
    specular_map: PointerProperty(type=AxSpecularMap)
    normal_map: PointerProperty(type=AxNormalMap)
    invert_green_channel: BoolProperty(name="Invert Normal Green Channel", default=True)
    rebuild_blue_channel: BoolProperty(name="Rebuild Normal Blue Channel", default=False)
    remove_doubles: BoolProperty(name="Remove Doubles", default=True)
    smooth_shading: BoolProperty(name="Smooth Shading", default=True)


# --------------------------------------------------------------------------------------------------
class AxModelMeshAndAnimationBase(PropertyGroup):
    """these are common model, mesh and animation options."""

    conjugate_root: BoolProperty(name="Conjugate Root", default=True)
    conjugate_non_root: BoolProperty(name="Conjugate Non-Root", default=True)

    from_axis_forward: EnumProperty(
        name="Axis Forward",
        description="Axis Forward",
        items=config.axis_list,
        default="X",
    )

    from_axis_up: EnumProperty(
        name="Axis Up",
        description="Axis Up",
        items=config.axis_list,
        default="Z",
    )

    to_axis_forward: EnumProperty(
        name="Axis Forward",
        description="Axis Forward",
        items=config.axis_list,
        default="Y",
    )
    to_axis_up: EnumProperty(
        name="Axis Up",
        description="Axis Up",
        items=config.axis_list,
        default="Z",
    )


# --------------------------------------------------------------------------------------------------
class AxAnimation(AxFileBase, AxModelMeshAndAnimationBase, PropertyGroup):
    """these are the animation options."""

    import_what: StringProperty(default="actorx_animation")
    filter_glob: StringProperty(name="Filter Glob", default="*.psa")

    hide_advanced_options: BoolProperty(name="Hide Advanced Options", default=True)

    use_translation: bpy.props.BoolProperty(name="Use Translation", default=True)
    interpolation: bpy.props.EnumProperty(
        name=bpy.types.Keyframe.bl_rna.properties["interpolation"].name,
        description=bpy.types.Keyframe.bl_rna.properties["interpolation"].description,
        items=[
            (x.identifier, x.name, x.description)
            for x in bpy.types.Keyframe.bl_rna.properties["interpolation"].enum_items
        ],
    )
    easing: bpy.props.EnumProperty(
        name=bpy.types.Keyframe.bl_rna.properties["easing"].name,
        description=bpy.types.Keyframe.bl_rna.properties["easing"].description,
        items=[
            (x.identifier, x.name, x.description)
            for x in bpy.types.Keyframe.bl_rna.properties["easing"].enum_items
        ],
    )


# --------------------------------------------------------------------------------------------------
class AxMesh(AxFileBase, AxModelAndMeshBase, AxModelMeshAndAnimationBase, PropertyGroup):
    """these are the mesh options."""

    import_what: StringProperty(default="actorx_mesh")
    filter_glob: StringProperty(name="Filter Glob", default="*.psk;*.pskx")

    hide_texture_maps: BoolProperty(name="Hide Texture Maps", default=True)
    hide_advanced_options: BoolProperty(name="Hide Advanced Options", default=True)


# --------------------------------------------------------------------------------------------------
class AxModel(AxFileBase, AxModelAndMeshBase, AxModelMeshAndAnimationBase, PropertyGroup):
    """these are the model options."""

    import_what: StringProperty(default="actorx_model")
    filter_glob: StringProperty(name="Filter Glob", default="*.psk;*.pskx")

    hide_texture_maps: BoolProperty(name="Hide Texture Maps", default=True)
    hide_advanced_options: BoolProperty(name="Hide Advanced Options", default=True)

    parent_name: StringProperty(default="")
    parent_model: EnumProperty(
        name="Parent Model",
        description="Sets this Models Parent to the Selected Model",
        items=get_actorx_models,
        update=update_parent_name,
    )
    parent_link: EnumProperty(
        name="Parent Link",
        description="The Type of Link to Create Between This Armature and it's Parent",
        items=config.parent_link,
    )
    builder: EnumProperty(
        name="Builder",
        description="",
        items=[
            ("direct_matrix", "Direct Matrix", ""),
            ("align_roll", "Align Roll", ""),
            ("axis_roll", "Axis Roll", ""),
        ],
    )
    plus_vector: EnumProperty(
        name="Plus Vector",
        description="",
        items=[
            ("100", "100", "100"),
            ("010", "010", "010"),
            ("001", "001", "001"),
        ],
    )
    detect_reversed_bones: BoolProperty(name="Detect Reversed Bones", default=True)
    show_bones_as_joints: BoolProperty(name="Show Bones as Joints", default=True)
    mesh_index: IntProperty(default=-1)
    mesh_list: CollectionProperty(type=AxMesh)
    animation_index: IntProperty(default=-1)
    animation_list: CollectionProperty(type=AxAnimation)


# --------------------------------------------------------------------------------------------------
# class AxAsset(AxFileBase, PropertyGroup):
#     """this is the asset folder in a list of asset folders."""

#     import_what: StringProperty(default="asset_path")
#     filter_glob: StringProperty(name="Filter Glob", default="")


# --------------------------------------------------------------------------------------------------
class AxImport(PropertyGroup):
    """this is the root import group."""

    import_what: StringProperty(default="Batch", options={"HIDDEN"})
    # asset_folder_index: IntProperty(default=-1)
    # asset_folder_list: CollectionProperty(type=AxAsset)
    model_index: IntProperty(default=-1)
    model_list: CollectionProperty(type=AxModel)
    mesh_index: IntProperty(default=-1)
    mesh_list: CollectionProperty(type=AxMesh)
    blender_collection: StringProperty(
        default="ActorX Import",
        description="The collection to add imported items to in the outliner",
    )
    import_status: StringProperty(default="")
    dump_configuration: BoolProperty(
        default=False, description="Dump the import configuration to a json and yaml file"
    )
    dummy_ax_model: PointerProperty(type=AxModel)


# --------------------------------------------------------------------------------------------------
classes = [
    AxUITabs,
    AxFileBase,
    AxUEViewerMat,
    AxTexturePath,
    AxDiffuseMap,
    AxSpecularMap,
    AxNormalMap,
    AxModelAndMeshBase,
    AxModelMeshAndAnimationBase,
    AxAnimation,
    AxMesh,
    AxModel,
    # AxAsset,
    AxImport,
]


# --------------------------------------------------------------------------------------------------
def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ui_tabs = PointerProperty(type=AxUITabs)
    bpy.types.Scene.node_ax_import = PointerProperty(type=AxImport)


# --------------------------------------------------------------------------------------------------
def unregister():
    del bpy.types.Scene.node_ax_import
    del bpy.types.Scene.ui_tabs
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
