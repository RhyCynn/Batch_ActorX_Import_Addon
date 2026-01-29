# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 RhyCynn
#
# SPDX-License-Identifier: MIT
# --------------------------------------------------------------------------------------------------

"""model node and controls drawing."""

import bpy
from bpy.props import PointerProperty, StringProperty
from bpy.types import Context, Node, NodeLink, NodeSocket, UILayout

from .core.core import Configuration as config
from .core.core import hex_to_rgba, set_defaults

# from .core.core import node_colors
# from .core.core import node_colors, set_defaults
from .operators import (
    ACTORXNODE_OT_AddAnimationInputSocket,
    ACTORXNODE_OT_AddFile,
    ACTORXNODE_OT_AddFolder,
)
from .properties import AxModel


# --------------------------------------------------------------------------------------------------
class ActorXModelSocketOut(NodeSocket):
    """output socket to connect a model node to a import node or another model node."""

    bl_idname = "ActorXModelSocketOut"
    bl_label = "ActorX Model Socket Output"

    identifier = "model_socket"
    link_limit = 1

    node_path: StringProperty(default="", options={"HIDDEN"})

    # ----------------------------------------------------------------------------------------------
    def draw(self, context: Context, layout: UILayout, node: Node, text: str):
        draw_ax_model_props(
            context=context,
            layout=layout,
            model_node=node,
            source_node=repr(self).split(".", maxsplit=1)[1].rsplit(".", maxsplit=1)[0],
        )

    def draw_color(self, context: Context, node: Node) -> dict:
        return hex_to_rgba(config.user_settings["socket_colors"]["model_socket"])
        # return node_colors["model_socket"]


# --------------------------------------------------------------------------------------------------
class ActorXModelNode(Node):
    """import node and properties for models. additional animation input sockets for standard
    animations can be added via the command button. chained animations are for addon or
    partial animations that run at the same time as the standard animation."""

    bl_idname = "ActorXModelNode"
    bl_label = "ActorX Model"

    # used to tell an operator which node to update
    source_repr: StringProperty(default="", options={"HIDDEN"})

    ax_model_props: PointerProperty(type=AxModel)

    # ----------------------------------------------------------------------------------------------
    def draw_buttons(self, context: Context, layout: UILayout):
        layout.use_property_split = False
        layout.use_property_decorate = False
        col = layout.column(align=False)
        add_animation_socket = col.operator(
            ACTORXNODE_OT_AddAnimationInputSocket.bl_idname, text="Animation", icon="ADD"
        )
        add_animation_socket.source_repr = self.source_repr

    # ----------------------------------------------------------------------------------------------
    def init(self, context: Context):
        """set_defaults: sets the properties default values from the json driver template."""

        self.source_repr = repr(self).split(".", maxsplit=1)[1]

        set_defaults(self.ax_model_props, "AxModel")
        set_defaults(self.ax_model_props.ueviewer_mat, "AxUEViewerMat")
        set_defaults(self.ax_model_props.texture_path, "AxTexturePath")
        set_defaults(self.ax_model_props.diffuse_map, "AxDiffuseMap")
        set_defaults(self.ax_model_props.specular_map, "AxSpecularMap")
        set_defaults(self.ax_model_props.normal_map, "AxNormalMap")

        socket_out = self.outputs.new(type="ActorXModelSocketOut", name="model_socket")
        socket_out.display_shape = "CIRCLE"

        socket_in = self.inputs.new(type="ActorXMeshSocketIn", name="mesh_socket")
        socket_in.display_shape = "CIRCLE"

        socket_in = self.inputs.new(type="ActorXAnimationSocketIn", name="animation_socket")
        socket_in.display_shape = "CIRCLE"

        socket_in = self.inputs.new(type="ActorXModelSocketIn", name="model_socket")
        socket_in.display_shape = "CIRCLE"

        self.width = config.user_settings["model_node"]["default_width"]
        self.color = hex_to_rgba(config.user_settings["model_node"]["node_color"])

    # ----------------------------------------------------------------------------------------------
    def insert_link(self, link: NodeLink):
        """update the node graph to remove an invalid link."""

        node_tree = self.id_data
        node_tree.inserted_links.append(link)


# --------------------------------------------------------------------------------------------------
def draw_ax_model_props(
    context: Context, layout: UILayout, model_node: AxModel, source_node: str
) -> None:
    """draws the controls on the node with values from the property driver."""

    # ----------------------------------------------------------------------------------------------
    def add_file_select_row(
        layout: UILayout,
        model_node_prop: AxModel,
        textbox: str,
        label: str,
        source_node: str,
        target_prop: str,
        add_folder: bool = False,
    ) -> None:
        """adds a row with a textbox and file select button.
        - source_node: the model node to set properties values.
        - target_prop: the target property to set on the source node."""

        row = layout.row(align=True)
        row.prop(model_node_prop, textbox, text=label)
        if not add_folder:
            op = row.operator(
                ACTORXNODE_OT_AddFile.bl_idname, text="", emboss=True, icon="FILEBROWSER"
            )
        else:
            op = row.operator(
                ACTORXNODE_OT_AddFolder.bl_idname, text="", emboss=True, icon="FILEBROWSER"
            )
        op.import_what = model_node_prop.import_what
        op.filter_glob = model_node_prop.filter_glob
        op.source_node = source_node
        op.target_prop = target_prop

    # ----------------------------------------------------------------------------------------------
    layout.use_property_split = config.user_settings["model_node"]["use_property_split"]
    layout.use_property_decorate = False
    col = layout.column(align=True)

    add_file_select_row(
        layout=col,
        model_node_prop=model_node.ax_model_props,
        textbox="display_name",
        label="Model",
        source_node=source_node,
        target_prop="ax_model_props",
    )

    add_file_select_row(
        layout=col,
        model_node_prop=model_node.ax_model_props.ueviewer_mat,
        textbox="display_name",
        label="Material",
        source_node=source_node,
        target_prop="ax_model_props.ueviewer_mat",
    )

    add_file_select_row(
        layout=col,
        model_node_prop=model_node.ax_model_props.texture_path,
        textbox="display_name",
        label="Texture Path",
        source_node=source_node,
        target_prop="ax_model_props.texture_path",
        add_folder=True,
    )

    col.prop(model_node.ax_model_props, "remove_doubles")
    col.prop(model_node.ax_model_props, "smooth_shading")
    col.prop(model_node.ax_model_props, "invert_green_channel")
    col.prop(model_node.ax_model_props, "conjugate_root")
    col.prop(model_node.ax_model_props, "detect_reversed_bones")
    col.prop(model_node.ax_model_props, "show_bones_as_joints")

    if not config.user_settings["model_node"]["hide_model_linking"]:
        col.prop(model_node.ax_model_props, "parent_link")

    col.use_property_split = False
    col.prop(model_node.ax_model_props, "hide_texture_maps")

    # if not config.user_settings["model_node"]["hide_texture_maps"]:
    if not model_node.ax_model_props.hide_texture_maps:
        col.use_property_split = config.user_settings["model_node"]["use_property_split"]

        add_file_select_row(
            layout=col,
            model_node_prop=model_node.ax_model_props.diffuse_map,
            textbox="display_name",
            label="Diffuse",
            source_node=source_node,
            target_prop="ax_model_props.diffuse_map",
        )

        add_file_select_row(
            layout=col,
            model_node_prop=model_node.ax_model_props.specular_map,
            textbox="display_name",
            label="Specular",
            source_node=source_node,
            target_prop="ax_model_props.specular_map",
        )

        add_file_select_row(
            layout=col,
            model_node_prop=model_node.ax_model_props.normal_map,
            textbox="display_name",
            label="Normal",
            source_node=source_node,
            target_prop="ax_model_props.normal_map",
        )

    col.use_property_split = False
    col.prop(model_node.ax_model_props, "hide_advanced_options")

    # if not config.user_settings["model_node"]["hide_advanced_options"]:
    if not model_node.ax_model_props.hide_advanced_options:
        col.use_property_split = config.user_settings["model_node"]["use_property_split"]

        col.prop(model_node.ax_model_props, "builder")
        col.prop(model_node.ax_model_props, "conjugate_non_root")
        col.prop(model_node.ax_model_props, "from_axis_forward")
        col.prop(model_node.ax_model_props, "from_axis_up")


# --------------------------------------------------------------------------------------------------
classes = [
    ActorXModelSocketOut,
    ActorXModelNode,
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
