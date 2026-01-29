# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 RhyCynn
#
# SPDX-License-Identifier: MIT
# --------------------------------------------------------------------------------------------------

"""root import node and controls drawing."""

import bpy
from bpy.props import StringProperty
from bpy.types import Context, Node, NodeLink, UILayout

from .core.core import Configuration as config
from .core.core import hex_to_rgba
from .operators import (
    ACTORXNODE_OT_AddMeshInputSocket,
    ACTORXNODE_OT_AddModelInputSocket,
    ACTORXNODE_OT_RunImport,
)


# --------------------------------------------------------------------------------------------------
class ActorXImportNode(Node):
    """root node containing a model socket in and a mesh socket in. addition sockets of each
    type can be added by clicking the appropriate button."""

    bl_idname = "ActorXImportNode"
    bl_label = "ActorX Import"

    # used to tell an operator which node to update
    source_repr: StringProperty(default="", options={"HIDDEN"})

    # ----------------------------------------------------------------------------------------------
    def init(self, context: Context):
        self.source_repr = repr(self).split(".", maxsplit=1)[1]

        model_socket_in = self.inputs.new(type="ActorXModelSocketIn", name="model_socket")
        model_socket_in.display_shape = "CIRCLE"

        mesh_socket_in = self.inputs.new(type="ActorXMeshSocketIn", name="mesh_socket")
        mesh_socket_in.display_shape = "CIRCLE"

        self.width = config.user_settings["import_node"]["default_width"]
        self.color = hex_to_rgba(config.user_settings["import_node"]["node_color"])

    # ----------------------------------------------------------------------------------------------
    def draw_buttons(self, context: Context, layout: UILayout):
        layout.use_property_split = False
        layout.use_property_decorate = False
        col = layout.column(align=False)

        node_ax_import = context.scene.node_ax_import

        row = layout.row(align=True)
        row.prop(node_ax_import, "blender_collection", text="Collection")
        row = layout.row(align=True)
        row.prop(node_ax_import, "import_status", text="Status")
        col = layout.column(align=False)
        add_model_socket = col.operator(
            ACTORXNODE_OT_AddModelInputSocket.bl_idname, text="Model", icon="ADD"
        )
        add_model_socket.source_repr = self.source_repr
        add_mesh_socket = col.operator(
            ACTORXNODE_OT_AddMeshInputSocket.bl_idname, text="Mesh", icon="ADD"
        )
        add_mesh_socket.source_repr = self.source_repr
        col = layout.column(align=False)
        action = col.operator(ACTORXNODE_OT_RunImport.bl_idname, text="Run Import")
        action.source_repr = self.source_repr

    # ----------------------------------------------------------------------------------------------
    def insert_link(self, link: NodeLink):
        """update the node graph to remove an invalid link."""

        node_tree = self.id_data
        node_tree.inserted_links.append(link)


# --------------------------------------------------------------------------------------------------
classes = [
    ActorXImportNode,
]


# --------------------------------------------------------------------------------------------------
def register():
    for cls in classes:
        bpy.utils.register_class(cls)


# --------------------------------------------------------------------------------------------------
def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
