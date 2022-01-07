import bpy
from bpy import data as D
from mathutils import *
from math import *

from typing import List, Set

"""
utility functions
"""
def ik2fk(context: bpy.types.Context, operator: bpy.types.Operator, add_keyframe: bool) -> Set[str]:
    obj = context.view_layer.objects.active
    if obj is None:
        operator.report({'OPERATOR'}, 'No object selected')
        return {"CANCELLED"}
    pose = obj.pose
    if pose is None:
        operator.report({'OPERATOR'}, 'Active object does not have pose data')
        return {"CANCELLED"}
    pose: bpy.types.Pose

    bones = selected_bones(obj)

    if bones is None:
        operator.report({'OPERATOR'}, 'No bone selected')
        return {"CANCELLED"}
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
        converted = obj.convert_space(pose_bone=bone, matrix=bone.matrix, from_space='POSE', to_space='LOCAL')
        bone.bone.select = True
        current_frame = context.scene.frame_current
        if add_keyframe:
            bone.keyframe_insert('rotation_quaternion', frame=current_frame - 1, group='FKIK Pose')
        bone.matrix_basis = converted
        if add_keyframe:
            bone.keyframe_insert('rotation_quaternion', frame=current_frame, group='FKIK Pose')
    
    # change constrint weight
    for constraint in ik_constraints:
        current_frame = context.scene.frame_current
        if add_keyframe:
            constraint.keyframe_insert('influence', frame=current_frame - 1, group='IK Weight')
        constraint.influence = 0
        if add_keyframe:
            constraint.keyframe_insert('influence', frame=current_frame, group='IK Weight')
    
    return {'FINISHED'}


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

"""
Blender Addon Interface
"""
bl_info = {
    "name": "FK/IK Switch",
    "author": "tianer2820",
    "version": (0, 1),
    "blender": (2, 80, 0),
    "location": "View3D > Pose Mode Side Panel > FK/IK Switch",
    "description": "Switch on/off IK constraints while keeping bones in-place",
    "warning": "",
    "doc_url": "",
    "category": "Animation",
}


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
    def poll(cls, context: bpy.types.Context):
        obj = context.view_layer.objects.active
        return (obj is not None) and\
            (obj.pose is not None) and\
            len(selected_bones(obj)) > 0 and\
            context.mode == 'POSE'

    def execute(self, context):
        if self.action == 'TOGGLE':
            pass
            return {'FINISHED'}
        elif self.action == 'FK2IK':
            pass
            return {'FINISHED'}
        elif self.action == 'IK2FK':
            return ik2fk(context, self, self.insert_keyframe)
        else:
            self.report({'ERROR'}, "Unknown action type: {}".format(self.action))
            return {'CANCELLED'}


class VIEW3D_PT_animation_fkik_switch(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Animation"
    bl_label = "FK/IK Switch"

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.mode == 'POSE'

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        props = layout.operator(ToggleFKIK.bl_idname, text=ToggleFKIK.bl_label)
        props.action = 'TOGGLE'
        props = layout.operator(ToggleFKIK.bl_idname, text="FK->IK")
        props.action = 'FK2IK'
        props = layout.operator(ToggleFKIK.bl_idname, text="IK->FK")
        props.action = 'IK2FK'

# Register and add to the "object" menu (required to also use F3 search "Simple Object Operator" for quick access)
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
