import bpy
from bpy.types import PropertyGroup, Scene, WindowManager
from bpy.props import BoolProperty, EnumProperty, PointerProperty


class SceneProperties(PropertyGroup):

    mode: EnumProperty(
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

    direction: EnumProperty(
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

    cameras_usage: EnumProperty(
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

    keep_frame_in_filepath: BoolProperty(
        name="Keep Frame Number",
        default=False,
        description="If not selected, the frame number will\n"
                    "be removed from the rendered file name"
    )


class WindowManagerProperties(PropertyGroup):

    is_rendering: BoolProperty(default=False)


classes_ = [
    SceneProperties,
    WindowManagerProperties
]

cls_register, cls_unregister = bpy.utils.register_classes_factory(classes_)


def register():
    cls_register()

    Scene.mcr = PointerProperty(type=SceneProperties)
    WindowManager.mcr = PointerProperty(type=WindowManagerProperties)


def unregister():
    cls_unregister()

    del Scene.mcr
    del WindowManager.mcr
