import logging
import os

import utility
import parsing_unreal_text

from .convert_custom_bp_actor_data import create_custom_bp_actor_data, CustomBP_ActorData_to_Blueprint

import unreal


def spawn_actor_custom_bp_or_actor(subsystem, blueprint_library, actor_label, actor_uobject, asset_type_name, folder_name):
    if actor_uobject.has_value(asset_type_name):
        asset_name = actor_uobject.get_value(asset_type_name)
        asset_path = utility.package_name_to_asset_path(asset_name)
        if asset_path:
            asset = unreal.EditorAssetLibrary.load_asset(asset_path)

            # check custom bp actor asset
            if asset_type_name == 'CustomBP_Actor':
                overwrite_custom_bp_actor = False
                if asset is None:
                    asset = create_custom_bp_actor_data(subsystem, blueprint_library, asset_path, actor_uobject)
                elif overwrite_custom_bp_actor:
                    CustomBP_ActorData_to_Blueprint(subsystem, blueprint_library, asset_path, actor_uobject, asset)

            if asset is not None:
                # spawn actor
                for component_uboject in actor_uobject.get_children_by_attribute('Name', 'BaseComponent'):
                    if component_uboject.has_value('RelativeLocation') or component_uboject.has_value('RelativeRotation') or component_uboject.has_value('RelativeScale3D'):
                        #logging.info(f'spawn_common_actor: {asset_type_name} {actor_label}')
                        location_and_is_valid = unreal.StringLibrary.conv_string_to_vector(component_uboject.get_value('RelativeLocation', ''))
                        rotation_and_is_valid = utility.convert_string_to_rotation(component_uboject.get_value('RelativeRotation', ''))
                        scale_and_is_valid = unreal.StringLibrary.conv_string_to_vector(component_uboject.get_value('RelativeScale3D', 'X=1.000 Y=1.000 Z=1.000'))
                        
                        actor = unreal.EditorLevelLibrary.spawn_actor_from_object(asset, location_and_is_valid[0], rotation_and_is_valid[0], False)
                        if scale_and_is_valid[1]:
                            actor.set_actor_scale3d(scale_and_is_valid[0])

                        actor.set_actor_label(actor_label)

                        if folder_name:
                            actor.set_folder_path(folder_name)
                        break

def spawn_common_actor(actor_label, actor_uobject, asset_type_name, folder_name):
    component_ubojects = actor_uobject.get_children_has_value(asset_type_name)
    if component_ubojects:
        component_uboject = component_ubojects[0]
        asset_name = component_uboject.get_value(asset_type_name)
        asset_path = utility.package_name_to_asset_path(asset_name)
        if asset_path:
            asset = unreal.EditorAssetLibrary.load_asset(asset_path)
            # spawn actor
            if asset is not None:
                #logging.info(f'spawn_common_actor: {asset_type_name} {actor_label}')
                location_and_is_valid = unreal.StringLibrary.conv_string_to_vector(component_uboject.get_value('RelativeLocation', ''))
                rotation_and_is_valid = utility.convert_string_to_rotation(component_uboject.get_value('RelativeRotation', ''))
                scale_and_is_valid = unreal.StringLibrary.conv_string_to_vector(component_uboject.get_value('RelativeScale3D', 'X=1.000 Y=1.000 Z=1.000'))

                actor = unreal.EditorLevelLibrary.spawn_actor_from_object(asset, location_and_is_valid[0], rotation_and_is_valid[0], False)

                if scale_and_is_valid[1]:
                    actor.set_actor_scale3d(scale_and_is_valid[0])

                if asset_type_name == 'StaticMesh':
                    utility.set_override_materials(actor.static_mesh_component, component_uboject)
                elif asset_type_name == 'SkeletalMesh':
                    utility.set_override_materials(actor.skeletal_mesh_component, component_uboject)
                    utility.set_animation_data(actor.skeletal_mesh_component, component_uboject)

                actor.set_actor_label(actor_label)

                if folder_name:
                    actor.set_folder_path(folder_name)


def spawn_actors_on_current_world(migrate_tool, subsystem, blueprint_library, root_uobject, clear_level=False, folder_name=''):
    logging.info(f'>>> Begin spawn_actors_on_current_world: {root_uobject.get_attribute("Name", "")}')
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if root_uobject:
        if clear_level:
            level_actors = unreal.EditorLevelLibrary.get_all_level_actors()
            actor_subsystem.destroy_actors(level_actors)
        
        # gather class uobject
        all_actor_uobjects = root_uobject.get_children_by_type('Actor', recursive=True)
        actor_class_map = {}
        for uobject in all_actor_uobjects:
            actor_class = uobject.get_attribute('Class', '')
            if actor_class not in actor_class_map:
                actor_class_map[actor_class] = []
            actor_class_map[actor_class].append(uobject)
        
        # log
        class_names = list(actor_class_map.keys())
        class_names.sort()
        for class_name in class_names:
            logging.info(f'    {class_name}({len(actor_class_map[class_name])})')

        def execute_taks(task_name, uobjects, task_func, **kargs):
            num_frames = len(uobjects)
            with unreal.ScopedSlowTask(num_frames, task_name) as slow_task:
                slow_task.make_dialog(True)
                for actor_uobject in uobjects:
                    actor_label = actor_uobject.get_value('ActorLabel', actor_uobject.get_attribute('Name', ''))
                    slow_task.enter_progress_frame(1)
                    task_func(actor_label=actor_label, actor_uobject=actor_uobject, **kargs)

        custom_bp_actor_uobjects = actor_class_map.get('/Script/CustomScene.CustomBP_Actor', [])
        custom_bp_uobjects = actor_class_map.get('/Script/CustomScene.CustomBPActor', [])
        emitter_uobjects = actor_class_map.get('/Script/Engine.Emitter', [])
        skeletal_mesh_uobjects = actor_class_map.get('/Script/Engine.SkeletalMeshActor', [])
        static_mesh_uobjects = actor_class_map.get('/Script/Engine.StaticMeshActor', [])
        decal_uobjects = actor_class_map.get('/Script/Engine.DecalActor', [])
        
        execute_taks('adding StaticMeshes...', static_mesh_uobjects, spawn_common_actor, asset_type_name='StaticMesh', folder_name=folder_name)
        execute_taks('adding SkeletalMesh...', skeletal_mesh_uobjects, spawn_common_actor, asset_type_name='SkeletalMesh', folder_name=folder_name)
        execute_taks('adding DecalMaterial...', decal_uobjects, spawn_common_actor, asset_type_name='DecalMaterial', folder_name=folder_name)
        execute_taks('adding Emitter...', emitter_uobjects, spawn_common_actor, asset_type_name='Template', folder_name=folder_name)
        execute_taks('adding CustomBPs...', custom_bp_uobjects, spawn_actor_custom_bp_or_actor, subsystem=subsystem, blueprint_library=blueprint_library, asset_type_name='CustomBP', folder_name=folder_name)
        execute_taks('adding CustomBP_Actors...', custom_bp_actor_uobjects, spawn_actor_custom_bp_or_actor, subsystem=subsystem, blueprint_library=blueprint_library, asset_type_name='CustomBP_Actor', folder_name=folder_name)
    logging.info(f'>>> End spawn_actors_on_current_world: {root_uobject.get_attribute("Name", "")}')


def gather_world_filepaths(migrate_tool, subsystem, blueprint_library, clear_level, filter_world_filepaths, category_object, parent_category_name, world_filepath_map):
    category_name = category_object.get_value("CategoryName", "")
    if parent_category_name:
        category_name = f'{parent_category_name}/{category_name}'        
    category_level_object_names = category_object.get_value('Levels', [])
    subcategory_object_names = category_object.get_value('Subcategories', [])
    logging.info(f'{category_object.get_attribute("Name")}: CategoryName={category_name}, Levels({len(category_level_object_names)}), Subcategories({len(subcategory_object_names)})')

    # gather worlds
    world_filepaths = []
    for category_level_object_name in category_level_object_names:
        category_level_asest_path = utility.package_name_to_asset_path(category_level_object_name)
        category_level_objects = category_object.get_children_by_attribute('Name', category_level_asest_path)
        for category_level_object in category_level_objects:
            level_asset_path = category_level_object.get_value('LevelPackageName')
            if level_asset_path:
                # filter - exported world filepaths
                relative_filepath = utility.asset_path_to_relative_filepath(level_asset_path, '.T3D')
                if relative_filepath in filter_world_filepaths:
                    world_filepaths.append(os.path.join(migrate_tool.intermediate_dircetory, relative_filepath))
    world_filepath_map[category_name] = world_filepaths

    # revursive
    for subcategory_object_name in subcategory_object_names:
        subcategory_asset_path = utility.package_name_to_asset_path(subcategory_object_name)
        subcategory_objects = category_object.get_children_by_attribute('Name', subcategory_asset_path)
        for subcategory_object in subcategory_objects:
            gather_world_filepaths(migrate_tool, subsystem, blueprint_library, clear_level, filter_world_filepaths, subcategory_object, category_name, world_filepath_map)


def convert_world_partition(migrate_tool, subsystem, blueprint_library, root_uobject, clear_level=False):
    logging.info(f'convert_world_partition: {root_uobject.get_attribute("Name", "")}')

    # gather level infos
    level_infos = []
    for level_asset_name in root_uobject.get_value('LevelInfos'):
        asset_path = utility.package_name_to_asset_path(level_asset_name)
        if asset_path:
            for child in root_uobject.get_children_by_attribute('Name', asset_path):
                if child.has_value('LevelPackageName'):
                    level_infos.append(child)
    
    # gather world filepaths
    filter_world_filepaths = migrate_tool.get_exported_filelist('World')
    category_name = ''
    root_categories = root_uobject.get_children_by_attribute('Name', 'RootCategory')
    world_filepath_map = {} # { category_name: [levels] }
    for root_category in root_categories:
        gather_world_filepaths(migrate_tool, subsystem, blueprint_library, clear_level, filter_world_filepaths, root_category, category_name, world_filepath_map)

    # spawn_actors_on_current_world
    task_name = 'spawn_actors_on_current_world'
    task_num = sum([len(files) for files in world_filepath_map.values()])
    with unreal.ScopedSlowTask(task_num, task_name) as slow_task:
        slow_task.make_dialog(True)
        for (category_name, world_filepaths) in world_filepath_map.items():
            for world_filepath in world_filepaths:
                slow_task.enter_progress_frame(1)
                world_uobject = parsing_unreal_text.parser_unreal_text_file(world_filepath)
                if world_uobject:
                    name = os.path.split(world_uobject.get_attribute('Name'))[1]
                    level_categoty = '/'.join([category_name, name])
                    spawn_actors_on_current_world(migrate_tool, subsystem, blueprint_library, world_uobject, clear_level, level_categoty)