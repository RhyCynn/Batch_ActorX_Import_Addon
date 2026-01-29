# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 RhyCynn
#
# SPDX-License-Identifier: MIT
# --------------------------------------------------------------------------------------------------

"""root import node and panel drawing."""

from pathlib import Path

import bpy
from bpy.props import IntProperty, StringProperty
from bpy.types import Context, Operator
from bpy_extras.io_utils import ImportHelper
from magicattr import get

from .core.core import MatFileReadError, MissingImportFileName
from .processor import walk_import_nodes


# --------------------------------------------------------------------------------------------------
class ACTORXNODE_OT_AddFolder(Operator, ImportHelper):
    """set the folder to search for texture maps.
    - source_node: the node to set properties values.
    - target_prop: the target property to set on the source node."""

    bl_idname = "actorxnode.add_folder"
    bl_label = "Add Folder"
    bl_options = {"UNDO", "PRESET"}

    import_what: StringProperty()
    index: IntProperty()

    directory: StringProperty(
        name="Asset Folder", description="Folder to search for texture maps", subtype="DIR_PATH"
    )
    filter_glob: StringProperty(default="", options={"HIDDEN"})
    source_node: StringProperty(default="", options={"HIDDEN"})
    target_prop: StringProperty(default="", options={"HIDDEN"})

    # ----------------------------------------------------------------------------------------------
    def invoke(self, context, event):
        return super().invoke(context, event)

    # ----------------------------------------------------------------------------------------------
    def execute(self, context):
        from magicattr import get, set

        target = get(bpy, f"{self.source_node}.{self.target_prop}")
        set(target, "file_path", Path(self.directory).as_posix())
        set(target, "display_name", Path(self.directory).as_posix())

        return {"FINISHED"}


# --------------------------------------------------------------------------------------------------
class ACTORXNODE_OT_AddFile(Operator, ImportHelper):
    """add a ueviewer material or texture map.
    - source_node: the node to set properties values.
    - target_prop: the target property to set on the source node."""

    bl_idname = "actorxnode.add_file"
    bl_label = ""
    bl_options = {"UNDO", "PRESET"}

    import_what: StringProperty()
    index: IntProperty()

    filter_glob: StringProperty(default="", options={"HIDDEN"})
    source_node: StringProperty(default="", options={"HIDDEN"})
    target_prop: StringProperty(default="", options={"HIDDEN"})

    # ----------------------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        match self.import_what:
            case "Model":
                self.bl_label = "Add Model"
            case "Mesh":
                self.bl_label = "Add Mesh"
            case "Animation":
                self.bl_label = "Add Animation"
            case "Material":
                self.bl_label = "Add UEV Material"
            case "DiffuseMap", "SpecularMap", "NormalMap":
                self.bl_label = "Add Texture"

    # ----------------------------------------------------------------------------------------------
    def invoke(self, context, event):
        return super().invoke(context, event)

    # ----------------------------------------------------------------------------------------------
    def execute(self, context):
        from magicattr import get, set

        display_name = f"{Path(self.filepath).stem}_{self.index:01d}"

        target = get(bpy, f"{self.source_node}.{self.target_prop}")
        set(target, "file_path", Path(self.filepath).as_posix())
        set(target, "display_name", display_name)

        return {"FINISHED"}


# ----------------------------------------------------------------------------------------------
class ACTORXNODE_OT_AddModelInputSocket(Operator):
    """add an import socket for model nodes."""

    bl_idname = "actorxnode.add_model_input_socket"
    bl_label = "Add Model"
    bl_options = {"UNDO", "PRESET"}

    source_repr: StringProperty(default="", options={"HIDDEN"})

    # ----------------------------------------------------------------------------------------------
    def execute(self, context):
        target = get(bpy, self.source_repr)

        new_socket = target.inputs.new(type="ActorXModelSocketIn", name="model_socket")
        new_socket.display_shape = "CIRCLE"

        return {"FINISHED"}


# ----------------------------------------------------------------------------------------------
class ACTORXNODE_OT_AddMeshInputSocket(Operator):
    """add an import socket for mesh nodes."""

    bl_idname = "actorxnode.add_mesh_input_socket"
    bl_label = "Add Mesh"
    bl_options = {"UNDO", "PRESET"}

    source_repr: StringProperty(default="", options={"HIDDEN"})

    # ----------------------------------------------------------------------------------------------
    def execute(self, context):
        target = get(bpy, self.source_repr)

        new_socket = target.inputs.new(type="ActorXMeshSocketIn", name="mesh_socket")
        new_socket.display_shape = "CIRCLE"

        return {"FINISHED"}


# ----------------------------------------------------------------------------------------------
class ACTORXNODE_OT_AddAnimationInputSocket(Operator):
    """add an import socket for animation nodes."""

    bl_idname = "actorxnode.add_animation_input_socket"
    bl_label = "Add Animation"
    bl_options = {"UNDO", "PRESET"}

    source_repr: StringProperty(default="", options={"HIDDEN"})

    # ----------------------------------------------------------------------------------------------
    def execute(self, context):
        target = get(bpy, self.source_repr)

        new_socket = target.inputs.new(type="ActorXAnimationSocketIn", name="animation_socket")
        new_socket.display_shape = "CIRCLE"

        return {"FINISHED"}


# --------------------------------------------------------------------------------------------------
class ACTORXNODE_OT_RunImport(Operator):
    """TODO: dump the uilists / node-tree to json / yaml."""

    bl_idname = "actorx.run_import"
    bl_label = "Run Import"
    bl_options = {"UNDO", "PRESET"}
    source_repr: StringProperty(default="", options={"HIDDEN"})

    # ----------------------------------------------------------------------------------------------
    @classmethod
    def poll(cls, context: Context):
        return True

    # ----------------------------------------------------------------------------------------------
    def execute(self, context):
        node_ax_import = bpy.context.scene.node_ax_import

        try:
            walk_import_nodes(context, self.source_repr)
            node_ax_import["import_status"] = "Finished"
            return {"FINISHED"}
        except MissingImportFileName:
            node_ax_import["import_status"] = "Error"
            self.report({"ERROR"}, "The import failed with a missing file name. See the console.")
            return {"CANCELLED"}
        except MatFileReadError:
            node_ax_import["import_status"] = "Error"
            self.report({"ERROR"}, "The import failed with a mat file read error. See the console.")
            return {"CANCELLED"}
        except RuntimeError as e:
            node_ax_import["import_status"] = "Error"
            print()
            print("A runtime error occurred")
            print()
            print(e)
            self.report({"ERROR"}, "The import failed with a runtime error. See the console.")
            return {"CANCELLED"}


# --------------------------------------------------------------------------------------------------
classes = [
    ACTORXNODE_OT_AddFile,
    ACTORXNODE_OT_AddFolder,
    ACTORXNODE_OT_RunImport,
    ACTORXNODE_OT_AddModelInputSocket,
    ACTORXNODE_OT_AddMeshInputSocket,
    ACTORXNODE_OT_AddAnimationInputSocket,
]


# --------------------------------------------------------------------------------------------------
def register():
    for cls in classes:
        bpy.utils.register_class(cls)


# --------------------------------------------------------------------------------------------------
def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
