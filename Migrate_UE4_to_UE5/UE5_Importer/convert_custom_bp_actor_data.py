import logging
import os
import re

from utility import *

import unreal


def CustomBP_ActorData_to_Blueprint(subsystem, blueprint_library, package_name, uobject, blueprint):
    logging.info(f'CustomBP_ActorData_to_Blueprint: {package_name}')

    # clean-up
    subobject_data_handles = subsystem.k2_gather_subobject_data_for_blueprint(blueprint)    
    bp_handle = subobject_data_handles[0]    
    subsystem.delete_subobjects(bp_handle, subobject_data_handles, blueprint)

    # refresh sub handles
    subobject_data_handles = subsystem.k2_gather_subobject_data_for_blueprint(blueprint)
    # 0: actor_handle, 1: default_scene_root_handle
    bp_handle = subobject_data_handles[0]
    default_scene_root_handle = subobject_data_handles[1]
    
    sub_object_name = "SourceComponent"    
    component_asset_path = None
    component_types = ['CustomBP', 'StaticMesh', 'SkeletalMesh']
    for component_type in component_types:
        component_asset_path = uobject.get_value(component_type)
        if component_asset_path is not None:
            break
    else:
        logging.error(f"ERROR: not found custom bp actor component type: {package_name}")
        return None

    if component_asset_path:
        asset_package_name = ''
        match_package_name = re_package_name.match(component_asset_path)
        if match_package_name:
            asset_package_name = match_package_name.groups()[0]
        
        new_class = None
        asset_editor_property_name = ''
        if 'CustomBP' == component_type:
            new_class = unreal.ChildActorComponent
            asset_editor_property_name = 'ChildActorClass'
        elif 'StaticMesh' == component_type:
            new_class = unreal.StaticMeshComponent
            asset_editor_property_name = 'StaticMesh'               
        elif 'SkeletalMesh' == component_type:
            new_class = unreal.SkeletalMeshComponent
            asset_editor_property_name = 'SkeletalMesh'
        else:
            logging.error(f"ERROR: not implemented custom bp actort component type({package_name}): {component_type}")
            return None

        # create sub object component
        if asset_package_name and new_class:
            params = unreal.AddNewSubobjectParams(parent_handle=default_scene_root_handle, new_class=new_class, blueprint_context=blueprint)
            sub_handle, fail_reason = subsystem.add_new_subobject(params)
            if not fail_reason.is_empty():
                logging.info(f"ERROR: from sub_object_subsystem.add_new_subobject: {fail_reason}")
                return None

            sub_data = blueprint_library.get_data(sub_handle)
            sub_object = blueprint_library.get_object(sub_data)
            if sub_object is None:
                return None
            
            # set properties
            subsystem.rename_subobject(sub_handle, sub_object_name)
            asset_path = package_name_to_asset_path(asset_package_name)
            if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
                sub_object_asset = unreal.EditorAssetLibrary.load_asset(asset_path)
                if sub_object_asset is not None:
                    value = sub_object_asset.generated_class() if 'ChildActorClass' == asset_editor_property_name else sub_object_asset
                    sub_object.set_editor_property(asset_editor_property_name, value)
            is_hidden = uobject.get_value('bHidden')
            if is_hidden is not None:
                sub_object.set_editor_property('visible', is_hidden)
            
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)


def create_custom_bp_actor_data(subsystem, blueprint_library, asset_path, uobject):
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    blueprint_factory = unreal.BlueprintFactory()
    blueprint_factory.set_editor_property("ParentClass", unreal.Actor)
    asset_folder, asset_name = os.path.split(asset_path)    
    uasset = asset_tools.create_asset(asset_name, asset_folder, None, blueprint_factory)

    CustomBP_ActorData_to_Blueprint(subsystem, blueprint_library, asset_path, uobject, uasset)

    return uasset
