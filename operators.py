import os
import shutil
import math

import bpy
from mathutils import Vector


class MCR_OT_multiple_camera_render(bpy.types.Operator):
    bl_idname = "mcr.multiple_camera_render"
    bl_label = "Render Sequence"
    bl_options = {'INTERNAL'}

    # Operator properties
    clockwise: bpy.props.BoolProperty(default=True)
    mode: bpy.props.EnumProperty(
        items=[
            ('VISIBLE', "Visible", ""),
            ('SELECTED', "Selected", "")
        ],
        default='VISIBLE'
    )

    # Fields to restore after render complete
    camera_queue = []
    render_filepath = ""
    frame_current = 0
    frame_end = 0
    use_lock_interface = True

    @classmethod
    def description(cls, context, properties):
        direction = "Clockwise" if properties.clockwise else "Counterclockwise"
        return f"Sequential rendering from multiple {properties.mode.lower()} cameras ({direction}).\n"\
            "Interface will be locked during rendering"

    @classmethod
    def render_pre_handler(cls, scene, c):
        scene.frame_current = cls.frame_current

    @classmethod
    def render_post_handler(cls, scene, c):
        prev_filepath = bpy.path.abspath(
            scene.render.filepath[0:-2]
            + f"_{cls.frame_current:01d}{scene.render.file_extension}")
        if os.path.isfile(prev_filepath):
            new_filepath = f"{scene.render.filepath[0: -2]}{scene.render.file_extension}"
            try:
                if os.path.isfile(new_filepath):
                    shutil.move(prev_filepath, new_filepath)
                else:
                    os.rename(prev_filepath, new_filepath)
            except Exception as e:
                print("Unable to rename output file")

        if len(cls.camera_queue):
            next_camera = cls.camera_queue.pop(0)
            scene.camera = next_camera
            scene.render.filepath = os.path.join(
                cls.render_filepath, next_camera.name) + "_#"
        else:
            scene.render.filepath = cls.render_filepath
            scene.frame_end = cls.frame_end
            scene.render.use_lock_interface = cls.use_lock_interface

            bpy.app.handlers.render_pre.remove(cls.render_pre_handler)
            bpy.app.handlers.render_post.remove(cls.render_post_handler)
            bpy.app.handlers.render_cancel.remove(cls.render_cancel_handler)

    @classmethod
    def render_cancel_handler(cls, scene, c):
        cls.camera_queue.clear()
        cls.render_post_handler(scene, None)

    def execute(self, context):
        cls = self.__class__

        scene = context.scene

        # Initial values ​​in order to return as it was at the
        # end of the render
        cls.render_filepath = scene.render.filepath
        cls.frame_current = scene.frame_current
        cls.frame_end = scene.frame_end
        cls.use_lock_interface = scene.render.use_lock_interface

        # Determine the queue of cameras in a circular sequence
        if self.mode == 'VISIBLE':
            camera_objects_src = context.visible_objects
        elif self.mode == 'SELECTED':
            camera_objects_src = context.selected_objects

        camera_angles = {}
        for ob in camera_objects_src:
            if ob.type == 'CAMERA':
                mat = ob.matrix_world
                x, y = -Vector([mat[0][2], mat[1][2]]).normalized()
                camera_angles[ob] = math.atan2(x, y)

        cls.camera_queue = [i[0] for i in sorted(
            camera_angles.items(), key=lambda item: item[1],
            reverse=(not self.clockwise)
        )]

        if not cls.camera_queue:
            if self.mode == 'VISIBLE':
                self.report(type={'WARNING'},
                            message="Scene missing camera object")
            elif self.mode == 'SELECTED':
                self.report(type={'WARNING'},
                            message="No camera object selected")
            return {'CANCELLED'}

        initial_camera = scene.camera
        if initial_camera and initial_camera in cls.camera_queue:
            ind = cls.camera_queue.index(initial_camera)
            if ind != 0:
                queue_start = cls.camera_queue[0:ind]
                cls.camera_queue = cls.camera_queue[ind:len(cls.camera_queue)]
                cls.camera_queue.extend(queue_start)

        # print([_.name for _ in cls.camera_queue])

        scene.frame_end = scene.frame_current + len(cls.camera_queue) - 1
        scene.render.use_lock_interface = True

        scene.camera = cls.camera_queue.pop(0)
        scene.render.filepath = os.path.join(
            cls.render_filepath, scene.camera.name) + "_#"

        bpy.app.handlers.render_pre.append(cls.render_pre_handler)
        bpy.app.handlers.render_post.append(cls.render_post_handler)
        bpy.app.handlers.render_cancel.append(cls.render_cancel_handler)

        bpy.ops.render.render('INVOKE_DEFAULT', animation=True,
                              use_viewport=True, write_still=True)

        return {'FINISHED'}


classes_ = [
    MCR_OT_multiple_camera_render


]

register, unregister = bpy.utils.register_classes_factory(classes_)
