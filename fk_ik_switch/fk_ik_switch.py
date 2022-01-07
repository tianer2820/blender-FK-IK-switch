import bpy
from bpy import data as D
from mathutils import *
from math import *

from typing import List, Set


"""
Blender Addon Info
"""
bl_info = {
    "name": "FK/IK Switch",
    "author": "tianer2820",
    "version": (0, 1),
    "blender": (2, 80, 0),
    "location": "View3D > Pose Mode Side Panel > FK/IK Switch",
    "description": "Switch on/off IK constraints while keeping bones in-place",
    "warning": "",
    "support": "COMMUNITY",
    "doc_url": "https://github.com/tianer2820/blender-FK-IK-switch",
    "category": "Animation",
}


"""
utility functions
"""


def follow_bone_chain(bone: bpy.types.PoseBone, count: int) -> List[bpy.types.PoseBone]:
    chain = []
    current = bone
    i = 0
    while not current is None:
        chain.append(current)
        i += 1
        if not current.bone.use_connect:
            break
        if count != 0 and i >= count:
            break
        current = current.parent
    return chain


def selected_bones(object: bpy.types.Object) -> List[bpy.types.PoseBone]:
    if object is None:
        return None
    if object.pose is None:
        return None
    bones = []
    for p_bone in object.pose.bones:
        p_bone: bpy.types.PoseBone
        if p_bone.bone.select:
            bones.append(p_bone)
    return bones


class IKChain:
    def __init__(self, bones: List[bpy.types.PoseBone], constraint: bpy.types.KinematicConstraint) -> None:
        self.bones = bones
        self.constraint = constraint
        self.target = constraint.target
        self.subtarget = None
        if self.target is not None and self.target.type == 'ARMATURE':
            self.subtarget = self.target.pose.bones[self.constraint.subtarget]

        self.pole = constraint.pole_target
        self.subpole = None
        if self.pole is not None and self.pole.type == 'ARMATURE':
            self.subpole = self.pole.pose.bones[self.constraint.pole_subtarget]


"""
Operators
"""


class ToggleFKIK(bpy.types.Operator):
    """Switch IK on/off"""
    bl_idname = "pose.toggle_fk_ik"
    bl_label = "Toggle FK/IK"
    bl_options = {'REGISTER', 'UNDO'}

    _actions = [
        ("TOGGLE", "Toggle", "Toggle FK/IK"),
        ("FK2IK", "FK->IK", "Switch on IK"),
        ("IK2FK", "IK->FK", "Switch off IK"),
    ]
    action: bpy.props.EnumProperty(
        items=_actions,
        name="Action",
        description="The action to perform",
        default="TOGGLE")

    insert_keyframe: bpy.props.BoolProperty(name="Insert Keyframe",
                                            description="Insert Keyframe for bones and IK constraints",
                                            default=True)

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        obj = context.view_layer.objects.active
        return (obj is not None) and\
            (obj.pose is not None) and\
            len(selected_bones(obj)) > 0 and\
            context.mode == 'POSE'

    def execute(self, context: bpy.types.Context):
        if self.action == 'TOGGLE':
            self.report({'ERROR'}, 'Toggle is unimplemented yet')
            return {'CANCELLED'}
        elif self.action == 'FK2IK':
            return self.fk2ik(context)
        elif self.action == 'IK2FK':
            return self.ik2fk(context)
        else:
            self.report(
                {'ERROR'}, "Unknown action type: {}".format(self.action))
            return {'CANCELLED'}

    def try_get_obj_bones(self, context: bpy.types.Context) -> List:
        """
        return (active_object, selected pose bones) if valid,
        otherwise report an error and return None
        """
        obj = context.view_layer.objects.active
        if obj is None:
            self.report({'OPERATOR'}, 'No object selected')
            return None
        pose = obj.pose
        if pose is None:
            self.report({'OPERATOR'}, 'Active object does not have pose data')
            return None
        pose: bpy.types.Pose

        bones = selected_bones(obj)
        if bones is None:
            self.report({'OPERATOR'}, 'No bone selected')
            return None
        return obj, bones

    def ik2fk(self, context: bpy.types.Context) -> Set[str]:
        obj_bones = self.try_get_obj_bones(context)
        if obj_bones is None:
            return {'CANCELLED'}
        obj, bones = obj_bones

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

        # apply pose
        for bone in ik_bones:
            bone: bpy.types.PoseBone
            converted = obj.convert_space(
                pose_bone=bone, matrix=bone.matrix, from_space='POSE', to_space='LOCAL')
            current_frame = context.scene.frame_current
            if self.insert_keyframe:
                bone.keyframe_insert('rotation_quaternion', frame=current_frame - 1, group=bone.name)
            bone.matrix_basis = converted
            if self.insert_keyframe:
                bone.keyframe_insert('rotation_quaternion', frame=current_frame, group=bone.name)

        # change constrint influence
        for constraint in ik_constraints:
            current_frame = context.scene.frame_current
            if self.insert_keyframe:
                constraint.keyframe_insert(
                    'influence', frame=current_frame - 1, group='IK Weight')
            constraint.influence = 0
            if self.insert_keyframe:
                constraint.keyframe_insert(
                    'influence', frame=current_frame, group='IK Weight')

        return {'FINISHED'}

    def fk2ik(self, context: bpy.types.Context) -> Set[str]:
        # get required context
        obj_bones = self.try_get_obj_bones(context)
        if obj_bones is None:
            return {'CANCELLED'}
        obj, bones = obj_bones
        obj: bpy.types.Object
        bones: List[bpy.types.PoseBone]
        current_frame = context.scene.frame_current

        # detect IK chains
        ik_chains: List[IKChain] = []
        for bone in bones:
            # find IK head
            constraints = bone.constraints
            for constraint in constraints:
                constraint: bpy.types.Constraint
                if constraint.type == 'IK':
                    # is an ik head
                    constraint: bpy.types.KinematicConstraint
                    chain_length = constraint.chain_count
                    chain_bones = follow_bone_chain(bone, chain_length)

                    ik_chain = IKChain(chain_bones, constraint)
                    ik_chains.append(ik_chain)

        # convert each IK chain
        for chain in ik_chains:
            # calc the pole vector
            root = chain.bones[-1]
            leaf = chain.bones[0]
            chain_vector: Vector = leaf.tail - root.head
            chain_pole: Vector = Vector()
            for bone in chain.bones:
                relative: Vector = bone.center - root.head
                projected: Vector = relative.project(chain_vector)
                pole: Vector = relative - projected
                chain_pole += pole
            chain_pole /= len(chain.bones)
            chain_pole.magnitude = max(chain_pole.length * 4, chain_vector.length / 2)
            pole_location = root.head + chain_vector / 2 + chain_pole

            # set pole object location
            if chain.pole is not None:
                world_mat: Matrix = obj.convert_space(pose_bone=root, matrix=Matrix.Translation(pole_location),
                                                      from_space='POSE', to_space='WORLD')
                if chain.subpole is None:
                    # for object target
                    converted = chain.pole.convert_space(matrix=world_mat,
                                                         from_space='WORLD', to_space='LOCAL')
                    if self.insert_keyframe:
                        chain.target.keyframe_insert('location', frame=current_frame - 1, group='Object Transforms')
                    chain.pole.location = converted.translation
                    if self.insert_keyframe:
                        chain.target.keyframe_insert('location', frame=current_frame, group='Object Transforms')
                else:
                    # for bone target
                    converted = chain.pole.convert_space(pose_bone=chain.subpole,
                                                         matrix=world_mat,
                                                         from_space='WORLD', to_space='LOCAL')
                    if self.insert_keyframe:
                        chain.subtarget.keyframe_insert('location', frame=current_frame - 1, group=chain.subtarget.name)
                    chain.subpole.location = converted.translation
                    if self.insert_keyframe:
                        chain.subtarget.keyframe_insert('location', frame=current_frame, group=chain.subtarget.name)
            
            # set target object location
            if chain.target is not None:
                world_mat: Matrix = obj.convert_space(pose_bone=root, matrix=Matrix.Translation(leaf.tail),
                                                      from_space='POSE', to_space='WORLD')
                if chain.subtarget is None:
                    # for object target
                    converted = chain.target.convert_space(matrix=world_mat,
                                                         from_space='WORLD', to_space='LOCAL')
                    if self.insert_keyframe:
                        chain.target.keyframe_insert('location', frame=current_frame - 1, group='Object Transforms')
                    chain.target.location = converted.translation
                    if self.insert_keyframe:
                        chain.target.keyframe_insert('location', frame=current_frame, group='Object Transforms')
                else:
                    # for bone target
                    converted = chain.target.convert_space(pose_bone=chain.subtarget,
                                                         matrix=world_mat,
                                                         from_space='WORLD', to_space='LOCAL')
                    if self.insert_keyframe:
                        chain.subtarget.keyframe_insert('location', frame=current_frame - 1, group=chain.subtarget.name)
                    chain.subtarget.location = converted.translation
                    if self.insert_keyframe:
                        chain.subtarget.keyframe_insert('location', frame=current_frame, group=chain.subtarget.name)
            # change constraint influence
            if self.insert_keyframe:
                chain.constraint.keyframe_insert('influence', frame=current_frame - 1, group='IK Weight')
            chain.constraint.influence = 1.0
            if self.insert_keyframe:
                chain.constraint.keyframe_insert('influence', frame=current_frame, group='IK Weight')
            # clear bone pose
            for bone in chain.bones:
                if self.insert_keyframe:
                    bone.keyframe_insert('rotation_quaternion', frame=current_frame - 1, group=bone.name)
                bone.rotation_quaternion = Quaternion()
                if self.insert_keyframe:
                    bone.keyframe_insert('rotation_quaternion', frame=current_frame, group=bone.name)

        return {'FINISHED'}


"""
UIs
"""


class VIEW3D_PT_animation_fkik_switch(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Animation"
    bl_label = "FK/IK Switch"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.mode == 'POSE'

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        props = layout.operator(ToggleFKIK.bl_idname, text=ToggleFKIK.bl_label)
        props.action = 'TOGGLE'
        props = layout.operator(ToggleFKIK.bl_idname, text="FK->IK")
        props.action = 'FK2IK'
        props = layout.operator(ToggleFKIK.bl_idname, text="IK->FK")
        props.action = 'IK2FK'


"""
Register/Unregister functions
"""


def register():
    bpy.utils.register_class(ToggleFKIK)
    bpy.utils.register_class(VIEW3D_PT_animation_fkik_switch)
    # bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    bpy.utils.unregister_class(ToggleFKIK)
    bpy.utils.unregister_class(VIEW3D_PT_animation_fkik_switch)

    # bpy.types.VIEW3D_MT_object.remove(menu_func)


if __name__ == "__main__":
    register()

    # test call
    # bpy.ops.object.simple_operator()
