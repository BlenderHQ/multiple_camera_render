from . import extend_bpy_types
from . import operators
from . import ui

if "bpy" in locals():
    import importlib
    importlib.reload(extend_bpy_types)
    importlib.reload(operators)
    importlib.reload(ui)

    register()

import bpy

bl_info = {
    "name": "Multiple Camera Render",
    "author": "Vlad Kuzmin (ssh4), Ivan Perevala (vanyOk)",
    "version": (0, 0, 2),
    "blender": (2, 80, 0),
    "description": "Sequential rendering from multiple cameras",
    "location": "Tool settings > Camera Render",
    "support": 'COMMUNITY',
    "category": "Render",
    "doc_url": "https://github.com/BlenderHQ/multiple_camera_render"
}


modules_ = [
    extend_bpy_types,
    operators,
    ui
]


def register():
    for module in modules_:
        reg_func = getattr(module, "register", None)
        if reg_func is not None:
            reg_func()


def unregister():
    for module in reversed(modules_):
        reg_func = getattr(module, "unregister", None)
        if reg_func is not None:
            reg_func()
