import os
import shutil
import math

import bpy
from mathutils import Vector


class MCR_OT_multiple_camera_render(bpy.types.Operator):
    bl_idname = "mcr.multiple_camera_render"
    bl_label = "Render Sequence"
    bl_options = {'INTERNAL'}

    # Fields to restore after render complete
    camera_queue = []
    camera_index = 0

    render_filepath = ""
    frame_current = 0
    frame_start = 0
    frame_end = 0
    use_lock_interface = True

    @classmethod
    def poll(cls, context):
        scene = context.scene
        if scene.render.is_movie_format:
            return False

        if scene.mcr.cameras_usage == 'VISIBLE':
            camera_objects_src = context.visible_objects
        elif scene.mcr.cameras_usage == 'SELECTED':
            camera_objects_src = context.selected_objects

        for ob in camera_objects_src:
            if ob.type == 'CAMERA':
                return True
        return False

    @classmethod
    def description(cls, context, properties):
        scene = context.scene
        camera_objects_src = []
        if scene.mcr.cameras_usage == 'VISIBLE':
            camera_objects_src = context.visible_objects
        elif scene.mcr.cameras_usage == 'SELECTED':
            camera_objects_src = context.selected_objects

        frames_count = 1 + scene.frame_end - scene.frame_start
        cameras_count = len(
            [_ for _ in camera_objects_src if _.type == 'CAMERA'])

        if cameras_count == 0:
            return f"Missing {scene.mcr.cameras_usage.lower()} cameras!"

        ret = ""
        if scene.mcr.mode == 'RENDER':
            ret = f"Render {cameras_count} images on current frame"
        elif scene.mcr.mode == 'ANIMATION':
            ret = f"Render {cameras_count * frames_count} images\n" \
                f"({frames_count} frames "\
                f"from {cameras_count} {scene.mcr.cameras_usage.lower()} cameras)"

        return ret

    @classmethod
    def reset_properties(cls):
        cls.camera_queue.clear()
        cls.camera_index = 0
        cls.render_filepath = ""
        cls.frame_current = 0
        cls.frame_start = 0
        cls.frame_end = 0
        cls.use_lock_interface = True

    @classmethod
    def update_camera(cls, scene):
        next_camera_object = cls.camera_queue[cls.camera_index]
        scene.camera = next_camera_object
        scene.render.filepath = os.path.join(
            cls.render_filepath, next_camera_object.name) + "_####"

    @classmethod
    def render_pre_handler(cls, scene, c):
        scene.frame_current = cls.frame_current

    @classmethod
    def restore_scene_settings(cls, scene):
        wm = bpy.context.window_manager
        wm.mcr.is_rendering = False

        scene.render.filepath = cls.render_filepath
        scene.frame_start = cls.frame_start
        scene.frame_end = cls.frame_end
        scene.render.use_lock_interface = cls.use_lock_interface

        bpy.app.handlers.render_pre.remove(cls.render_pre_handler)
        bpy.app.handlers.render_post.remove(cls.render_post_handler)
        bpy.app.handlers.render_cancel.remove(cls.render_cancel_handler)

    @classmethod
    def render_post_handler(cls, scene, c):
        # Remove frame number from rendered image filepath
        # (only if scene.mcr.mode == 'RENDER')
        if scene.mcr.mode == 'RENDER' and (not scene.mcr.keep_frame_in_filepath):
            prev_filepath = bpy.path.abspath(
                scene.render.filepath[0:-5]
                + f"_{cls.frame_current:04d}{scene.render.file_extension}")

            if os.path.isfile(prev_filepath):
                new_filepath = f"{scene.render.filepath[0: -5]}{scene.render.file_extension}"
                try:
                    if os.path.isfile(new_filepath):
                        shutil.move(prev_filepath, new_filepath)
                    else:
                        os.rename(prev_filepath, new_filepath)
                except Exception:
                    print("Unable to rename output file")

        if cls.camera_index < len(cls.camera_queue) - 1:
            cls.camera_index += 1
            cls.update_camera(scene)
        else:
            if scene.mcr.mode == 'RENDER':
                cls.restore_scene_settings(scene)
            elif scene.mcr.mode == 'ANIMATION':
                if cls.frame_current == cls.frame_end:
                    cls.restore_scene_settings(scene)
                else:
                    cls.camera_index = 0
                    cls.frame_current += 1
                    cls.update_camera(scene)

    @classmethod
    def render_cancel_handler(cls, scene, c):
        cls.restore_scene_settings(scene)

    def execute(self, context):
        cls = self.__class__

        cls.reset_properties()

        scene = context.scene

        # Initial values ​​in order to return as it was at the
        # end of the render
        cls.render_filepath = scene.render.filepath

        # Determine the queue of cameras in a circular sequence
        if scene.mcr.cameras_usage == 'VISIBLE':
            camera_objects_src = context.visible_objects
        elif scene.mcr.cameras_usage == 'SELECTED':
            camera_objects_src = context.selected_objects

        camera_angles = {}
        for ob in camera_objects_src:
            if ob.type == 'CAMERA':
                mat = ob.matrix_world
                x, y = -Vector([mat[0][2], mat[1][2]]).normalized()
                camera_angles[ob] = math.atan2(x, y)

        # Here we determine in which direction cameras will be changed
        if scene.mcr.direction == 'CLOCKWISE':
            reverse = False
        elif scene.mcr.direction == 'COUNTER':
            reverse = True

        cls.camera_queue = [i[0] for i in sorted(
            camera_angles.items(), key=lambda item: item[1],
            reverse=reverse
        )]

        # Cancel execution if there is no cameras
        if not cls.camera_queue:
            if scene.mcr.cameras_usage == 'VISIBLE':
                self.report(type={'WARNING'},
                            message="Scene missing camera object")
            elif scene.mcr.cameras_usage == 'SELECTED':
                self.report(type={'WARNING'},
                            message="No camera object selected")
            return {'CANCELLED'}

        # If scene.camera is not None, reformat queue to start from this camera
        initial_camera = scene.camera
        if initial_camera and initial_camera in cls.camera_queue:
            ind = cls.camera_queue.index(initial_camera)
            if ind != 0:
                queue_start = cls.camera_queue[0:ind]
                cls.camera_queue = cls.camera_queue[ind:len(cls.camera_queue)]
                cls.camera_queue.extend(queue_start)

        initial_camera = cls.camera_queue[cls.camera_index]

        # Prepare scene for execution in selected mode
        cameras_count = len(cls.camera_queue)

        frame_current = scene.frame_current
        frame_start = scene.frame_start
        frame_end = scene.frame_end

        cls.frame_start = frame_start
        cls.frame_end = frame_end

        if scene.mcr.mode == 'RENDER':
            frame_start = frame_current
            frame_end = frame_current + cameras_count - 1
        elif scene.mcr.mode == 'ANIMATION':
            frame_current = frame_start
            frame_end = (frame_start + (cameras_count *
                                        (frame_end - frame_start + 1))) - 1

        cls.frame_current = frame_current
        scene.frame_current = frame_current
        scene.frame_start = frame_start
        scene.frame_end = frame_end

        cls.update_camera(scene)

        bpy.app.handlers.render_pre.append(cls.render_pre_handler)
        bpy.app.handlers.render_post.append(cls.render_post_handler)
        bpy.app.handlers.render_cancel.append(cls.render_cancel_handler)

        wm = context.window_manager
        wm.mcr.is_rendering = True

        cls.use_lock_interface = scene.render.use_lock_interface
        scene.render.use_lock_interface = True
        bpy.ops.render.render('INVOKE_DEFAULT', animation=True,
                              use_viewport=True, write_still=True)

        return {'FINISHED'}


classes_ = [
    MCR_OT_multiple_camera_render


]

register, unregister = bpy.utils.register_classes_factory(classes_)
