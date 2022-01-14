# Multiple Camera Render addon.
# Copyright (C) 2020  Vlad Kuzmin (ssh4), Ivan Perevala (ivpe)

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

bl_info = {
    "name": "Multiple Camera Render",
    "author": "Vlad Kuzmin (ssh4), Ivan Perevala (ivpe)",
    "version": (3, 0, 0),
    "blender": (2, 80, 0),
    "description": "Sequential rendering from multiple cameras",
    "location": "Tool settings > Camera Render",
    "support": 'COMMUNITY',
    "category": "Render",
    "doc_url": "https://github.com/BlenderHQ/multiple_camera_render",
    "wiki_url": "https://github.com/BlenderHQ/multiple_camera_render",
}

import os
import shutil
import math

import bpy
from mathutils import Vector

# ____________________________________________________________________________ #
# Extend 'bpy' types.


class MCR_SceneProperties(bpy.types.PropertyGroup):
    mode: bpy.props.EnumProperty(
        name="Direction",
        items=(
            ('RENDER', "Render",
                "Render will be performed for cameras\n"
                "sequentially for the currently selected frame",
                'RENDER_STILL',
                0
             ),
            ('ANIMATION', "Animation",
                "Render will be performed for cameras\n"
                "sequentially for the selected frame interval",
                'RENDER_ANIMATION',
                1
             )
        ),
        default='RENDER',
        options={'HIDDEN'},
        description="Render mode"
    )

    direction: bpy.props.EnumProperty(
        name="Direction",
        items=(
            ('COUNTER', "Counter", "", 'LOOP_BACK', 0),
            ('CLOCKWISE', "Clockwise", "", 'LOOP_FORWARDS', 1)
        ),
        default='CLOCKWISE',
        options={'HIDDEN'},
        description="The direction in which the cameras will change\n"
                    "during the rendering of the sequence\n"
                    "(Starting from the current camera of the scene)"
    )

    cameras_usage: bpy.props.EnumProperty(
        name="Cameras Usage",
        items=[
            ('VISIBLE', "Visible",
                "Render from all visible cameras",
                'VIS_SEL_11',
                0
             ),
            ('SELECTED', "Selected",
                "Render only from selected cameras",
                'RESTRICT_SELECT_OFF',
                1
             )
        ],
        default='VISIBLE'
    )

    keep_frame_in_filepath: bpy.props.BoolProperty(
        name="Keep Frame Number",
        default=False,
        description="If not selected, the frame number will\n"
                    "be removed from the rendered file name"
    )


class MCR_WindowManagerProperties(bpy.types.PropertyGroup):
    is_rendering: bpy.props.BoolProperty(default=False)


# ____________________________________________________________________________ #
# Operators.


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
    def description(cls, context, _properties):
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
    def render_pre_handler(cls, scene, _c):
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
            frame_end = (frame_start + (cameras_count
                                        * (frame_end - frame_start + 1))) - 1

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

# ____________________________________________________________________________ #
# UI.


def get_ot_text_and_icon(context: bpy.types.Context) -> tuple:
    scene = context.scene
    text = icon = ""
    if scene.mcr.mode == 'RENDER':
        text = f"Render Sequence"
        icon = 'RENDER_STILL'

    elif scene.mcr.mode == 'ANIMATION':
        text = f"Render Animation Sequence"
        icon = 'RENDER_ANIMATION'

    return (text, icon)


class MCR_PT_multiple_camera_render(bpy.types.Panel):
    bl_label = "Multiple Camera Render"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Camera Render"
    bl_options = set()

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

        text, icon = get_ot_text_and_icon(context)

        wm = context.window_manager
        if wm.mcr.is_rendering:
            col.template_running_jobs()
        else:
            scol = col.column(align=True)
            scol.scale_y = 1.5
            scol.operator(
                operator=MCR_OT_multiple_camera_render.bl_idname,
                text=text, icon=icon
            )


# ____________________________________________________________________________ #
# Register/Unregister workflow.

_classes = [
    MCR_SceneProperties,
    MCR_WindowManagerProperties,
    MCR_OT_multiple_camera_render,
    MCR_PT_multiple_camera_render,
]

_cls_register, _cls_unregister = bpy.utils.register_classes_factory(_classes)


def draw_topbar_mt_render(self, context):
    layout = self.layout
    layout.separator()

    text, icon = get_ot_text_and_icon(context)
    layout.operator(
        operator=MCR_OT_multiple_camera_render.bl_idname,
        text=text, icon=icon
    )


def register():
    _cls_register()

    bpy.types.Scene.mcr = bpy.props.PointerProperty(type=MCR_SceneProperties)
    bpy.types.WindowManager.mcr = bpy.props.PointerProperty(type=MCR_WindowManagerProperties)

    bpy.types.TOPBAR_MT_render.append(draw_topbar_mt_render)


def unregister():
    del bpy.types.Scene.mcr
    del bpy.types.WindowManager.mcr

    _cls_unregister()
