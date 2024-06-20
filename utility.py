import logging
import pathlib
import re
import os
import stat
import shutil

import unreal

re_engine_version = re.compile('(\d+)\.(\d+)\.(\d+)')
re_class_name = re.compile(".+?\'(.+?)\'")
re_package_name = re.compile(".+?\'\"(.+?)\"\'")
re_split_package_name = re.compile("(.+?)\'\"(.+?)\"\'")

"""
usage) re_split_class_name
    input: "<Object '/Game/TestGame/Characters/MonsterAI_Temp/BP_Monster_Simple.BP_Monster_Simple_C' (0x0000066368DC5B00) Class 'BlueprintGeneratedClass'>"
    output: ('/Game/TestGame/Characters/MonsterAI_Temp/BP_Monster_Simple.BP_Monster_Simple_C', 'BlueprintGeneratedClass')
"""
re_split_class_name = re.compile(".+?\'(.+?)\'.+?Class \'(.+?)\'")

def class_name_to_asset_path(class_name):
    """usage) Object '/Game/Characters/BP_Monster_Simple.BP_Monster_Simple_C' -> '/Game/Characters/BP_Monster_Simple'"""
    m_asset_path = re_class_name.match(class_name)
    if m_asset_path:
        return m_asset_path.groups()[0].split('.')[0]
    logging.error(f'invalid class name: {class_name}')
    return ''

def package_name_to_asset_path(package_name):
    """usage) SkeletalMesh'"/Game/Item/IT_P_Arrow_00002_SK.IT_P_Arrow_00002_SK"' -> '/Game/Item/IT_P_Arrow_00002_SK'"""
    m_asset_path = re_package_name.match(package_name)
    if m_asset_path:
        return m_asset_path.groups()[0].split('.')[0]
    logging.error(f'invalid package name: {package_name}')
    return ''

def relative_filepath_to_asset_path(relative_filepath):
    """usage) 'Content/Characters/BP_Monster_Simple.uasset' -> '/Game/Characters/BP_Monster_Simple'"""
    base_filename = os.path.splitext(relative_filepath)[0]
    return base_filename.replace("Content/", "/Game/", 1)

def package_name_to_relative_filepath(package_name, ext):
    """usage) SkeletalMesh'"/Game/Characters/BP_Monster_Simple.BP_Monster_Simple"' -> 'Content/Characters/BP_Monster_Simple.uasset'"""
    asset_path = package_name_to_asset_path(package_name)
    return asset_path.replace("/Game/", "Content/", 1) + ext

def asset_path_to_relative_filepath(asset_path, ext):
    """usage) '/Game/Characters/BP_Monster_Simple' -> 'Content/Characters/BP_Monster_Simple.uasset'"""
    return asset_path.replace("/Game/", "Content/", 1) + ext

def copy_file(src_filepath, dst_filepath, use_source_control=False):
    try:
        if not os.path.exists(src_filepath):
            logging.info(f'Failed to copy_file: not exists {src_filepath}')
            return False
        
        # make directory
        dst_directory = os.path.split(dst_filepath)[0]
        if not os.path.exists(dst_directory):
            os.makedirs(dst_directory)

        # make writable
        was_file_exists = os.path.exists(dst_filepath)
        if was_file_exists:
            os.chmod(dst_filepath, stat.S_IWRITE)   
        shutil.copy(src_filepath, dst_filepath)
        if not was_file_exists:
            os.chmod(dst_filepath, stat.S_IWRITE)

        if use_source_control:
            unreal.SourceControl.check_out_or_add_file(dst_filepath)
        logging.info(f'copy_file: {src_filepath} to {dst_filepath}')
        return True
    except:
        logging.error(f'Failed to copy_file: {src_filepath} to {dst_filepath}')
    return False

def write_to_file(filepath, content, use_source_control=False):
    try:
        dirname = os.path.split(filepath)[0]
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        if os.path.exists(filepath):
            os.chmod(filepath, stat.S_IWRITE)
        with open(filepath, 'w') as f:
            f.write(content)
        if use_source_control:
            unreal.SourceControl.check_out_or_add_file(filepath)
        logging.info(f'write_to_file: {filepath}')
        return True
    except:
        logging.error(f'failed to write_to_file: {filepath}')
    return False

def export_to_unreal_text(filepath, asset, use_source_control=False):
    try:
        dirname = os.path.split(filepath)[0]
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        if os.path.exists(filepath):
            os.chmod(filepath, stat.S_IWRITE)

        export_task = unreal.AssetExportTask()
        export_task.automated = True
        export_task.prompt = False 
        export_task.filename = filepath
        export_task.object = asset
        unreal.Exporter.run_asset_export_task(export_task)

        if use_source_control:
            unreal.SourceControl.check_out_or_add_file(filepath)
        logging.info(f'export_to_unreal_text: {filepath}')
        return True
    except:
        logging.error(f'failed to export_to_unreal_text: {filepath}')
    return False


# TODO - unreal, python version wrapper
def __try_relative_to__(path, ignore_folder):
    try:
        return bool(path.relative_to(ignore_folder))
    except:
        pass
    return False

def __path_is_relative_to__(path, ignore_folder):
    return path.is_relative_to(ignore_folder)

__func_is_relative_to__ = __path_is_relative_to__ if hasattr(pathlib.Path, 'is_relative_to') else __try_relative_to__
    
def check_ignore_folders(filepath, ignore_folders):
    if ignore_folders:
        path = pathlib.Path(filepath)        
        for ignore_folder in ignore_folders:            
            if __try_relative_to__(path, ignore_folder):
                return True
    return False


def convert_string_to_linear_color(string_value):
    return unreal.StringLibrary.conv_string_to_color(string_value)

def convert_string_to_color(string_value, use_srgb = True):
    color, is_valid = convert_string_to_linear_color(string_value)
    return (unreal.Color(color.b, color.g, color.r, color.a), is_valid)


unreal_shading_model_map = {
    'MSM_ClearCoat': unreal.MaterialShadingModel.MSM_CLEAR_COAT,
    'MSM_Cloth': unreal.MaterialShadingModel.MSM_CLOTH,
    'MSM_DefaultLit': unreal.MaterialShadingModel.MSM_DEFAULT_LIT,
    'MSM_Eye': unreal.MaterialShadingModel.MSM_EYE,
    'MSM_FromMaterialExpression': unreal.MaterialShadingModel.MSM_FROM_MATERIAL_EXPRESSION,
    'MSM_Hair': unreal.MaterialShadingModel.MSM_HAIR,
    'MSM_PreintegratedSkin': unreal.MaterialShadingModel.MSM_PREINTEGRATED_SKIN,
    'MSM_SingleLayerWater': unreal.MaterialShadingModel.MSM_SINGLE_LAYER_WATER,
    'MSM_Subsurface': unreal.MaterialShadingModel.MSM_SUBSURFACE,
    'MSM_SubsurfaceProfile': unreal.MaterialShadingModel.MSM_SUBSURFACE_PROFILE,
    'MSM_ThinTranslucent': unreal.MaterialShadingModel.MSM_THIN_TRANSLUCENT,
    'MSM_TwoSidedFoliage': unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE,
    'MSM_Unlit': unreal.MaterialShadingModel.MSM_UNLIT,
}

unreal_blend_mode_map = {
    'BLEND_Additive': unreal.BlendMode.BLEND_ADDITIVE,
    'BLEND_AlphaComposite': unreal.BlendMode.BLEND_ALPHA_COMPOSITE,
    'BLEND_AlphaHoldout': unreal.BlendMode.BLEND_ALPHA_HOLDOUT,
    'BLEND_Masked': unreal.BlendMode.BLEND_MASKED,
    'BLEND_Modulate': unreal.BlendMode.BLEND_MODULATE,
    'BLEND_Opaque': unreal.BlendMode.BLEND_OPAQUE,
    'BLEND_Translucent': unreal.BlendMode.BLEND_TRANSLUCENT,
    'BLEND_TranslucentColoredTransmittance': unreal.BlendMode.BLEND_TRANSLUCENT_COLORED_TRANSMITTANCE,
}

def convert_string_to_animation_mode(string_value):
    if 'AnimationBlueprint' == string_value:
        return (unreal.AnimationMode.ANIMATION_BLUEPRINT, True)
    elif 'AnimationSingleNode' == string_value:
        return (unreal.AnimationMode.ANIMATION_SINGLE_NODE, True)
    elif 'AnimationCustomMode' == string_value:
        return (unreal.AnimationMode.ANIMATION_CUSTOM_MODE, True)
    logging.error(f'Unknown animation mode: {string_value}')
    return (unreal.AnimationMode.ANIMATION_BLUEPRINT, False)

def convert_string_to_detail_mode(string_value):
    if 'DM_Epic' == string_value:
        return (unreal.DetailMode.DM_EPIC, True)
    elif 'DM_High' == string_value:
        return (unreal.DetailMode.DM_HIGH, True)
    elif 'DM_Medium' == string_value:
        return (unreal.DetailMode.DM_MEDIUM, True)
    elif 'DM_Low' == string_value:
        return (unreal.DetailMode.DM_LOW, True)
    logging.error(f'Unknown detail mode: {string_value}')
    return (unreal.DetailMode.DM_LOW, False)

def convert_string_to_mobility(string_value):
    if 'Movable' == string_value:
        return (unreal.ComponentMobility.MOVABLE, True)
    elif 'Movable' == string_value:
        return (unreal.ComponentMobility.STATIC, True)
    elif 'Movable' == string_value:
        return (unreal.ComponentMobility.STATIONARY, True)
    logging.error(f'Unknown mobility: {string_value}')
    return (unreal.ComponentMobility.MOVABLE, False)
    
def convert_string_to_light_intensit_unit(string_value):
    if 'Candelas' == string_value:
        return (unreal.LightUnits.CANDELAS, True)
    elif 'Ev' == string_value:
        return (unreal.LightUnits.EV, True)
    elif 'Lumens' == string_value:
        return (unreal.LightUnits.LUMENS, True)
    elif 'Unitless' == string_value:
        return (unreal.LightUnits.UNITLESS, True)
    logging.error(f'Unknown light intensity unit: {string_value}')
    return (unreal.LightUnits.UNITLESS, False)


# (Pitch=0.000000,Yaw=0.000000,Roll=0.000000) -> (P=0.000000,Y=0.000000,R=0.000000)
def convert_string_to_rotation(rotation_string):
    rotation_string = rotation_string.replace('Pitch', 'P')
    rotation_string = rotation_string.replace('Yaw', 'Y')
    rotation_string = rotation_string.replace('Roll', 'R')
    return unreal.StringLibrary.conv_string_to_rotator(rotation_string)


def set_override_materials(component, component_uobject):
    material_paths = component_uobject.get_value('OverrideMaterials', [])
    for (i, material_path) in enumerate(material_paths):
        if material_path:
            asset_path = package_name_to_asset_path(material_path)
            if asset_path and unreal.EditorAssetLibrary.does_asset_exist(asset_path):
                material = unreal.EditorAssetLibrary.load_asset(asset_path)
                if material is not None:
                    #logging.info(f'set_material[{i}]: {asset_path}')
                    component.set_material(i, material)


def set_asset_to_component(component, component_uobject, asset_property_name):
    asset_package_name = component_uobject.get_value(asset_property_name, '')
    if asset_package_name:
        asset_path = package_name_to_asset_path(asset_package_name)
        if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
            component_asset = unreal.EditorAssetLibrary.load_asset(asset_path)
            if component_asset is not None:
                component.set_editor_property(asset_property_name, component_asset)


def set_animation_data(component, component_uobject):
    (animation_mode, is_valid) = convert_string_to_animation_mode(component_uobject.get_value('AnimationMode', ''))
    if not animation_mode or not is_valid:
        return
    
    component.set_animation_mode(animation_mode)
    if animation_mode is unreal.AnimationMode.ANIMATION_BLUEPRINT:
        animation_class_path = component_uobject.get_value('AnimClass', '')
        if animation_class_path:
            asset_path = class_name_to_asset_path(animation_class_path)
            if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
                anim_class = unreal.EditorAssetLibrary.load_asset(asset_path)
                if anim_class is not None:
                    component.set_anim_class(anim_class)
                    #logging.info(f'set_anim_class: {asset_path}')
    elif animation_mode is unreal.AnimationMode.ANIMATION_SINGLE_NODE:
        animation_data = component_uobject.get_value('AnimationData', '')
        if animation_data:            
            asset_path = package_name_to_asset_path(animation_data)
            if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
                anim_montage = unreal.EditorAssetLibrary.load_asset(asset_path)
                if anim_montage is not None:
                    component.animation_data.anim_to_play = anim_montage
                    #logging.info(f'anim_to_play: {asset_path}')
    else:
        logging.error(f'Unknown AnimationMode: {animation_mode}')