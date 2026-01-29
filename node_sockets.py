# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 RhyCynn
#
# SPDX-License-Identifier: MIT
# --------------------------------------------------------------------------------------------------

"""input sockets."""

import bpy
from bpy.props import IntProperty, StringProperty
from bpy.types import Context, Node, NodeSocket, UILayout

from .core.core import Configuration as config
from .core.core import hex_to_rgba

# from .core.core import node_colors
# from .core.logging import Echo

# echo = Echo()


# --------------------------------------------------------------------------------------------------
class ActorXModelSocketIn(NodeSocket):
    bl_idname = "ActorXModelSocketIn"
    bl_label = "ActorX Model"

    identifier = "model_socket"
    link_limit = 1

    source_repr: StringProperty()
    index: IntProperty()

    def draw(self, context: Context, layout: UILayout, node: Node, text: str):
        layout.label(text="Model")

    def draw_color(self, context: Context, node: Node) -> dict:
        return hex_to_rgba(config.user_settings["socket_colors"]["model_socket"])
        # return node_colors["model_socket"]


# --------------------------------------------------------------------------------------------------
class ActorXMeshSocketIn(NodeSocket):
    bl_idname = "ActorXMeshSocketIn"
    bl_label = "ActorX Mesh Socket Input"

    identifier = "mesh_socket"
    link_limit = 1

    source_repr: StringProperty()
    index: IntProperty()

    # ----------------------------------------------------------------------------------------------
    def draw(self, context: Context, layout: UILayout, node: Node, text: str):
        layout.label(text="Mesh")

    def draw_color(self, context: Context, node: Node) -> dict:
        return hex_to_rgba(config.user_settings["socket_colors"]["mesh_socket"])
        # return node_colors["mesh_socket"]


# --------------------------------------------------------------------------------------------------
class ActorXAnimationSocketIn(NodeSocket):
    bl_idname = "ActorXAnimationSocketIn"
    bl_label = "ActorX Animation Socket Input"

    identifier = "animation_socket"
    link_limit = 1

    source_repr: StringProperty()
    index: IntProperty()

    # ----------------------------------------------------------------------------------------------
    def draw(self, context: Context, layout: UILayout, node: Node, text: str):
        layout.label(text="Animation")

    def draw_color(self, context: Context, node: Node) -> dict:
        return hex_to_rgba(config.user_settings["socket_colors"]["animation_socket"])
        # return node_colors["animation_socket"]


# --------------------------------------------------------------------------------------------------
classes = [
    ActorXModelSocketIn,
    ActorXMeshSocketIn,
    ActorXAnimationSocketIn,
]


# --------------------------------------------------------------------------------------------------
def register():
    """register the classes and add the scene properties."""

    for cls in classes:
        bpy.utils.register_class(cls)


# --------------------------------------------------------------------------------------------------
def unregister():
    """unregister the classes and remove the scene properties."""

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
