from . import operators

if "bpy" in locals():
    import importlib
    importlib.reload(operators)

import bpy


class MCRBase:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Camera Render"
    bl_options = set()


class MCR_PT_multiple_camera_render(MCRBase, bpy.types.Panel):
    bl_label = "Multiple Camera Render"

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=True)
        col.use_property_split = False
        col.use_property_decorate = False

        scene = context.scene

        row = col.row(align=True)
        row.prop(scene.mcr, "mode", expand=True)

        row = col.row(align=True)
        row.prop(scene.mcr, "direction", expand=True)

        row = col.row(align=True)
        row.prop(scene.mcr, "cameras_usage", expand=True)

        if scene.mcr.mode == 'RENDER':
            col.use_property_split = True
            col.prop(scene.mcr, "keep_frame_in_filepath")
        else:
            col.separator()

        if scene.render.is_movie_format:
            col.label(text="Unsupported render file format", icon='ERROR')

        if scene.mcr.mode == 'RENDER':
            text = f"Render Sequence"
            icon = 'RENDER_STILL'

        elif scene.mcr.mode == 'ANIMATION':
            text = f"Render Animation Sequence"
            icon = 'RENDER_ANIMATION'

        wm = context.window_manager
        if wm.mcr.is_rendering:
            col.template_running_jobs()
        else:
            scol = col.column(align=True)
            scol.scale_y = 1.5
            scol.operator(
                operator=operators.MCR_OT_multiple_camera_render.bl_idname,
                text=text, icon=icon
            )


classes_ = [
    MCR_PT_multiple_camera_render
]

register, unregister = bpy.utils.register_classes_factory(classes_)
