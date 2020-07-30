from . import operators

if "bpy" in locals():
    import importlib
    importlib.reload(operators)

import bpy


class MCR_PT_multiple_camera_render(bpy.types.Panel):
    bl_label = "Multiple Camera Render"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Camera Render"
    bl_options = set()

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=True)

        # 'ALL' mode for MCR_OT_multiple_camera_render operator
        camera_count = 0
        for ob in context.visible_objects:
            if ob.type == 'CAMERA':
                camera_count += 1
        col.label(text=f"All cameras ({camera_count})")

        row = col.row(align=True)
        row.enabled = bool(camera_count)

        if camera_count == 1:
            props = row.operator(
                operator=operators.MCR_OT_multiple_camera_render.bl_idname,
                text="Render"
            )
            props.clockwise = True
            props.mode = 'SELECTED'
        else:
            props = row.operator(
                operator=operators.MCR_OT_multiple_camera_render.bl_idname,
                text="Сounter", icon='LOOP_BACK'
            )
            props.clockwise = False
            props.mode = 'VISIBLE'

            props = row.operator(
                operator=operators.MCR_OT_multiple_camera_render.bl_idname,
                text="Сlockwise", icon='LOOP_FORWARDS'
            )
            props.clockwise = True
            props.mode = 'VISIBLE'

        # 'SELECTED' mode for MCR_OT_multiple_camera_render operator
        camera_count = 0
        for ob in context.selected_objects:
            if ob.type == 'CAMERA':
                camera_count += 1

        col.label(text=f"Selected cameras ({camera_count})")

        row = col.row(align=True)
        row.enabled = bool(camera_count)

        if camera_count == 1:
            props = row.operator(
                operator=operators.MCR_OT_multiple_camera_render.bl_idname,
                text="Render Selected"
            )
            props.clockwise = True
            props.mode = 'SELECTED'
        else:
            props = row.operator(
                operator=operators.MCR_OT_multiple_camera_render.bl_idname,
                text="Сounter", icon='LOOP_BACK'
            )
            props.clockwise = False
            props.mode = 'SELECTED'

            props = row.operator(
                operator=operators.MCR_OT_multiple_camera_render.bl_idname,
                text="Сlockwise", icon='LOOP_FORWARDS'
            )
            props.clockwise = True
            props.mode = 'SELECTED'


classes_ = [
    MCR_PT_multiple_camera_render
]

register, unregister = bpy.utils.register_classes_factory(classes_)
