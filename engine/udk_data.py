# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 RhyCynn
#
# SPDX-License-Identifier: MIT
# --------------------------------------------------------------------------------------------------

"""this module reads actorx files and stores the decoded data for use in
armature, mesh and animation creation."""

import struct
from dataclasses import dataclass, field
from itertools import islice

import bpy  # type: ignore  # NOQA
from mathutils import Quaternion, Vector

from ..core.logging import Echo, debug_dump

echo = Echo()


# --------------------------------------------------------------------------------------------------
@dataclass
class UChunkHeader:
    """chunk_id: ACTRHEAD, ANIMHEAD:
    A header with an ID, record size and record count."""

    # ----------------------------------------------------------------------------------------------
    chunk_id: str
    type_flag: int
    data_size: int
    data_count: int


# --------------------------------------------------------------------------------------------------
@dataclass
class UPoint:
    """A vertex."""

    vertex: list
    bmesh_vertex: None  # internal
    weights: list  # internal


# --------------------------------------------------------------------------------------------------
@dataclass
class UWedge:
    """chunk_id: VTXW0000:
    UDK: Vertex with texturing info, akin to Hoppe's 'Wedge' concept."""

    # ----------------------------------------------------------------------------------------------
    point_index: int  # pointer to vertex
    u: int  # texture U coordinate
    v: int  # texture V coordinate
    mat_index: int  # unused: udk, ActorX
    reserved: int  # unused: udk: reserved
    pad2: int  # padding
    vertex: int = 0  # internal: vertex for the UPoint at point_index
    bmesh_vertex: int = 0  # internal: bmesh vertex for the UPoint at point_index


# --------------------------------------------------------------------------------------------------
@dataclass
class UFace:
    """chunk_id: FACE0000:
    UDK: Textured triangle."""

    # ----------------------------------------------------------------------------------------------
    wedge_0: int  # pointer to UWedge
    wedge_1: int  # pointer to UWedge
    wedge_2: int  # pointer to UWedge
    mat_index: int  # pointer to material
    aux_mat_index: int  # unused: udk: unused
    smoothing_groups: int  # unused: 32-bit flag for smoothing groups


# --------------------------------------------------------------------------------------------------
@dataclass
class UMaterial:
    """chunk_id: MATT0000:
    UDK: Raw data material."""

    # ----------------------------------------------------------------------------------------------
    name: str  # voof
    texture_index: int  # unused ActorX: udk: multiskin index
    poly_flags: int  # unused ActorX: udk: polys with this material have this flag
    aux_material: int  # unused: udk: reserved
    aux_flags: int  # unused: udk: reserved
    lod_bias: int  # unused: udk: unused
    lod_style: int  # unused: udk: unused


# --------------------------------------------------------------------------------------------------
@dataclass
class UBone:
    """chunk_id: REFSKELT:
    UDK: A bone: an orientation, and a position, all relative to their parent."""

    # ----------------------------------------------------------------------------------------------
    index: int
    name: str  # voof
    flags: int  # unused: udk: reserved
    num_children: int  # unused: udk: unused
    parent_index: int  # index to parent bone, 0 or null if root
    qx: float  # quaternion x
    qy: float  # quaternion y
    qz: float  # quaternion z
    qw: float  # quaternion w
    px: float  # vector x
    py: float  # vector y
    pz: float  # vector z
    length: float  # unused: udk: unused
    sx: float  # vector x
    sy: float  # vector y
    sz: float  # vector z
    position: Vector = None  # position relative to parent
    orientation: Quaternion = None  # orientation (rotation) relative to parent
    pose_bone = None  # internal:
    data_bone = None  # internal:
    parent = None  # internal:
    world_matrix = None  # internal:
    world_translation = None  # internal:
    world_rotation = None  # internal:
    # fcurves_location = dict()
    # fcurves_rotation = dict()


# --------------------------------------------------------------------------------------------------
@dataclass
class UWeight:
    """chunk_id: RAWWEIGHTS:
    UDK: Raw data bone influence."""

    # ----------------------------------------------------------------------------------------------
    weight: float  # weight value
    point_index: int  # pointer to UPoint
    bone_index: int  # pointer to UBone


# --------------------------------------------------------------------------------------------------
@dataclass
class UExtraUV:
    """chunk_id: EXTRAUVS0:
    Additional UV sets created by ueviewer."""

    # ----------------------------------------------------------------------------------------------
    u: int  # texture U coordinate
    v: int  # texture V coordinate


# --------------------------------------------------------------------------------------------------
@dataclass
class UAnimationAction:
    """chunk_id: ANIMINFO:
    UDK: Binary animation info format."""

    # ----------------------------------------------------------------------------------------------
    name: str  # voof
    group: str  # group name, used as action name
    total_bones: int  # unused ActorX: udk: number of animation keys = total_bones * num_raw_frames
    root_include: int  # unused: udk unused
    key_compression_style: int  # unused: udk reserved
    key_quotum: int  # unused ActorX: udk: max key quotum for compression
    key_reduction: float  # unused ActorX: udk: desired
    track_time: float  # unused ActorX: udk: explicit, can be overridden by animation rate
    anim_rate: float  # unused: udk: fps TODO: determine if this is useful
    start_bone: int  # unused: udk: reserved, unused
    first_raw_frame: int  # unused ActorX: udk: no description
    num_raw_frames: int  # total frames for the track (not keyframes)
    anim_key_frames: list = field(default_factory=list)  # UAnimationKeyframes for this action


# --------------------------------------------------------------------------------------------------
@dataclass
class UAnimationKeyframe:
    """chunk_id: ANIMKEYS:
    UDK: An animation key. Position and orientation relative to parent."""

    # ----------------------------------------------------------------------------------------------
    px: float  # vector x
    py: float  # vector y
    pz: float  # vector z
    qx: float  # quaternion x
    qy: float  # quaternion y
    qz: float  # quaternion z
    qw: float  # quaternion w
    time: float  # unused: udk: duration until next key TODO: determine if this is useful
    position: Vector = None  # vector position relative to parent
    orientation: Quaternion = None  # quaternion orientation (rotation) relative to parent


# --------------------------------------------------------------------------------------------------
@dataclass
class UScaleAnimKey:
    """chunk_id: SCALEKEYS:
    UDK:."""

    # ----------------------------------------------------------------------------------------------
    px: float  #
    py: float  #
    pz: float  #
    time: float  #


# --------------------------------------------------------------------------------------------------
class ModelData:
    """contains the model classes and file parser."""

    # ----------------------------------------------------------------------------------------------
    def __init__(self, filepath):
        self.filepath = filepath
        self.points = []
        self.wedges = []
        self.faces = []
        self.materials = []
        self.bones = []
        self.weights = []
        self.extrauv = None
        self.extrauvs = []
        self.exception_type = None
        self.exception_value = None
        self.exception_traceback = None

    # ----------------------------------------------------------------------------------------------
    def __enter__(self):
        return self

    # ----------------------------------------------------------------------------------------------
    def __exit__(self, exception_type, exception_value, exception_traceback):
        if exception_type is not None:
            self.exception_type = exception_type
            self.exception_value = exception_value
            self.exception_traceback = exception_traceback

    # ----------------------------------------------------------------------------------------------
    def read_head(self, chunk_id=None, record_count=None, data_file=None):
        pass

    # ----------------------------------------------------------------------------------------------
    def read_header(self, data_file):
        fmt = "<20sLLL"
        calcsize = struct.calcsize(fmt)

        data_in = data_file.read(calcsize)

        if len(data_in) != 32:
            return

        data_in = struct.unpack(fmt, data_in)
        chunk_header = UChunkHeader(*data_in)

        chunk_header.chunk_id = bytes.decode(
            chunk_header.chunk_id.rstrip(b"\x00"), errors="replace"
        )

        return chunk_header

    # ----------------------------------------------------------------------------------------------
    def read_vertices(self, chunk_id=None, record_count=None, data_file=None):
        fmt = "<fff"
        calcsize = struct.calcsize(fmt)

        for record in struct.iter_unpack(fmt, data_file.read(record_count * calcsize)):
            point = UPoint(record, None, [])

            # if point in self.points:
            #     print("duplicate point")

            self.points.append(point)

    # ----------------------------------------------------------------------------------------------
    def read_wedges(self, chunk_id=None, record_count=None, data_file=None):
        if record_count <= 65536:
            fmt = "<HhffBBH"
        else:
            fmt = "<LffBBH"

        calcsize = struct.calcsize(fmt)

        if record_count <= 65536:
            for record in struct.iter_unpack(fmt, data_file.read(record_count * calcsize)):
                wedge = UWedge(record[0], *record[2:])
                wedge.vertex = self.points[wedge.point_index].vertex

                # if wedge in self.wedges:
                #     print("duplicate wedge")

                self.wedges.append(wedge)
        else:
            for record in struct.iter_unpack(fmt, data_file.read(record_count * calcsize)):
                wedge = UWedge(*record)
                wedge.vertex = self.points[wedge.point_index].vertex

                # if wedge in self.wedges:
                #     print("duplicate wedge")

                self.wedges.append(wedge)

    # ----------------------------------------------------------------------------------------------
    def read_face16s(self, chunk_id=None, record_count=None, data_file=None):
        fmt = "<HHHBBL"
        calcsize = struct.calcsize(fmt)

        self.read_faces(
            chunk_id=chunk_id,
            record_count=record_count,
            data_file=data_file,
            fmt=fmt,
            calcsize=calcsize,
        )

    # ----------------------------------------------------------------------------------------------
    def read_face32s(self, chunk_id=None, record_count=None, data_file=None):
        fmt = "<LLLBBL"
        calcsize = struct.calcsize(fmt)

        self.read_faces(
            chunk_id=chunk_id,
            record_count=record_count,
            data_file=data_file,
            fmt=fmt,
            calcsize=calcsize,
        )

    # ----------------------------------------------------------------------------------------------
    def read_faces(self, chunk_id=None, record_count=None, data_file=None, fmt=None, calcsize=None):
        for record in struct.iter_unpack(fmt, data_file.read(record_count * calcsize)):
            face = UFace(*record)

            # if face in self.faces:
            #     print("duplicate face")

            self.faces.append(face)

    # ----------------------------------------------------------------------------------------------
    def read_materials(self, chunk_id=None, record_count=None, data_file=None):
        fmt = "<64sLLLLll"
        calcsize = struct.calcsize(fmt)

        for record in struct.iter_unpack(fmt, data_file.read(record_count * calcsize)):
            material = UMaterial(*record)
            material.name = bytes.decode(material.name.rstrip(b"\x00"))

            self.materials.append(material)

    # ----------------------------------------------------------------------------------------------
    def read_bones(self, chunk_id=None, record_count=None, data_file=None):
        fmt = "<64sLllfffffffffff"
        calcsize = struct.calcsize(fmt)

        for index, record in enumerate(
            struct.iter_unpack(fmt, data_file.read(record_count * calcsize))
        ):
            bone = UBone(index, *record)
            bone.name = bytes.decode(bone.name.rstrip(b"\x00"))
            bone.position = Vector((bone.px, bone.py, bone.pz))
            bone.orientation = Quaternion((bone.qw, bone.qx, bone.qy, bone.qz))

            self.bones.append(bone)

    # ----------------------------------------------------------------------------------------------
    def read_weights(self, chunk_id=None, record_count=None, data_file=None):
        fmt = "<fLL"
        calcsize = struct.calcsize(fmt)

        for record in struct.iter_unpack(fmt, data_file.read(record_count * calcsize)):
            self.weights.append(UWeight(*record))

    # ----------------------------------------------------------------------------------------------
    def read_extra_uv(self, chunk_id=None, record_count=None, data_file=None):
        fmt = "<LL"
        calcsize = struct.calcsize(fmt)

        for record in struct.iter_unpack(fmt, data_file.read(record_count * calcsize)):
            self.extrauvs.append(UExtraUV(*record))

    # ----------------------------------------------------------------------------------------------
    def load_data(self, chunk_id=None, record_count=None, data_file=None):
        loader = dict(
            ACTRHEAD=dict(reader=self.read_head, records=None),
            PNTS0000=dict(reader=self.read_vertices, records=self.points),
            VTXW0000=dict(reader=self.read_wedges, records=self.wedges),
            FACE0000=dict(reader=self.read_face16s, records=self.faces),
            FACE3200=dict(reader=self.read_face32s, records=self.faces),
            MATT0000=dict(reader=self.read_materials, records=self.materials),
            REFSKELT=dict(reader=self.read_bones, records=self.bones),
            RAWWEIGHTS=dict(reader=self.read_weights, records=self.weights),
            EXTRAUVS0=dict(reader=self.read_extra_uv, records=self.extrauv),
            EXTRAUVS1=dict(reader=self.read_extra_uv, records=self.extrauv),
            EXTRAUVS2=dict(reader=self.read_extra_uv, records=self.extrauv),
        ).get(chunk_id)

        if loader:
            loader["records"] = loader["reader"](
                chunk_id=chunk_id, record_count=record_count, data_file=data_file
            )

    # ----------------------------------------------------------------------------------------------
    # @SectionHeader()
    def dump_data(self, name, data, maximum_records):
        """basic dump data to the console."""
        echo.value(message="name", value=name)

        for x in range(maximum_records):
            echo.value(message="index", value=x, indent_step=1)
            # echo.items(data[x])
        echo.message("")

    # ----------------------------------------------------------------------------------------------
    # @SectionHeader()
    def parse_psk_file(self):
        """parse and load an actorx psk / pskx model file."""

        with open(self.filepath, "rb") as data_file:
            record_count = None

            while True:
                chunk_header = self.read_header(data_file)

                if not chunk_header:
                    break

                chunk_id = chunk_header.chunk_id

                record_count = chunk_header.data_count

                self.load_data(chunk_id=chunk_id, record_count=record_count, data_file=data_file)

        if points := debug_dump["points"] > 0:
            self.dump_data("self.points", self.points, points)
        if wedges := debug_dump["wedges"] > 0:
            self.dump_data("self.wedges", self.wedges, wedges)
        if faces := debug_dump["faces"] > 0:
            self.dump_data("self.faces", self.faces, faces)
        if materials := debug_dump["materials"] > 0:
            self.dump_data("self.materials", self.materials, materials)
        if bones := debug_dump["bones"] > 0:
            self.dump_data("self.bones", self.bones, bones)
        if weights := debug_dump["weights"] > 0:
            self.dump_data("self.weights", self.weights, weights)
        if extrauvs := debug_dump["extrauvs"] > 0:
            self.dump_data("self.extrauvs", self.extrauvs, extrauvs)


# --------------------------------------------------------------------------------------------------
class AnimData:
    """contains the animation classes and file parser."""

    # ----------------------------------------------------------------------------------------------
    def __init__(self, filepath):
        self.filepath = filepath
        self.psa_bones = dict()
        self.bones = []
        self.actions = []
        self.key_frames = []
        self.scale_keys = []
        self.exception_type = None
        self.exception_value = None
        self.exception_traceback = None

    # ----------------------------------------------------------------------------------------------
    def __enter__(self):
        return self

    # ----------------------------------------------------------------------------------------------
    def __exit__(self, exception_type, exception_value, exception_traceback):
        if exception_type is not None:
            self.exception_type = exception_type
            self.exception_value = exception_value
            self.exception_traceback = exception_traceback

    # ----------------------------------------------------------------------------------------------
    def read_head(self, chunk_id=None, record_count=None, data_file=None):
        pass

    # ----------------------------------------------------------------------------------------------
    def read_header(self, data_file):
        fmt = "<20sLLL"
        calcsize = struct.calcsize(fmt)

        data_in = data_file.read(calcsize)

        if len(data_in) != 32:
            return

        data_in = struct.unpack(fmt, data_in)
        chunk_header = UChunkHeader(*data_in)

        chunk_header.chunk_id = bytes.decode(
            chunk_header.chunk_id.rstrip(b"\x00"), errors="replace"
        )

        return chunk_header

    # ----------------------------------------------------------------------------------------------
    def read_bones(self, chunk_id=None, record_count=None, data_file=None):
        fmt = "<64sLllfffffffffff"
        calcsize = struct.calcsize(fmt)

        for index, record in enumerate(
            struct.iter_unpack(fmt, data_file.read(record_count * calcsize))
        ):
            bone = UBone(index, *record)
            bone.name = bytes.decode(bone.name.rstrip(b"\x00"))
            bone.position = Vector((bone.px, bone.py, bone.pz))
            bone.orientation = Quaternion((bone.qw, bone.qx, bone.qy, bone.qz))

            self.bones.append(bone)
            self.psa_bones[bone.name] = bone

    # ----------------------------------------------------------------------------------------------
    def read_actions(self, chunk_id=None, record_count=None, data_file=None):
        fmt = "<64s64sllllffflll"
        calcsize = struct.calcsize(fmt)

        for record in struct.iter_unpack(fmt, data_file.read(record_count * calcsize)):
            anim_action = UAnimationAction(*record)
            anim_action.name = bytes.decode(anim_action.name.rstrip(b"\x00"))
            anim_action.group = bytes.decode(anim_action.group.rstrip(b"\x00"))

            self.actions.append([anim_action.name, anim_action])

    # ----------------------------------------------------------------------------------------------
    def read_keyframes(self, chunk_id=None, record_count=None, data_file=None):
        fmt = "<ffffffff"
        calcsize = struct.calcsize(fmt)

        key_frames = []

        for record in struct.iter_unpack(fmt, data_file.read(record_count * calcsize)):
            keyframe = UAnimationKeyframe(*record)
            keyframe.position = Vector((keyframe.px, keyframe.py, keyframe.pz))
            keyframe.orientation = Quaternion((keyframe.qw, keyframe.qx, keyframe.qy, keyframe.qz))

            key_frames.append(keyframe)

        start = 0
        stop = 0

        for action_name, action in self.actions:
            stop = stop + (action.total_bones * action.num_raw_frames)
            for frame in islice(key_frames, start, stop):
                action.anim_key_frames.append(frame)
            start = start + (action.total_bones * action.num_raw_frames)

    # ----------------------------------------------------------------------------------------------

    def read_scalekeys(self, chunk_id=None, record_count=None, data_file=None):
        fmt = "<ffff"
        calcsize = struct.calcsize(fmt)

        for record in struct.iter_unpack(fmt, data_file.read(record_count * calcsize)):
            scalekey = UScaleAnimKey(*record)

            self.scale_keys.append(scalekey)

    def split_anim_keys(self, anim_keys: dict):
        pass

    # ----------------------------------------------------------------------------------------------
    def load_data(self, chunk_id=None, record_count=None, data_file=None):
        loader = dict(
            ACTRHEAD=dict(reader=self.read_head),
            BONENAMES=dict(reader=self.read_bones),
            ANIMINFO=dict(reader=self.read_actions),
            ANIMKEYS=dict(reader=self.read_keyframes),
            SCALEKEYS=dict(reader=self.read_scalekeys),
        ).get(chunk_id)

        if loader:
            loader["reader"](chunk_id=chunk_id, record_count=record_count, data_file=data_file)

    # ----------------------------------------------------------------------------------------------
    def parse_psa_file(self):
        """parse and load an actorx psa animation file."""

        with open(self.filepath, "rb") as data_file:
            record_count = None

            while True:
                chunk_header = self.read_header(data_file)

                if not chunk_header:
                    break

                chunk_id = chunk_header.chunk_id

                record_count = chunk_header.data_count

                self.load_data(chunk_id=chunk_id, record_count=record_count, data_file=data_file)
