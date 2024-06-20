import logging
import traceback
from utility import *

import unreal


def set_editor_property(source_component, property_name, sub_object, editor_property_name, convert_method, check_is_valid):
    property_value = source_component.get_value(property_name)
    if property_value is not None:
        is_valid = True
        value = property_value
        if convert_method is not None:
            if check_is_valid:
                value, is_valid = convert_method(property_value)
            else:
                value = convert_method(property_value)
        
        if is_valid:
            sub_object.set_editor_property(editor_property_name, value)
            return True
    return False

    
def set_point_light_properties(sub_object, source_component):    
    set_editor_property(source_component, 'IntensityUnits', sub_object, 'intensity_units', convert_string_to_light_intensit_unit, True)
    set_editor_property(source_component, 'AttenuationRadius', sub_object, 'attenuation_radius', None, False)
    set_editor_property(source_component, 'MaxDrawDistance', sub_object, 'max_draw_distance', None, False)
    set_editor_property(source_component, 'MaxDistanceFadeRange', sub_object, 'max_distance_fade_range', None, False)
    set_editor_property(source_component, 'ContactShadowLength', sub_object, 'contact_shadow_length', None, False)
    set_editor_property(source_component, 'Intensity', sub_object, 'intensity', None, False)
    set_editor_property(source_component, 'LightColor', sub_object, 'light_color', convert_string_to_color, True)
    set_editor_property(source_component, 'CastShadows', sub_object, 'cast_shadows', None, False)
    set_editor_property(source_component, 'CastStaticShadows', sub_object, 'cast_static_shadows', None, False)
    set_editor_property(source_component, 'CastDynamicShadows', sub_object, 'cast_dynamic_shadows', None, False)
    set_editor_property(source_component, 'VolumetricScatteringIntensity', sub_object, 'volumetric_scattering_intensity', None, False)
    set_editor_property(source_component, 'Mobility', sub_object, 'mobility', convert_string_to_mobility, True)
    set_editor_property(source_component, 'DetailMode', sub_object, 'detail_mode', convert_string_to_detail_mode, True)

def CustomBP_to_Blueprint(migrate_tool, subsystem, blueprint_library, package_name, uobject, blueprint):
    logging.info(f'CustomBP_to_Blueprint: {package_name}')

    # clean-up
    subobject_data_handles = subsystem.k2_gather_subobject_data_for_blueprint(blueprint)    
    bp_handle = subobject_data_handles[0]    
    subsystem.delete_subobjects(bp_handle, subobject_data_handles, blueprint)

    # refresh sub handles
    subobject_data_handles = subsystem.k2_gather_subobject_data_for_blueprint(blueprint)
    # 0: actor_handle, 1: default_scene_root_handle
    bp_handle = subobject_data_handles[0]
    default_scene_root_handle = subobject_data_handles[1]

    # make blueprint subobjects
    ignore_distance_field_shadow_mesh = True
    unknown_classes = []
    part_infos = uobject.get_value('Parts')    
    for (i, part_info) in enumerate(part_infos):
        m_part_info = re_split_package_name.match(part_info)
        part_type = ''
        part_name = ''
        children = []
        if m_part_info:
            part_type, part_name = m_part_info.groups()        
            children = uobject.get_children_by_attribute('Name', part_name)

        for child in children:
            sub_object_name = child.get_value('Name', '')

            # ignore mesh for distance field shadow
            if ignore_distance_field_shadow_mesh and sub_object_name.endswith('_DFS'):
                continue

            # make subobject component
            if child.has_value('SourceComponent'):
                source_components = child.get_children_by_attribute('Name', 'SourceComponent')
                for source_component in source_components:
                    new_class = None
                    if 'CustomBPStaticMeshPart' == part_type:
                        new_class = unreal.StaticMeshComponent
                    elif 'CustomBPSkeletalMeshPart' == part_type:
                        new_class = unreal.SkeletalMeshComponent
                    elif 'CustomBPParticlePart' == part_type:
                        new_class = unreal.ParticleSystemComponent
                    elif 'CustomBPDecalPart' == part_type:
                        new_class = unreal.DecalComponent
                    elif 'CustomBPPointLightPart' == part_type:
                        new_class = unreal.PointLightComponent
                    else:
                        unknown_classes.append(part_type)

                    # create sub object component
                    if new_class:
                        # add component
                        params = unreal.AddNewSubobjectParams(parent_handle=default_scene_root_handle, new_class=new_class, blueprint_context=blueprint)
                        sub_handle, fail_reason = subsystem.add_new_subobject(params)
                        if not fail_reason.is_empty():
                            logging.error(f"ERROR: from sub_object_subsystem.add_new_subobject: {fail_reason}")
                            continue

                        sub_data = blueprint_library.get_data(sub_handle)
                        sub_object = blueprint_library.get_object(sub_data)
                        if sub_object is None:
                            continue
                        
                        # set common properties
                        if sub_object_name:
                            subsystem.rename_subobject(sub_handle, sub_object_name)
                        set_editor_property(source_component, 'bVisible', sub_object, 'visible', None, False)
                        set_editor_property(source_component, 'bHiddenInGame', sub_object, 'hidden_in_game', None, False)
                        set_editor_property(source_component, 'RelativeLocation', sub_object, 'RelativeLocation', unreal.StringLibrary.conv_string_to_vector, True)
                        set_editor_property(source_component, 'RelativeRotation', sub_object, 'RelativeRotation', convert_string_to_rotation, True)
                        set_editor_property(source_component, 'RelativeScale3D', sub_object, 'RelativeScale3D', unreal.StringLibrary.conv_string_to_vector, True)

                        # set specifiy data
                        try:
                            if 'CustomBPStaticMeshPart' == part_type:
                                set_asset_to_component(sub_object, source_component, 'StaticMesh')
                                set_override_materials(sub_object, source_component)
                            elif 'CustomBPSkeletalMeshPart' == part_type:
                                set_asset_to_component(sub_object, source_component, 'SkeletalMesh')
                                set_override_materials(sub_object, source_component)
                                set_animation_data(sub_object, source_component)
                            elif 'CustomBPParticlePart' == part_type:
                                set_asset_to_component(sub_object, source_component, 'Template')
                            elif 'CustomBPDecalPart' == part_type:
                                set_asset_to_component(sub_object, source_component, 'DecalMaterial')
                            elif 'CustomBPPointLightPart' == part_type:
                                set_point_light_properties(sub_object, source_component)
                            else:
                                logging.error(f'Unknown CustomBPPartType({part_name}): {part_type}')
                        except:
                            logging.error(f'{package_name}:{traceback.format_exc()}')
    if unknown_classes:
        unknown_classes = set(unknown_classes)
        logging.error(f"unknown_classes: {unknown_classes}")
    
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
