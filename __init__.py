# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 RhyCynn
#
# SPDX-License-Identifier: MIT
# --------------------------------------------------------------------------------------------------

if "bpy" in locals():
    import importlib

    importlib.reload(properties)  # noqa
    importlib.reload(operators)  # noqa
    importlib.reload(node_tree)  # noqa
    importlib.reload(node_sockets)  # noqa
    importlib.reload(node_import)  # noqa
    importlib.reload(node_model)  # noqa
    importlib.reload(node_mesh)  # noqa
    importlib.reload(node_animation)  # noqa

else:
    from . import (
        properties,
        operators,
        node_tree,
        node_sockets,
        node_import,
        node_model,
        node_mesh,
        node_animation,
    )

from .core import core


# --------------------------------------------------------------------------------------------------
def load_configuration():
    """load the default configuration."""

    core.Configuration.load_configuration()


load_configuration()


# --------------------------------------------------------------------------------------------------
def register():
    """register blender classes."""
    properties.register()
    operators.register()
    node_tree.register()
    node_sockets.register()
    node_import.register()
    node_model.register()
    node_mesh.register()
    node_animation.register()


# --------------------------------------------------------------------------------------------------
def unregister():
    """unregister blender classes."""
    node_animation.unregister()
    node_mesh.unregister()
    node_model.unregister()
    node_import.unregister()
    node_sockets.unregister()
    node_tree.unregister()
    operators.unregister()
    properties.unregister()


# --------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    register()
