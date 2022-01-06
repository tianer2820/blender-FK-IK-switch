import bpy
from bpy import data as D
from bpy import context as C
from mathutils import *
from math import *

from typing import List


def ik2fk():
    obj = C.active_object
    if obj is None:
        print('nothing selected, abort')
        return
    pose = obj.pose
    if pose is None:
        print('active object does not have pose, abort')
        return
    pose: bpy.types.Pose

    bones = C.selected_pose_bones_from_active_object

    if bones is None:
        print('nothing selected, abort')
        return
    bones = bones.copy()

    ik_bones: List[bpy.types.PoseBone] = []
    ik_constraints = []
    for bone in bones:
        # detect IK head
        constraints = bone.constraints
        for constraint in constraints:
            constraint: bpy.types.Constraint
            if constraint.type == 'IK':
                # is a ik head
                constraint: bpy.types.KinematicConstraint
                chain_length = constraint.chain_count
                chain = follow_bone_chain(bone, chain_length)
                ik_bones.extend(chain)
                ik_constraints.append(constraint)
    
    # apply pose and select affected bones
    bpy.ops.pose.select_all(action='DESELECT')
    for bone in ik_bones:
        bone: bpy.types.PoseBone
        converted = obj.convert_space(pose_bone=bone, matrix=bone.matrix, from_space='WORLD', to_space='LOCAL')
        bone.matrix_basis = converted
        bone.bone.select = True
    for constraint in ik_constraints:
        constraint.influence = 0


def follow_bone_chain(bone: bpy.types.PoseBone, count: int) -> List[bpy.types.PoseBone]:
    chain = []
    current = bone
    i = 0
    while not current is None:
        chain.append(current)
        i += 1
        current = current.parent
        if count != 0 and i >= count:
            break
        print(current)
    return chain
    

if __name__ == "__main__":
    ik2fk()
