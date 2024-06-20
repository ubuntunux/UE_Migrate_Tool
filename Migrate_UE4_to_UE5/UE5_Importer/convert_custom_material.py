import logging
import re

import utility

import unreal


re_overrides = re.compile('\((.+?)\)')
re_parameter_name = re.compile('Name="(.+?)"')
re_scalar_parameter = re.compile('ParameterValue=(.+?),')
re_vector_parameters = re.compile('ParameterValue=(\(.+?\))')
re_texture_parameter = re.compile('ParameterValue=.+?\"(.+?)\"')
re_static_switch_values = re.compile('Value=(True|False)')
re_static_switch_names = re.compile('Name=\"(.+?)\"')


def set_override_properties(material_instacne, property_overrides_value):
    # gather override properties
    override_properties = {}
    override_property_names = []
    m_overrides = re_overrides.match(property_overrides_value)
    if m_overrides:
        override_items = m_overrides.groups()[0].split(',')
        for item in override_items:
            key, value = item.split('=')
            override_properties[key] = value
            # find override property
            if key.startswith('bOverride_') and value == 'True':
                override_property_names.append(key.replace('bOverride_', '', 1))

    # set override property
    material_instance_overrides = material_instacne.get_editor_property('base_property_overrides')
    if material_instance_overrides:
        for property_name in override_property_names:
            value = override_properties.get(property_name, None)
            if value is not None:
                if 'TwoSided' == property_name:
                    material_instance_overrides.set_editor_property('override_two_sided', True)
                    material_instance_overrides.set_editor_property('TwoSided', value == 'True')
                elif 'DitheredLODTransition' == property_name:
                    material_instance_overrides.set_editor_property('override_dithered_lod_transition', True)
                    material_instance_overrides.set_editor_property('DitheredLODTransition', value == 'True')
                elif 'OpacityMaskClipValue' == property_name:
                    material_instance_overrides.set_editor_property('override_opacity_mask_clip_value', True)
                    material_instance_overrides.set_editor_property('OpacityMaskClipValue', float(value))
                elif 'ShadingModel' == property_name:
                    material_instance_overrides.set_editor_property('override_shading_model', True)
                    shading_model = utility.unreal_shading_model_map.get(value, unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
                    material_instance_overrides.set_editor_property('ShadingModel', shading_model)
                elif 'BlendMode' == property_name:
                    material_instance_overrides.set_editor_property('override_blend_mode', True)
                    blend_mode = utility.unreal_blend_mode_map.get(value, unreal.BlendMode.BLEND_OPAQUE)
                    material_instance_overrides.set_editor_property('BlendMode', blend_mode)
                else:
                    logging.error(f'not implemented override property: {property_name}={value}')

                
def CustomUnrealMaterial_to_MaterialInstanceConstant(migrate_tool, package_name, uobject, material_instacne):
    logging.info(f'CustomUnrealMaterial_to_MaterialInstanceConstant: {package_name}')

    component_name = utility.package_name_to_asset_path(uobject.get_value('Parent', ''))
    component_uobjects = uobject.get_children_by_attribute('Name', component_name)
    for component_uobject in component_uobjects:
        parent_material_name = component_uobject.get_value('Parent')
        physical_material_name = component_uobject.get_value('PhysMaterial')
        property_overrides_value = component_uobject.get_value('BasePropertyOverrides')
        scalar_values = component_uobject.get_value('ScalarParameterValues', [])
        vector_values = component_uobject.get_value('VectorParameterValues', [])
        texture_values = component_uobject.get_value('TextureParameterValues', [])
        static_parameters = component_uobject.get_value('StaticParameters')

        if parent_material_name:      
            asset_path = utility.package_name_to_asset_path(parent_material_name)
            parent_material = unreal.EditorAssetLibrary.load_asset(asset_path)
            if parent_material:                
                unreal.MaterialEditingLibrary.set_material_instance_parent(material_instacne, parent_material)
        
        if physical_material_name:
            asset_path = utility.package_name_to_asset_path(physical_material_name)
            physical_material = unreal.EditorAssetLibrary.load_asset(asset_path)
            if physical_material:
                material_instacne.phys_material = physical_material
        
        if property_overrides_value:
            set_override_properties(material_instacne, property_overrides_value)
        
        for scalar_value in scalar_values:
            m = re_scalar_parameter.search(scalar_value)
            if m is not None:
                key = re_parameter_name.search(scalar_value).groups()[0]
                value = float(m.groups()[0])
                unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(material_instacne, key, value)

        for vector_value in vector_values:
            m = re_vector_parameters.search(vector_value)
            if m is not None:
                key = re_parameter_name.search(vector_value).groups()[0]
                value = unreal.StringLibrary.conv_string_to_color(m.groups()[0])
                unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(material_instacne, key, value[0])
        
        for texture_value in texture_values:
            m = re_texture_parameter.search(texture_value)
            if m is not None:
                key = re_parameter_name.search(texture_value).groups()[0]
                texture = unreal.EditorAssetLibrary.load_asset(m.groups()[0])
                unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(material_instacne, key, texture)

        if static_parameters:
            switch_names = re_static_switch_names.findall(static_parameters)
            switch_values = re_static_switch_values.findall(static_parameters)
            for (key, value) in zip(switch_names, switch_values):
                unreal.MaterialEditingLibrary.set_material_instance_static_switch_parameter_value(material_instacne, key, 'True' == value)
                
    # update material instances
    unreal.MaterialEditingLibrary.update_material_instance(material_instacne)
    return material_instacne