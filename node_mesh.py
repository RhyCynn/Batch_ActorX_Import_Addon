# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 RhyCynn
#
# SPDX-License-Identifier: MIT
# --------------------------------------------------------------------------------------------------

"""mesh node and controls drawing."""

import bpy
from bpy.props import PointerProperty, StringProperty
from bpy.types import Context, Node, NodeLink, NodeSocket, UILayout

from .core.core import Configuration as config
from .core.core import hex_to_rgba, set_defaults

# from .core.core import node_colors
# from .core.core import node_colors, set_defaults
from .operators import ACTORXNODE_OT_AddFile, ACTORXNODE_OT_AddFolder
from .properties import AxMesh


# --------------------------------------------------------------------------------------------------
class ActorXMeshSocketOut(NodeSocket):
    """output socket to connect a mesh node to a model node or another mesh node."""

    bl_idname = "ActorXMeshSocketOut"
    bl_label = "ActorX Mesh Socket Output"

    identifier = "mesh_socket"
    link_limit = 1

    node_path: StringProperty(default="", options={"HIDDEN"})

    # ----------------------------------------------------------------------------------------------
    def draw(self, context: Context, layout: UILayout, node: Node, text: str):
        draw_ax_mesh_props(
            context=context,
            layout=layout,
            mesh_node=node,
            source_node=repr(self).split(".", maxsplit=1)[1].rsplit(".", maxsplit=1)[0],
        )

    def draw_color(self, context: Context, node: Node) -> dict:
        return hex_to_rgba(config.user_settings["socket_colors"]["mesh_socket"])


# --------------------------------------------------------------------------------------------------
class ActorXMeshNode(Node):
    """import node and properties for meshes (ignores armature) or static meshes.
    multiple mesh nodes are chained together."""

    bl_idname = "ActorXMeshNode"
    bl_label = "ActorX Mesh"

    ax_mesh_props: PointerProperty(type=AxMesh)

    # ----------------------------------------------------------------------------------------------
    def init(self, context: Context):
        """set_defaults: sets the properties default values from the json driver template."""

        set_defaults(self.ax_mesh_props, "AxMesh")
        set_defaults(self.ax_mesh_props.ueviewer_mat, "AxUEViewerMat")
        set_defaults(self.ax_mesh_props.texture_path, "AxTexturePath")
        set_defaults(self.ax_mesh_props.diffuse_map, "AxDiffuseMap")
        set_defaults(self.ax_mesh_props.specular_map, "AxSpecularMap")
        set_defaults(self.ax_mesh_props.normal_map, "AxNormalMap")

        socket_out = self.outputs.new(type="ActorXMeshSocketOut", name="mesh_socket")
        socket_out.display_shape = "CIRCLE"

        socket_in = self.inputs.new(type="ActorXMeshSocketIn", name="mesh_socket")
        socket_in.display_shape = "CIRCLE"

        self.width = config.user_settings["mesh_node"]["default_width"]
        self.color = hex_to_rgba(config.user_settings["mesh_node"]["node_color"])

    # ----------------------------------------------------------------------------------------------
    def insert_link(self, link: NodeLink):
        """update the node graph to remove an invalid link."""

        node_tree = self.id_data
        node_tree.inserted_links.append(link)


# --------------------------------------------------------------------------------------------------
def draw_ax_mesh_props(
    context: Context, layout: UILayout, mesh_node: AxMesh, source_node: str
) -> None:
    """draws the controls on the node with values from the property driver."""

    # ----------------------------------------------------------------------------------------------
    def add_file_select_row(
        layout: UILayout,
        mesh_node_prop: AxMesh,
        textbox: str,
        label: str,
        source_node: str,
        target_prop: str,
        add_folder: bool = False,
    ) -> None:
        """adds a row with a textbox and file select button.
        - source_node: the mesh node to set properties values.
        - target_prop: the target property to set on the source node."""

        row = layout.row(align=True)
        row.prop(mesh_node_prop, textbox, text=label)
        if not add_folder:
            op = row.operator(
                ACTORXNODE_OT_AddFile.bl_idname, text="", emboss=True, icon="FILEBROWSER"
            )
        else:
            op = row.operator(
                ACTORXNODE_OT_AddFolder.bl_idname, text="", emboss=True, icon="FILEBROWSER"
            )
        op.import_what = mesh_node_prop.import_what
        op.filter_glob = mesh_node_prop.filter_glob
        op.source_node = source_node
        op.target_prop = target_prop

    # ----------------------------------------------------------------------------------------------
    layout.use_property_split = config.user_settings["mesh_node"]["use_property_split"]
    layout.use_property_decorate = False
    col = layout.column(align=True)

    add_file_select_row(
        layout=col,
        mesh_node_prop=mesh_node.ax_mesh_props,
        textbox="display_name",
        label="Mesh",
        source_node=source_node,
        target_prop="ax_mesh_props",
    )

    add_file_select_row(
        layout=col,
        mesh_node_prop=mesh_node.ax_mesh_props.ueviewer_mat,
        textbox="display_name",
        label="Material",
        source_node=source_node,
        target_prop="ax_mesh_props.ueviewer_mat",
    )

    add_file_select_row(
        layout=col,
        mesh_node_prop=mesh_node.ax_mesh_props.texture_path,
        textbox="display_name",
        label="Texture Path",
        source_node=source_node,
        target_prop="ax_mesh_props.texture_path",
        add_folder=True,
    )

    col.prop(mesh_node.ax_mesh_props, "remove_doubles")
    col.prop(mesh_node.ax_mesh_props, "smooth_shading")
    col.prop(mesh_node.ax_mesh_props, "invert_green_channel")

    col.use_property_split = False
    col.prop(mesh_node.ax_mesh_props, "hide_texture_maps")

    # if not config.user_settings["mesh_node"]["hide_texture_maps"]:
    if not mesh_node.ax_mesh_props.hide_texture_maps:
        col.use_property_split = config.user_settings["mesh_node"]["use_property_split"]

        add_file_select_row(
            layout=col,
            mesh_node_prop=mesh_node.ax_mesh_props.diffuse_map,
            textbox="display_name",
            label="Diffuse",
            source_node=source_node,
            target_prop="ax_mesh_props.diffuse_map",
        )

        add_file_select_row(
            layout=col,
            mesh_node_prop=mesh_node.ax_mesh_props.specular_map,
            textbox="display_name",
            label="Specular",
            source_node=source_node,
            target_prop="ax_mesh_props.specular_map",
        )

        add_file_select_row(
            layout=col,
            mesh_node_prop=mesh_node.ax_mesh_props.normal_map,
            textbox="display_name",
            label="Normal",
            source_node=source_node,
            target_prop="ax_mesh_props.normal_map",
        )

    col.use_property_split = False
    col.prop(mesh_node.ax_mesh_props, "hide_advanced_options")

    # if not config.user_settings["mesh_node"]["hide_advanced_options"]:
    if not mesh_node.ax_mesh_props.hide_advanced_options:
        col.use_property_split = config.user_settings["mesh_node"]["use_property_split"]
        col.prop(mesh_node.ax_mesh_props, "from_axis_forward")
        col.prop(mesh_node.ax_mesh_props, "from_axis_up")


# --------------------------------------------------------------------------------------------------
classes = [
    ActorXMeshSocketOut,
    ActorXMeshNode,
]


# --------------------------------------------------------------------------------------------------
def register():
    """register blender classes."""

    for cls in classes:
        bpy.utils.register_class(cls)


# --------------------------------------------------------------------------------------------------
def unregister():
    """unregister blender classes."""

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
