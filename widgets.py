import tkinter as tk
from tkinter import ttk


class SelectAssetTypeWidget():
    def __init__(self, parent, title, values):
        frame = ttk.Frame(parent, padding=10)
        frame.grid()

        # Label
        label = ttk.Label(frame, text=title)
        label.grid(column=0, row=0, sticky=tk.W+tk.E)
        
        # combobox
        self.selected_asset_type = tk.StringVar()
        self.combo_box = ttk.Combobox(frame, values=values, textvariable=self.selected_asset_type, width=50)
        self.combo_box.grid(column=0, row=1, sticky=tk.W+tk.E)
        self.combo_box.set(values[0])
        self.combo_box.bind('<<ComboboxSelected>>', self.selected_combobox)
        
        # listbox
        self.selected_asset_list = tk.Variable(value=[])
        self.list_box = tk.Listbox(frame, height=5, listvariable=self.selected_asset_list, selectmode=tk.EXTENDED)
        self.list_box.grid(column=0, row=2, sticky=tk.W+tk.E)
        self.list_box.bind("<Delete>", self.delete_listbox)
        
        #scrollbar = ttk.Scrollbar(self.list_box, orient=tk.VERTICAL, command=self.list_box.yview)
        #scrollbar.pack(side="right")
        #self.list_box['yscrollcommand'] = scrollbar.set

    def selected_combobox(self, *args):
        selected_asset_type = self.selected_asset_type.get()
        selected_asset_list = self.selected_asset_list.get()
        if selected_asset_type not in selected_asset_list:
            self.list_box.insert(tk.END, selected_asset_type)

    def delete_listbox(self, event):
        selected_asset_list = list(self.selected_asset_list.get())
        selected_indices = self.list_box.curselection()
        selected_items = [selected_asset_list[i] for i in selected_indices]            
        for item in selected_items:
            if item in selected_asset_list:
                selected_asset_list.remove(item)
        self.selected_asset_list.set(selected_asset_list)

    def get_values(self):
        return list(self.selected_asset_list.get())