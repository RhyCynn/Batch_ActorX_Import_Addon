# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 RhyCynn
#
# SPDX-License-Identifier: MIT
# --------------------------------------------------------------------------------------------------

"""animation node and controls drawing."""

import bpy
from bpy.props import PointerProperty, StringProperty
from bpy.types import Context, Node, NodeLink, NodeSocket, UILayout

from .core.core import Configuration as config
from .core.core import hex_to_rgba, set_defaults
from .operators import ACTORXNODE_OT_AddFile
from .properties import AxAnimation


# --------------------------------------------------------------------------------------------------
class ActorXAnimationSocketOut(NodeSocket):
    """output socket to connect an animation node to a model node or another animation node."""

    bl_idname = "ActorXAnimationSocketOut"
    bl_label = "ActorX Animation Socket Output"

    identifier = "animation_socket"
    link_limit = 1

    node_path: StringProperty(default="", options={"HIDDEN"})

    # ----------------------------------------------------------------------------------------------
    def draw(self, context: Context, layout: UILayout, node: Node, text: str):
        draw_ax_animation_props(
            context=context,
            layout=layout,
            animation_node=node,
            source_node=repr(self).split(".", maxsplit=1)[1].rsplit(".", maxsplit=1)[0],
        )

    def draw_color(self, context: Context, node: Node) -> dict:
        return hex_to_rgba(config.user_settings["socket_colors"]["animation_socket"])


# --------------------------------------------------------------------------------------------------
class ActorXAnimationNode(Node):
    """import node and properties for animations."""

    bl_idname = "ActorXAnimationNode"
    bl_label = "ActorX Animation"

    ax_animation_props: PointerProperty(type=AxAnimation)

    # ----------------------------------------------------------------------------------------------
    def init(self, context: Context) -> None:
        """set_defaults: sets the properties default values from the json driver template."""

        set_defaults(self.ax_animation_props, "AxAnimation")

        socket_out = self.outputs.new(type="ActorXAnimationSocketOut", name="animation_socket")
        socket_out.display_shape = "CIRCLE"

        socket_in = self.inputs.new(type="ActorXAnimationSocketIn", name="animation_socket")
        socket_in.display_shape = "CIRCLE"

        self.width = config.user_settings["animation_node"]["default_width"]
        self.color = hex_to_rgba(config.user_settings["animation_node"]["node_color"])

    # ----------------------------------------------------------------------------------------------
    def insert_link(self, link: NodeLink) -> None:
        """update the node graph to remove an invalid link."""

        node_tree = self.id_data
        node_tree.inserted_links.append(link)


# --------------------------------------------------------------------------------------------------
def draw_ax_animation_props(
    context: Context, layout: UILayout, animation_node: AxAnimation, source_node: str
) -> None:
    """draws the controls on the node with values from the property driver."""

    # ----------------------------------------------------------------------------------------------
    def add_file_select_row(
        layout: UILayout,
        animation_node_prop: AxAnimation,
        textbox: str,
        label: str,
        source_node: str,
        target_prop: str,
    ) -> None:
        """adds a row with a textbox and file select button.
        - source_node: the animation node to set properties values.
        - target_prop: the target property to set on the source node."""

        row = layout.row(align=True)
        row.prop(animation_node_prop, textbox, text=label)
        op = row.operator(ACTORXNODE_OT_AddFile.bl_idname, text="", emboss=True, icon="FILEBROWSER")
        op.import_what = animation_node_prop.import_what
        op.filter_glob = animation_node_prop.filter_glob
        op.source_node = source_node
        op.target_prop = target_prop

    # ----------------------------------------------------------------------------------------------
    layout.use_property_split = config.user_settings["animation_node"]["use_property_split"]
    layout.use_property_decorate = False
    col = layout.column(align=True)

    add_file_select_row(
        layout=col,
        animation_node_prop=animation_node.ax_animation_props,
        textbox="display_name",
        label="Animation",
        source_node=source_node,
        target_prop="ax_animation_props",
    )

    col.prop(animation_node.ax_animation_props, "conjugate_root")
    col.prop(animation_node.ax_animation_props, "use_translation")

    col.use_property_split = False
    col.prop(animation_node.ax_animation_props, "hide_advanced_options")

    # if not config.user_settings["animation_node"]["hide_advanced_options"]:
    if not animation_node.ax_animation_props.hide_advanced_options:
        col.use_property_split = config.user_settings["animation_node"]["use_property_split"]

        col.prop(animation_node.ax_animation_props, "conjugate_non_root")
        col.prop(animation_node.ax_animation_props, "to_axis_forward")
        col.prop(animation_node.ax_animation_props, "to_axis_up")


# --------------------------------------------------------------------------------------------------
classes = [
    ActorXAnimationSocketOut,
    ActorXAnimationNode,
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
