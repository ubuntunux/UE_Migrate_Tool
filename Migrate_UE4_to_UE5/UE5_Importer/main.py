import importlib
import os
import logging
import shutil
import stat
import utility

import parsing_unreal_text
import widgets

# reload modules
from . import convert_custom_bp_actor_data
importlib.reload(convert_custom_bp_actor_data)

from . import convert_level_sequence
importlib.reload(convert_level_sequence)

from . import convert_custom_bp
importlib.reload(convert_custom_bp)

from . import convert_custom_material
importlib.reload(convert_custom_material)

from . import world_partition_builder
importlib.reload(world_partition_builder)

import unreal


def create_or_load_asset(asset_tools, package_name, asset_class, factory):
    uasset = unreal.EditorAssetLibrary.load_asset(package_name)
    if uasset is None:    
        asset_folder, asset_name = os.path.split(package_name)    
        uasset = asset_tools.create_asset(asset_name, asset_folder, asset_class, factory)
    return uasset

def create_or_load_world(asset_tools, package_name):
    if unreal.EditorAssetLibrary.does_asset_exist(package_name):
        result = unreal.EditorLevelLibrary.load_level(package_name)
        logging.info(f'Load Level {package_name}: {result}')
    else:
        result = unreal.EditorLevelLibrary.new_level(package_name)
        logging.info(f'New Level {package_name}: {result}')
        

def import_project_info(migrate_tool):
    logging.info("import_project_info...")
    src_project_info = {}
    with open(migrate_tool.src_project_info_filepath, 'r') as f:
        src_project_info = eval(f.read())
    return src_project_info


def import_assets(migrate_tool, class_name, ignore_folders, available_source_control, overwrite=True):
    logging.info(f">>> Begin copy_assets: {class_name}")
    filepath_list = migrate_tool.get_exported_filelist(class_name)
    total_num = len(filepath_list)
    task_name = f'copy_assets: {class_name}'
    with unreal.ScopedSlowTask(total_num, task_name) as slow_task:
        slow_task.make_dialog(True)
        for (i, relative_filepath) in enumerate(filepath_list):
            slow_task.enter_progress_frame(1)
            if utility.check_ignore_folders(relative_filepath, ignore_folders):
                logging.info(f'ignored: {relative_filepath}')
                continue

            src_filepath = os.path.join(migrate_tool.intermediate_dircetory, relative_filepath)
            if os.path.exists(src_filepath):
                dst_filepath = os.path.join(migrate_tool.project_dircetory, relative_filepath)
                
                # check overwrite
                if not overwrite and os.path.exists(dst_filepath):
                    logging.info(f'not overwrite: {dst_filepath}')
                    continue
                    
                utility.copy_file(src_filepath, dst_filepath, available_source_control)
            else:
                logging.info(f'not found source: {src_filepath}')
    logging.info(f">>> End copy_assets: {class_name}")


def import_assets_from_unreal_text(migrate_tool, class_name, ignore_folders, available_source_control, overwrite=True):    
    logging.info(f">>> Begin import_assets_from_unreal_text: {class_name}")
    blueprint_library = unreal.SubobjectDataBlueprintFunctionLibrary()
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    filepath_list = migrate_tool.get_exported_filelist(class_name)
    total_num = len(filepath_list)
    task_name = f"import_assets_from_unreal_text : {class_name}"
    with unreal.ScopedSlowTask(total_num, task_name) as slow_task:
        slow_task.make_dialog(True)
        for (i, relative_filepath) in enumerate(filepath_list):
            slow_task.enter_progress_frame(1)
            relative_base_filename = os.path.splitext(relative_filepath)[0]
            relative_filepath = relative_base_filename + '.T3D'

            if utility.check_ignore_folders(relative_filepath, ignore_folders):
                logging.info(f'ignored: {relative_filepath}')
                continue

            intermediate_filepath = os.path.join(migrate_tool.intermediate_dircetory, relative_filepath)
            if os.path.exists(intermediate_filepath):
                package_name = utility.relative_filepath_to_asset_path(relative_filepath)

                # prepare to converting                
                uobject = parsing_unreal_text.parser_unreal_text_file(intermediate_filepath)
                uasset = None

                # covert unreal text to asset
                if uobject:                
                    if 'CustomUnrealMaterial' == class_name:
                        uasset = create_or_load_asset(asset_tools, package_name, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
                        convert_custom_material.CustomUnrealMaterial_to_MaterialInstanceConstant(migrate_tool, package_name, uobject, uasset)
                    elif 'LevelSequence' == class_name:
                        uasset = create_or_load_asset(asset_tools, package_name, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
                        convert_level_sequence.build_level_sequence(migrate_tool, package_name, uobject, uasset)
                    elif 'CustomBP' == class_name:
                        blueprint_factory = unreal.BlueprintFactory()
                        blueprint_factory.set_editor_property("ParentClass", unreal.Actor)
                        uasset = create_or_load_asset(asset_tools, package_name, None, blueprint_factory)
                        convert_custom_bp.CustomBP_to_Blueprint(migrate_tool, subsystem, blueprint_library, package_name, uobject, uasset)
                    elif 'WorldWorkspace' == class_name:
                        level_package_name = uobject.get_value('PersistentLevelPackageName')
                        create_or_load_world(asset_tools, level_package_name)
                        world_partition_builder.convert_world_partition(migrate_tool, subsystem, blueprint_library, uobject, clear_level=False)
                        success = unreal.EditorLevelLibrary.save_current_level()
                        logging.info(f'Save Level {level_package_name}: {level_package_name}')
                    elif 'World' == class_name:
                        create_or_load_world(asset_tools, package_name)
                        world_partition_builder.spawn_actors_on_current_world(migrate_tool, subsystem, blueprint_library, uobject, clear_level=True)
                        success = unreal.EditorLevelLibrary.save_current_level()
                        logging.info(f'Save Level {package_name}: {success}')
                    else:
                        logging.info(f'not implemented convert method for {class_name}: {package_name}')

                # save asset
                if uasset is not None:
                    unreal.EditorAssetLibrary.save_loaded_asset(uasset)
            else:
                logging.info(f'not found intermediate file: {intermediate_filepath}')
    logging.info(f">>> End import_assets_from_unreal_text: {class_name}")


def clean_up_assets(migrate_tool, class_name):
    logging.info(f'>>> Begin clean_up_assets: {class_name}')
    filepath_list = migrate_tool.get_exported_filelist(class_name)
    num_tasks = len(filepath_list)
    with unreal.ScopedSlowTask(num_tasks, class_name) as slow_task:
        slow_task.make_dialog(True)
        for (i, filepath) in enumerate(filepath_list):
            slow_task.enter_progress_frame(1)
            filepath = os.path.splitext(filepath)[0] + '.uasset'
            filepath = os.path.join(migrate_tool.project_dircetory, filepath)
            if os.path.exists(filepath):
                logging.info(f'remove: {filepath}')
                os.chmod(filepath, stat.S_IWRITE)
                os.remove(filepath)
    logging.info(f'>>> End clean_up_assets: {class_name}')


def save_assets(migrate_tool, class_name, only_if_is_dirty=False):
    logging.info(f'>>> Begin save_assets: {class_name}')
    assets = migrate_tool.get_assets_by_class(class_name)
    num_tasks = len(assets)
    with unreal.ScopedSlowTask(num_tasks, class_name) as slow_task:
        slow_task.make_dialog(True)
        for (i, asset_data) in enumerate(assets):
            slow_task.enter_progress_frame(1)
            asset = asset_data.get_asset()
            asset_path_name = asset.get_path_name()            
            if asset_path_name.startswith('/Game/'):
                logging.info(f'Save: {asset_path_name}')
                unreal.EditorAssetLibrary.load_asset(asset_path_name)
                unreal.EditorAssetLibrary.save_asset(asset_path_name, only_if_is_dirty=only_if_is_dirty)
    logging.info(f'>>> End save_assets: {class_name}')


# Excute Importer
def execute(migrate_tool, copy_class_names, unreal_text_class_names, clean_up_class_names, save_class_names, ignore_folders):
    available_source_control = False # unreal.SourceControl.is_available()
    
    # import project infomation
    src_project_info = import_project_info(migrate_tool) 
    src_project_dircetory = src_project_info.get('project_directory')
    
    # copy files list for each class
    for class_name in copy_class_names:
        import_assets(migrate_tool, class_name, ignore_folders, available_source_control, overwrite=True)

    # convert UnrealText(.T3D) files to .uasset
    for class_name in unreal_text_class_names:
        import_assets_from_unreal_text(migrate_tool, class_name, ignore_folders, available_source_control, overwrite=True)

    # save class assets
    for class_name in clean_up_class_names:
        clean_up_assets(migrate_tool, class_name)

    # save class assets
    for class_name in save_class_names:
        save_assets(migrate_tool, class_name, only_if_is_dirty=False)

    
