import copy
import datetime
import json
import os
import time
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
import traceback
import webbrowser

import importlib
# reload - logging
import logging
importlib.reload(logging)

# add module path
import sys
module_path = os.path.split(__file__)[0]
if module_path not in sys.path:
    sys.path.append(module_path)

# reload modules
import constants
importlib.reload(constants)

import parsing_unreal_text
importlib.reload(parsing_unreal_text)

import utility
importlib.reload(utility)

import widgets
importlib.reload(widgets)

import unreal


class EngineVersion():
    def __init__(self, version):
        self.version = version
        self.major = 0
        self.minor = 0
        self.patch = 0        
        match_version = utility.re_engine_version.match(version)
        if match_version:
            self.major, self.minor, self.patch = [int(n) for n in match_version.groups()]
    
    def __str__(self):
        return self.version


class UE_Migrate_Tool():
    def __init__(self, migrate_module_name, migrate_module):
        self.is_valid = False
        self.migrate_module = migrate_module
        self.execute_migration = False

        # unreal engine
        engine_version = unreal.SystemLibrary.get_engine_version()
        self.engine_version = EngineVersion(engine_version)
        self.asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()

        # root gui
        self.root = tk.Tk()
        self.root.title(f'{self.__class__.__name__} for {engine_version}')
        
        # project directories
        self.project_dircetory = os.path.abspath(unreal.SystemLibrary.get_project_directory())        
        self.project_content_dircetory = os.path.join(self.project_dircetory, "Content")

        # project config
        self.project_config_direcotry = os.path.join(self.project_content_dircetory, 'UE_Migrate_Tool')        
        self.project_config_filepath = os.path.join(self.project_config_direcotry, 'config.ini')

        # load project config
        self.project_config = copy.copy(constants.default_project_config)
        if os.path.exists(self.project_config_filepath):
            with open(self.project_config_filepath, 'r') as f:
                self.project_config = eval(f.read())
        else:
            self.save_project_config_file()
            
        # set intermediate_dircetory 
        self.intermediate_dircetory = self.project_config.get('intermediate_dircetory')
        if not os.path.exists(self.intermediate_dircetory):
            initialdir = self.project_dircetory
            check_intermediate_dircetory = filedialog.askdirectory(initialdir=initialdir, title='Please select a Intermediate Data directory')
            print(os.path.exists(check_intermediate_dircetory), check_intermediate_dircetory)
            if os.path.exists(check_intermediate_dircetory):
                self.intermediate_dircetory = check_intermediate_dircetory
                self.project_config['intermediate_dircetory'] = check_intermediate_dircetory
                self.save_project_config_file()
            else:
                # exit
                print("Cancled..")
                self.destroy()
                return
        
        # intermediate sub dircetories
        self.intermediate_export_dircetory = os.path.join(self.intermediate_dircetory, "Export")
        self.log_dircetory = os.path.join(self.intermediate_dircetory, '.log')

        # intermediate files
        self.src_project_info_filepath = os.path.join(self.intermediate_dircetory, "project_info.txt")
        self.dirnames_filepath = os.path.join(self.intermediate_dircetory, 'dirnames.txt')
        self.config_filepath = os.path.join(self.intermediate_dircetory, 'config.ini')

        # prepare directories
        makedir_list = [self.intermediate_dircetory, self.log_dircetory]
        for dirpath in makedir_list:
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)
        
        # write to file and output steam
        log_time = datetime.datetime.fromtimestamp(time.time()).strftime('_%Y%m%d_%H%M%S.log')
        self.log_filename = os.path.join(self.log_dircetory, migrate_module_name + log_time)
        #format = '[%(levelname)s] %(asctime)s > %(message)s'
        format='%(asctime)s,%(msecs)03d [%(levelname)s|%(filename)s:%(lineno)d] %(message)s'
        logging.basicConfig(filename=self.log_filename, format=format, datefmt='%Y-%m-%d:%H:%M:%S', level=logging.DEBUG)
        self.log(f'>>> Begin Log: {self.log_filename}')

        # load config file
        self.config = copy.copy(constants.default_config)
        if not self.load_config_file():
            utility.write_to_file(filepath=self.config_filepath, content=json.dumps(constants.default_config, indent=4))

        self.build_gui()

        # at last
        self.is_valid = True

    def load_config_file(self):
        if os.path.exists(self.config_filepath):
            with open(self.config_filepath, 'r') as f:
                self.config = eval(f.read())
            return True
        return False

    def build_gui(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.grid()
        
        # work dir
        label = ttk.Label(frame, text=f'WorkDir: {self.intermediate_dircetory}')
        label.grid(column=0, row=0, sticky=tk.W+tk.E)

        # execute button
        def execute_migration():
            self.execute_migration = True
            self.destroy()
        button_excute = ttk.Button(frame, text="Execute Migration", command=execute_migration)
        button_excute.grid(column=0, row=1, sticky=tk.W+tk.E)

        # input classes
        all_export_class_names = self.config.get('all_class_names', [])
        self.copy_class_widget = widgets.SelectAssetTypeWidget(frame, 'Copy class names', all_export_class_names)
        self.unreal_text_class_widget = widgets.SelectAssetTypeWidget(frame, 'Convert class names', all_export_class_names)
        self.save_class_widget = widgets.SelectAssetTypeWidget(frame, 'Save class names', all_export_class_names)
        self.clean_up_class_widget = widgets.SelectAssetTypeWidget(frame, 'Warning! - Clean-Up silently class names', all_export_class_names)

    def destroy(self):
        if self.root:
            self.root.quit()
            self.root.destroy()
            self.root = None

    def save_project_config_file(self):
        utility.write_to_file(filepath=self.project_config_filepath, content=json.dumps(self.project_config, indent=4))

    def get_export_filepath(self, class_name):
        return os.path.join(self.intermediate_export_dircetory, f'{class_name}.txt')

    def get_exported_filelist(self, class_name):
        filepath_list = []
        import_filepath = self.get_export_filepath(class_name)
        if os.path.exists(import_filepath):            
            with open(import_filepath, 'r') as f:
                filepath_list = f.read().split('\n')
            logging.info(f'>>> Open {import_filepath}: exported assets({len(filepath_list)})')
        else:
            logging.info(f'>>> Failed to open {import_filepath}')
        return filepath_list

    def log(self, text):
        print(text)
        logging.info(text)

    def get_assets_by_class(self, class_name):
        # TODO - unreal engine version wrapper
        assets = []
        if self.engine_version.major == 4:
            assets = self.asset_registry.get_assets_by_class(unreal.StringLibrary.conv_string_to_name(class_name), False)
        elif self.engine_version.major == 5:
            assets = self.asset_registry.get_assets_by_class(unreal.TopLevelAssetPath('/Script/Engine', class_name))
        else:
            logging.error(f'not implemented - get_assets_by_class for engine version {self.engine_version}')
        return assets

    def execute(self):
        if not self.is_valid:
            self.destroy()
            return
        
        # blocking - todo multiprocess
        self.root.mainloop()

        # execute migration
        if self.execute_migration:
            ignore_folders = self.config.get('ignore_folders', [])
            self.migrate_module.execute(
                self, 
                copy_class_names = self.copy_class_widget.get_values(),
                unreal_text_class_names = self.unreal_text_class_widget.get_values(),
                clean_up_class_names = self.clean_up_class_widget.get_values(),
                save_class_names = self.save_class_widget.get_values(),
                ignore_folders=ignore_folders
            )

            if os.path.exists(self.log_filename):
                webbrowser.open(self.log_filename)
                
        self.log(f'>>> End - Log: {self.log_filename}')

if __name__ == '__main__':
    if 1 < len(sys.argv):
        module_name = sys.argv[1]
        print(f"run module: {module_name}")

        # reload modules
        migrate_module = None
        exec(f"import {module_name} as migrate_module")
        importlib.reload(migrate_module)

        try:
            tool = UE_Migrate_Tool(module_name, migrate_module)
            tool.execute()
        except:
            error = traceback.format_exc()
            print(error)
            logging.error(traceback.format_exc())
        logging.shutdown()
    else:
        print("Run: main.py Module_Name")
