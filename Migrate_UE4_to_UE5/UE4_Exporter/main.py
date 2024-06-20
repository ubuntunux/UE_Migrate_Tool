import logging
import os
import json
import utility

import unreal


def export_project_info(migrate_tool):
    logging.info(">>> export_project_info...")
    src_project_info = {
        'project_directory': migrate_tool.project_dircetory,
        'engine_version': unreal.SystemLibrary.get_engine_version()
    }
    utility.write_to_file(filepath=migrate_tool.src_project_info_filepath, content=json.dumps(src_project_info, indent=4))


def export_asset_file_list(migrate_tool, class_name, ext, ignore_folders):    
    assets = migrate_tool.get_assets_by_class(class_name)
    logging.info(f'>>> Begin export_asset_file_list: {class_name}({len(assets)})')
    if assets is not None:
        total_num = len(assets)
        file_list = []
        task_name = f'export_asset_file_list: {class_name}'
        with unreal.ScopedSlowTask(total_num, task_name) as slow_task:
            slow_task.make_dialog(True)
            for (i, asset_data) in enumerate(assets):
                slow_task.enter_progress_frame(1)
                package_name = str(asset_data.package_name)
                if package_name.startswith('/Game/'):
                    relative_filepath = package_name.replace("/Game/", "Content/", 1) + ext
                    if utility.check_ignore_folders(relative_filepath, ignore_folders):
                        logging.info(f'ignored: {relative_filepath}')
                    else:
                        logging.info(f'export: {relative_filepath}')
                        file_list.append(relative_filepath)        # write to file
        file_list.sort()
        export_data = "\n".join(file_list)
        export_filepath = migrate_tool.get_export_filepath(class_name)
        utility.write_to_file(filepath=export_filepath, content=export_data)
    logging.info(f'>>> End export_asset_file_list: {class_name}')


def export_assets(migrate_tool, class_name, ext, ignore_folders, overwrite=True):
    assets = migrate_tool.get_assets_by_class(class_name)
    logging.info(f'>>> Begin export_assets: {class_name}({len(assets)})')
    if assets is not None:        
        total_num = len(assets)
        task_name = f'export_assets: {class_name} {ext}'
        with unreal.ScopedSlowTask(total_num, task_name) as slow_task:
            slow_task.make_dialog(True)
            for (i, asset_data) in enumerate(assets):
                slow_task.enter_progress_frame(1)
                asset = asset_data.get_asset()
                if asset_data.is_valid() and asset is not None:
                    relative_filepath = str(asset_data.package_name)
                    if relative_filepath.startswith('/Game/'):                        
                        relative_filepath = relative_filepath.replace("/Game/", "Content/", 1) + ext
                    
                    source_filepath = os.path.join(migrate_tool.project_dircetory, relative_filepath)
                    export_filepath = os.path.join(migrate_tool.intermediate_dircetory, relative_filepath)

                    if utility.check_ignore_folders(relative_filepath, ignore_folders):
                        logging.info(f'ignored: {relative_filepath}')
                        continue

                    # check overwrite
                    is_file_exists = os.path.exists(export_filepath)
                    if not overwrite and is_file_exists:
                        logging.info(f'not overwrite: {export_filepath}')
                        continue

                    utility.copy_file(source_filepath, export_filepath)
    logging.info(f'>>> End export_assets: {class_name}')


def export_assets_to_unreal_text(migrate_tool, class_name, ext, ignore_folders, overwrite=True):    
    assets = migrate_tool.get_assets_by_class(class_name)
    logging.info(f'>>> Begin export_assets_to_unreal_text: {class_name}({len(assets)})')
    if assets is not None:        
        total_num = len(assets)
        task_name = f'export_assets_to_unreal_text: {class_name}'
        with unreal.ScopedSlowTask(total_num, task_name) as slow_task:
            slow_task.make_dialog(True)
            for (i, asset_data) in enumerate(assets):
                slow_task.enter_progress_frame(1)       
                asset = asset_data.get_asset()
                if asset_data.is_valid() and asset is not None:
                    relative_filepath = str(asset_data.package_name)
                    if relative_filepath.startswith('/Game/'):
                        relative_filepath = relative_filepath.replace("/Game/", "Content/", 1) + ext
                    
                    if utility.check_ignore_folders(relative_filepath, ignore_folders):
                        logging.info(f'ignored: {relative_filepath}')
                        continue

                    export_filepath = os.path.join(migrate_tool.intermediate_dircetory, relative_filepath)

                    # check overwrite
                    is_file_exists = os.path.exists(export_filepath)
                    if not overwrite and is_file_exists:
                        logging.info(f'not overwrite: {export_filepath}')
                        continue

                    utility.export_to_unreal_text(export_filepath, asset)
    logging.info(f'>>> Begin export_assets_to_unreal_text: {class_name}')


# Excute Exporter
def execute(migrate_tool, copy_class_names, unreal_text_class_names, clean_up_class_names, save_class_names, ignore_folders):
    export_project_info(migrate_tool)

    # Export assets
    for class_name in copy_class_names:
        ext = ".uasset"
        if class_name == 'World':
            ext = '.umap'
        export_asset_file_list(migrate_tool, class_name, ext, ignore_folders)
        export_assets(migrate_tool, class_name, ext, ignore_folders)
    
    # Export .uasset to text
    for class_name in unreal_text_class_names:
        ext = ".T3D"
        export_asset_file_list(migrate_tool, class_name, ext, ignore_folders)
        export_assets_to_unreal_text(migrate_tool, class_name, ext, ignore_folders, overwrite=False)
