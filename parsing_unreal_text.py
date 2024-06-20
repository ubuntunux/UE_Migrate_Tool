import os
import re
import sys
import logging
from collections import OrderedDict

re_attribute = re.compile('(.+?)=(.+)')
re_attribute_array = re.compile('(.+?)\(\d+\)=(.+)')


class UnrealObject:
    def __init__(self, parent=None, depth=0):
        self.__unreal_text_filepath = ''
        self.parent = parent
        self.children = []
        self.attributes = OrderedDict()
        self.values = OrderedDict()
        self.extras = []
        self.type = 'Object'
        self.depth = depth
        
        # register global values
        self.root = parent.root if parent is not None else self
        self.global_id_map = parent.global_id_map if parent is not None else {}
        self.global_id_map[id(self)] = self
        
    def __str__(self):
        text_object = UnrealObject_to_Text(self)
        return text_object.get_text()

    def get_unreal_text_filepath(self):
        return self.__unreal_text_filepath

    def set_unreal_text_filepath(self, filepath):
        self.__unreal_text_filepath = filepath

    def is_root(self):
        return self is self.root

    def get_root(self):
        return self.root
    
    def get_parent(self):
        return self.parent

    def get_uobject_by_id(self, object_id):
        return self.global_id_map.get(object_id, None)        

    def add_child(self):
        child = UnrealObject(self, self.depth + 1)
        self.children.append(child)
        return child

    def get_child(self, index):
        return self.children[index] if index < len(self.children) else None

    def get_children(self):
        return self.children
    
    def get_children_by_attribute(self, key, value, recursive=False, result=None):
        if result is None:
            result=[]            
        for child in self.children:
            if child.has_attribute(key) and value == child.get_attribute(key):
                result.append(child)        
            if recursive:
                child.get_children_by_attribute(key, value, recursive, result)
        return result
    
    def get_children_has_attribute(self, key, recursive=False, result=None):
        if result is None:
            result=[]            
        for child in self.children:
            if child.has_attribute(key):
                result.append(child)        
            if recursive:
                child.get_children_has_attribute(key, recursive, result)
        return result
    
    def get_children_by_value(self, key, value, recursive=False, result=None):
        if result is None:
            result=[]
        for child in self.children:
            if child.has_value(key) and value == child.get_value(key):
                result.append(child)
            if recursive:
                child.get_children_by_value(key, value, recursive, result)
        return result
    
    def get_children_has_value(self, key, recursive=False, result=None):
        if result is None:
            result=[]
        for child in self.children:
            if child.has_value(key):
                result.append(child)
            if recursive:
                child.get_children_has_value(key, recursive, result)
        return result
    
    def get_children_by_type(self, type_name, recursive=False, result=None):
        if result is None:
            result=[]
        for child in self.children:
            if type_name == child.type:
                result.append(child)
            if recursive:
                child.get_children_by_type(type_name, recursive, result)
        return result
    
    def set_type(self, type_name):
        if type_name:
            self.type = type_name
    
    def has_attribute(self, key, default_value=None):
        return key in self.attributes.keys()
    
    def get_attribute(self, key, default_value=None):
        return self.attributes.get(key, default_value)

    def set_attribute(self, key, value):
        self.attributes[key] = value

    def has_value(self, key, default_value=None):
        return key in self.values.keys()

    def get_value(self, key, default_value=None):
        return self.values.get(key, default_value)

    def set_value(self, key, value):
        self.values[key] = value

    def add_extra_value(self, value):
        self.extras.append(value)

    def get_extra_value(self, index):
        return self.extras[index] if index < len(self.extras) else None


class UnrealObject_to_Text:
    def __init__(self, uobject):
        self.uobject = uobject

    def get_text(self):
        return self.gather_text(self.uobject)

    def gather_text(self, uobject, index=0, depth=0, text_list = None):
        if text_list is None:
            text_list = []
            
        gather_text_list = [
            f'{self.get_header_text(uobject, index, depth)}',
            self.text_adjust_tab(f'Attributes({len(uobject.attributes)}):', depth + 1),
            f'{self.get_attributes_text(uobject, depth + 2)}',
            self.text_adjust_tab(f'Values({len(uobject.values)}):', depth + 1),
            f'{self.get_values_text(uobject, depth + 2)}',
            self.text_adjust_tab(f'Extras({len(uobject.extras)}):', depth + 1),
            f'{self.get_extras_text(uobject, depth + 2)}'            
        ]
        
        gather_text_list = [text for text in gather_text_list if text]
        text = '\n'.join(gather_text_list)
        text_list.append(text)
        
        for (child_index, child) in enumerate(uobject.children):
            self.gather_text(child, child_index, depth + 1, text_list)

        end_text = self.text_adjust_tab(f'End {uobject.type}', depth)
        text_list.append(end_text)

        if 0 == depth:
            return '\n'.join(text_list)
        return text

    def text_adjust_tab(self, text, depth=0):
        tab = '    ' * depth
        if text:
            return tab + text
        return ''
        
    def text_adjust_tab_and_space(self, text_list, depth=0):
        tab = '    ' * depth
        text = ' '.join(text_list)
        if text:
            return tab + text
        return ''

    def text_adjust_tab_and_line(self, text_list, depth=0):
        tab = '    ' * depth
        text = '\n'.join([tab + text for text in text_list if text])
        return text
        
    def get_header_text(self, uobject, index=0, depth=0):
        text_list = [
            f'Begin {uobject.type}',
            f'id={id(uobject)}',
            f'index={index}',
            f'depth={uobject.depth}',
            f'children={len(uobject.children)}'
        ]
        return self.text_adjust_tab_and_space(text_list, depth)
        
    def get_attributes_text(self, uobject, depth=0):
        text_list = [f'{key}={value}' for (key, value) in uobject.attributes.items()]
        return self.text_adjust_tab_and_line(text_list, depth)

    def get_values_text(self, uobject, depth=0):
        text_list = []
        for (key, value) in uobject.values.items():
            if type(value) is list:
                if value:
                    text_list.append(f'{key}({len(value)}):')
                    for (i, x) in enumerate(value):
                        text_list.append(f'    [{i}]={x}')
            else:
                text_list.append(f'{key}={value}')
        return self.text_adjust_tab_and_line(text_list, depth)

    def get_extras_text(self, uobject, depth=0):
        text_list = [f'{value}' for value in uobject.extras]
        return self.text_adjust_tab_and_line(text_list, depth)


def load_unreal_text(intermediate_filepath):
    logging.info(f'load_unreal_text: {intermediate_filepath}')
    # read .t3d file
    unreal_text = ""
    encodings = ['utf-8', 'utf-16']
    for encoding in encodings:
        try:
             with open(intermediate_filepath, encoding=encoding) as f:
                unreal_text = f.read()
                break
        except:
            logging.info(f'failed to read: file:{intermediate_filepath}, encoding:{encoding}')
    else:
        logging.info(f'not found encoding: file:{intermediate_filepath}')
    return unreal_text


def evaluate_string(value_string):
    value = value_string
    try:
        value = eval(value)
    except:
        pass
    return value


def parse_attribute(uobject, attribute_string, is_attribute) -> bool:
    # element of array
    m_attribute_array = re_attribute_array.match(attribute_string)
    if m_attribute_array is not None:
        (key, value) = m_attribute_array.groups()  
        value = evaluate_string(value)        
        attribute_array = uobject.get_attribute(key, []) if is_attribute else uobject.get_value(key, [])
        attribute_array.append(value)
        if is_attribute:
            uobject.set_attribute(key, attribute_array)
        else:
            uobject.set_value(key, attribute_array)
        return True
        
    # single value
    m_attribute = re_attribute.match(attribute_string)
    if m_attribute is not None:        
        (key, value) = m_attribute.groups()
        value = evaluate_string(value)
        if is_attribute:
            uobject.set_attribute(key, value)
        else:
            uobject.set_value(key, value)
        return True

    # extra - values
    uobject.add_extra_value(attribute_string)
    return False
    

def parser_unreal_text(unreal_text) -> UnrealObject:
    contents = unreal_text.split('\n')
    logging.info(f'parser_unreal_text: {len(contents)} lines')
    uobject = None    
    for content in contents:
        content = content.strip()
        if content == "":
            continue

        tokens = content.split(' ')
        if tokens:
            head = tokens[0]
            if 'Begin' == head:
                if uobject is None:
                    uobject = UnrealObject()
                else:
                    uobject = uobject.add_child()
                    
                if 1 < len(tokens):
                    uobject.set_type(tokens[1])
                    for attribute in tokens[2:]:
                        parse_attribute(uobject, attribute, is_attribute=True)
            elif 'End' == head:
                if uobject.parent is not None:
                    uobject = uobject.get_parent()
            else:
                parse_attribute(uobject, content, is_attribute=False)
    return uobject


def parser_unreal_text_file(filepath) -> UnrealObject:
    ext = os.path.splitext(filepath)[1].lower()
    if os.path.exists(filepath) and ext in ['.t3d', '.copy']:
        unreal_text = load_unreal_text(filepath)        
        try:
            uobject = parser_unreal_text(unreal_text)
            if uobject:
                uobject.set_unreal_text_filepath(filepath)
            return uobject
        except:
            logging.info(f'failed to parser_unreal_text: {filepath}')
    return None


def example():
    unreal_text = """
    Begin Object Class=/Script/UnrealEd.SceneThumbnailInfo Name="CustomBPStaticMeshPart_146"
      Begin Object Name="SourceComponent"
         StaticMesh=StaticMesh'"/Game/Environment/Artificial/Common/BG_BaseBox_01_02_SM.BG_BaseBox_01_02_SM"'
         StaticMeshImportVersion=1
         RelativeLocation=(X=-1605.832275,Y=-1191.363281,Z=478.546143)
         RelativeRotation=(Pitch=0.000000,Yaw=-0.000020,Roll=0.000000)
         RelativeScale3D=(X=0.362768,Y=0.257098,Z=0.414737)
         bVisible=False
         bHiddenInGame=True
      End Object
      DisabledMaterialSets(0)=0
      DisabledMaterialSets(1)=2
      ObjectName="Cam_BlokingBox_04"
      Guid=6FFB0BA3420EF56546E55186C885A07E
   End Object
   """

    # parsing
    uobject = parser_unreal_text(unreal_text)

    # print
    print(uobject)
    print(uobject.get_attribute('Class'))
    print(uobject.get_attribute('Name'))
    print(uobject.get_value('ObjectName'))
    print(uobject.get_value('Guid'))
    print(uobject.get_value('DisabledMaterialSets'))
    
    source_components = uobject.get_children_has_value('StaticMesh', recursive=True)
    for source_component in source_components:
        print(source_component.get_attribute('Name'))
        print(source_component.get_value('StaticMesh'))
        print(source_component.get_value('RelativeLocation'))
        print(f"\t\tName of SourceComponent: {uobject.get_attribute('Name')}")
        print(f"\t\tSourceComponent.StaticMesh: {source_component.get_value('StaticMesh')}")
        print(f"\t\tSourceComponent.RelativeLocation: {source_component.get_value('RelativeLocation')}")
    

if __name__ == '__main__':
    if 1 < len(sys.argv):
        uobject = parser_unreal_text_file(sys.argv[1])
        print(uobject)
    else:
        print("Run: main.py unreal_text_file.t3d")
        print("or")
        example()