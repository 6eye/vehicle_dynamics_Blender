bl_info = {
    "name": "Inertial-GNSS car data to blender",
    "author": "Federico Bertani",
    "location": "View3D > Tools",
    "description": "Blender simulation generator from inertial sensor data on car",
    "category": "Object", # TODO other possible categories are Animation and Physics
    "version": (1,1,2),
    "tracker_url" : "https://github.com/physycom/inertial_to_blender/issues"
}

import bpy
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
# different name from project and deployed zip
from . import addon_updater_ops
from blender import bootstrap

from bpy.props import StringProperty

bpy.types.Scene.datasetPath = StringProperty(
    name="Dataset path",
    description=":",
    default="",
    maxlen=2056,
)


class InertialBlenderPanel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = "Tools"
    bl_label = "Inertial-GNSS to blender"

    # bl_context = "object"

    def draw(self, context):
        layout = self.layout

        # Call to check for update in background
        # note: built-in checks ensure it runs at most once
        # and will run in the background thread, not blocking
        # or hanging blender
        # Internally also checks to see if auto-check enabled
        # and if the time interval has passed
        addon_updater_ops.check_for_update_background()

        col = layout.column()
        col.operator("physycom.load_dataset")
        col.prop(context.scene, "datasetPath")
        col.operator("physycom.animate_object")

        if addon_updater_ops.updater.update_ready == True:
            layout.label("Update available", icon="INFO")
        layout.label("")

        # call built-in function with draw code/checks
        addon_updater_ops.update_notice_box_ui(self, context)


# noinspection SpellCheckingInspection
class LoadDataset(bpy.types.Operator):
    """Object Cursor Array"""
    # TODO use more standard name
    bl_idname = "physycom.load_dataset"
    bl_label = "Load dataset"
    bl_options = {'REGISTER', 'UNDO'}

    # must be called filepath because fileselect_add() in invoke() assume this
    filepath = bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        context.scene.datasetPath = self.filepath
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class AnimateObject(bpy.types.Operator):
    """Object Cursor Array"""
    # TODO use more standard name
    bl_idname = "physycom.animate_object"
    bl_label = "Animate object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bootstrap.check_modules_existence()
        from src import get_trajectory_from_path
        scene = context.scene
        # get current frame per seconds value
        fps = scene.render.fps
        scene.unit_settings.system = 'METRIC'
        # get current selected object in scene
        obj = scene.objects.active
        # TODO check object is not None
        positions, times, angular_positions = get_trajectory_from_path(scene.datasetPath)
        # set animation lenght
        bpy.context.scene.frame_end = times[-1] * fps
        # create animation data
        obj.animation_data_clear()
        obj.animation_data_create()
        # create a new animation data action
        obj.animation_data.action = bpy.data.actions.new(name="MyAction")
        obj.rotation_mode = 'QUATERNION'
        positions_lenght = positions.shape[1]
        # create f-curve for each axis
        for index in range(3):
            fcurve_location = obj.animation_data.action.fcurves.new(data_path="location", index=index)
            fcurve_location.keyframe_points.add(positions_lenght)
            for i in range(0, positions_lenght):
                fcurve_location.keyframe_points[i].interpolation = 'CONSTANT'
                fcurve_location.keyframe_points[i].co = times[i] * fps, positions[index, i]
        # create f-curve for each quaternion component
        for index in range(4):
            fcurve_rotation = obj.animation_data.action.fcurves.new(data_path="rotation_quaternion", index=index)
            fcurve_rotation.keyframe_points.add(positions_lenght)
            for i in range(0, positions_lenght):
                fcurve_rotation.keyframe_points[i].interpolation = 'CONSTANT'
                fcurve_rotation.keyframe_points[i].co = times[i] * fps, angular_positions[index,i]
        print("Done adding keyframes!")
        curveData = bpy.data.curves.new('myCurve', type='CURVE')
        curveData.dimensions = '3D'
        curveData.resolution_u = 2

        # map coords to spline
        polyline = curveData.splines.new('POLY')
        polyline.points.add(positions_lenght)
        for i, location in enumerate(positions.T):
            polyline.points[i].co = (*location,1)
        curveOB = bpy.data.objects.new('myCurve', curveData)
        curveData.bevel_depth = 0.01
        # attach to scene and validate context
        scene.objects.link(curveOB)
        return {'FINISHED'}


def register():
    # register auto-update module
    # placed this on top so the plugin degenerate to a non working version
    # this can be fixed by a new release
    addon_updater_ops.register(bl_info)
    bpy.utils.register_class(AutoUpdatePreferences)
    bootstrap.install_dependencies()
    bpy.utils.register_class(LoadDataset)
    bpy.utils.register_class(AnimateObject)
    bpy.utils.register_class(InertialBlenderPanel)
    print("Done!")


def unregister():
    # TODO move to implicit unregistration (module)
    addon_updater_ops.unregister()
    bpy.utils.unregister_class(AutoUpdatePreferences)
    bootstrap.uninstall_packages_from_requirements_file()
    bpy.utils.unregister_class(LoadDataset)
    bpy.utils.unregister_class(AnimateObject)
    bpy.utils.unregister_class(InertialBlenderPanel)


class AutoUpdatePreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    # addon updater preferences

    auto_check_update = bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False,
    )

    updater_interval_months = bpy.props.IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0,
        min=0
    )
    updater_interval_days = bpy.props.IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=7,
        min=0,
        max=31
    )
    updater_interval_hours = bpy.props.IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23
    )
    updater_interval_minutes = bpy.props.IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59
    )


    def draw(self, context):
        layout = self.layout
        # col = layout.column() # works best if a column, or even just self.layout
        mainrow = layout.row()
        col = mainrow.column()
        # updater draw function
        # could also pass in col as third arg
        addon_updater_ops.update_settings_ui(self, context)

if __name__ == "__main__":
    register()
