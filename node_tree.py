# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 RhyCynn
#
# SPDX-License-Identifier: MIT
# --------------------------------------------------------------------------------------------------

"custom node tree."

import bpy
from bpy.types import NodeTree
from nodeitems_utils import (
    NodeCategory,
    NodeItem,
    register_node_categories,
    unregister_node_categories,
)


# --------------------------------------------------------------------------------------------------
class ActorXImportNodeTree(NodeTree):
    bl_idname = "ActorXImportNodeTree"
    bl_label = "ActorX Import Node Tree"
    bl_icon = "NODETREE"

    inserted_links = []

    # ----------------------------------------------------------------------------------------------
    def update(self):
        """called when node graph changes."""
        if len(self.inserted_links) > 0:
            link = self.inserted_links[0]

            from_socket = link.from_socket.identifier.rsplit("_")
            to_socket = link.to_socket.identifier.rsplit("_")
            from_socket = f"{from_socket[0]}_{from_socket[1]}"
            to_socket = f"{to_socket[0]}_{to_socket[1]}"

            if from_socket != to_socket:
                self.links.remove(link)

        self.inserted_links.clear()


# --------------------------------------------------------------------------------------------------
class ActorXNodes(NodeCategory):
    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == "ActorXImportNodeTree"


# --------------------------------------------------------------------------------------------------
# custom nodes can be set up here to add entries that override properties on the base node
node_categories = [
    ActorXNodes(
        "ACTORX_IMPORT",
        "Import",
        items=[
            NodeItem("ActorXImportNode"),
            NodeItem("ActorXModelNode"),
            # NodeItem(
            #     "ActorXModelNode",
            #     label="ActorX Model: Link Head",
            #     settings={"armature_link": repr("head_to_body")},
            # ),
            # NodeItem(
            #     "ActorXModelNode",
            #     label="ActorX Model: Link Hair",
            #     settings={"armature_link": repr("hair_to_head")},
            # ),
            NodeItem("ActorXMeshNode"),
            NodeItem("ActorXAnimationNode"),
        ],
    ),
]


# --------------------------------------------------------------------------------------------------
classes = [ActorXImportNodeTree]


# --------------------------------------------------------------------------------------------------
def register():
    """register the classes and add the scene properties."""

    for cls in classes:
        bpy.utils.register_class(cls)

    register_node_categories("ACTORX_NODES", node_categories)


# --------------------------------------------------------------------------------------------------
def unregister():
    """unregister the classes and remove the scene properties."""

    unregister_node_categories("ACTORX_NODES")

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
