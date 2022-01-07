import bpy


def main(context):
    for ob in context.scene.objects:
        print(ob)


class ToggleFKIK(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "pose.toggle_fk_ik"
    bl_label = "Toggle FK/IK"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        main(context)
        return {'FINISHED'}

def menu_func(self, context):
    self.layout.operator(ToggleFKIK.bl_idname, text=ToggleFKIK.bl_label)


class VIEW3D_PT_animation_fkik_switch(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Animation"
    bl_label = "FK/IK Switch"

    def draw(self, context: 'bpy.types.Context'):
        layout = self.layout
        layout.label(text="Test String")
        layout.operator(ToggleFKIK.bl_idname, text=ToggleFKIK.bl_label)

# Register and add to the "object" menu (required to also use F3 search "Simple Object Operator" for quick access)
def register():
    bpy.utils.register_class(ToggleFKIK)
    bpy.utils.register_class(VIEW3D_PT_animation_fkik_switch)
    # bpy.types.VIEW3D_MT_object.append(menu_func)

def unregister():
    bpy.utils.unregister_class(ToggleFKIK)
    bpy.utils.register_class(VIEW3D_PT_animation_fkik_switch)

    # bpy.types.VIEW3D_MT_object.remove(menu_func)


if __name__ == "__main__":
    register()

    # test call
    # bpy.ops.object.simple_operator()
