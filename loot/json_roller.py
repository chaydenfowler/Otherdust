import os
import json
import re
import random
import dice
import jsonpickle
import glob

class RangeDict(dict):
    def __getitem__(self, item):
        if not isinstance(item, range):
            for key in self:
                if item in key:
                    return self[key]
            raise KeyError(item)
        else:
            return super().__getitem__(item)

        
class PlunderTable:
    # A collection of multiple entries via dict keys
    def __init__(self, entries=None, entry_keys=None, examples=None):
        
        if entries is not None:
            self.entries = {key: entry for key,entry in zip(entry_keys, entries)}
            self.examples = {key: example for key,example in zip(entry_keys, examples)}
        else:
            self.entries = {}
            self.examples = {}
        
    def __str__(self):
        return "\n".join([f"{key} {entry}" for key,entry in self.entries.items()])
    
    def add_entry(self, entry, ID, example=""):
        self.entries[ID] = entry
        self.examples[ID] = example
    
    def get_entry(self, ID):
        return self.entries[ID]
    
    def get_example(self, ID):
        return self.examples[ID]
    
    def merge_items(self, deep=False, deep_ID=None):
        if deep:
            items = [item for k,entry in self.entries.items() for item in entry.items]
            entries = [Entry(items).merge_items()]
            if deep_ID is None:
                deep_ID = "New Merge"
            keys = [deep_ID]
            examples = ["Merged Entries"]
        else:
            entries,keys = zip(*[(entry.merge_items(),k) for k,entry in self.entries.items()])
            examples = self.examples

        return PlunderTable(entries, keys, examples)
    
    def roll_condition(self, table_dict, for_each=False):
        keys,entries = zip(*[(key,entry.roll_condition(table_dict, for_each)) 
                             for key,entry in self.entries.items()])
        return PlunderTable(entries, keys, [""])
    
    def sort_items(self, deep=True):
        if deep:
            keys,entries = zip(*[(key,entry.sort_items()) for key,entry in self.entries.items()])
        else:
            keys,entries = zip(*self.entries.items())
        keys,entries = zip(*sorted(zip(keys,entries))) 
        return PlunderTable(entries, keys, [""])
    
    def plunder(self, table_dict, ID):
        return self.entries[ID].plunder(table_dict)
    
    def plunder_verbose(self, table_dict, ID):
        print(self.get_entry(ID), "\n")
        plunder = self.plunder(table_dict, ID)
        print(plunder, "\n")
        return plunder
        
        
class Table:
    # A collection of multiple entries via range dicts
    def __init__(self, entries=None, entry_ranges=None):
        self.entries = RangeDict({range(key[0], key[1]): entry for key,entry in zip(entry_ranges, entries)})
        
    def __str__(self):
        return "\n".join([f"{key} {entry}" for key,entry in self.entries.items()])
    
    def rekey(self):
        #self.entries = RangeDict({range(int(key.lstrip("range(").rstrip(")").split(",")[0]),
        #                                int(key.lstrip("range(").rstrip(")").split(",")[1]))
        #                          : entry for key,entry in self.entries.items()})
        self.entries = RangeDict({eval(key): entry for key,entry in self.entries.items()})
    
    def get_entry(self, roll):
        return self.entries[int(roll)]
    
    def plunder(self, table_dict, roll):
        try:
            return self.entries[int(roll)].plunder(table_dict)
        except:
            key_max = max([key[-1] for key in self.entries.keys()])
            if roll > key_max:
                roll = key_max
            else:
                key_min = min([key[0] for key in self.entries.keys()])
                if roll < key_min:
                    roll = key_min
                else:
                    roll -= 1
            return self.plunder(table_dict, roll)
    
    
class Entry:
    # A collection of multiple items
    def __init__(self, items):
        self.items = items.copy()
        
    def __str__(self):
        return ", ".join([str(item) for item in self.items])
    
    def merge_items(self):
        new_items = {}
        for item in self.items:
            # Don't bother with chances. 
            if (item.chance is None) & (item.table_roll is None):
                ID = item.name+str(item.table_roll)+str(item.condition) 
                if ID in new_items.keys():
                    new_items[ID].num_items += item.num_items
                else:
                    new_items[ID] = item
               
        return Entry(list(new_items.values()))
    
    def roll_condition(self, table_dict, for_each=False):
        return Entry([i for s in [item.roll_condition(table_dict, for_each) for item in self.items] for i in s])
    
    def sort_items(self):
        return Entry(sorted(self.items, key=lambda x: x.name))
    
    def plunder(self, table_dict):
        return Entry([i for s in [item.plunder(table_dict) for item in self.items] for i in s])
        
    
class Item:
    def __init__(self, name, chance=None, num_items=1, table_roll=None, condition=None):
        # name can be item name or table reference
        self.name = name
        self.chance = chance
        self.num_items = num_items
        self.table_roll = table_roll
        self.condition = condition
        
    def __str__(self):
        return (f'{self.num_items} {self.name}'
                f'{" ["+self.condition+"]" if self.condition is not None else ""}'
                f'{" ("+self.table_roll+")" if self.table_roll is not None else ""}')
        
    def roll_condition(self, table_dict, for_each=False):
        # conditions: perfect, worn, light damage, moderate damage, heavy damage, broken, ruined
        condition = self.condition
        
        if (condition is None) and (for_each):
            return [Item(self.name, chance=self.chance, num_items=1, table_roll=self.table_roll,
                        condition=table_dict["equipment_wear"].plunder(table_dict, dice.roll("1d20t")).items[0].condition)
                   for i in range(self.num_items)]
        
        if condition is None:
            condition = table_dict["equipment_wear"].plunder(table_dict, dice.roll("1d20t")).items[0].condition
        return [Item(self.name, chance=self.chance, num_items=self.num_items, table_roll=self.table_roll, condition=condition)]          
        
    def plunder(self, table_dict):
        # roll on chance
        if self.chance is not None:
            if random.randint(1,100) < int(self.chance):
                return [Item("nothing")]
        
        # roll num items if not int
        if self.num_items is not None:
            num_items = dice.roll(str(self.num_items)+"t")
        
        # roll on tables for each item
        # return new item in collapsed form
        table_name = "_".join(self.name.split())
        if table_name in table_dict.keys():
            print(f"{table_name}")
            table_roll = "1d100" if self.table_roll is None else self.table_roll
            new_entries = [table_dict[table_name].plunder(table_dict, dice.roll(str(table_roll)+"t")) 
                           for i in range(num_items)]
            new_items = [item for entry in new_entries for item in entry.items]
            return new_items
        else:
            return [Item(self.name, chance=None, num_items=num_items, table_roll=None, condition=self.condition)]

def make_tables():
    dirname = os.path.dirname(__file__)
    searchname = os.path.join(dirname, 'json', '*')
    filenames = glob.iglob(searchname)

    #print(Item("").__class__)

    #classes = [RangeDict, PlunderTable, Table, Entry, Item]
    #jsonpickle.unpickler.Unpickler().register_classes(classes)

    table_dict = {}
    for filename in filenames:
        #print(f"{filename}")
        f = open(filename, "r")
        table_name = re.split('[/.]', filename)[-2]
        table_dict[table_name] = jsonpickle.decode(f.read())#, classes=classes)
        #print(type(table_dict[table_name]))
        #print(f"{table_name}")
        if table_name not in ["plunder"]:
            table_dict[table_name].rekey()
            
    return table_dict

def save_json(filename, object):
    f = open(filename, "w")
    f.write(jsonpickle.encode(object))


def plunder(table_dict, ID):
    return table_dict["plunder"].plunder(table_dict, ID)

def vplunder(table_dict, ID):
    return table_dict["plunder"].plunder_verbose(table_dict, ID)

def main():
    table_dict = make_tables()

    k = "P1"
    booty = PlunderTable()
    for i in range(5, 1, -1):
        booty.add_entry(plunder(table_dict, k), f"Roll {i+1}")

    print(booty)
    print(booty.merge_items("Merge 1"))
    print(booty.roll_condition(table_dict))
    print(booty.roll_condition(table_dict, for_each=True))
    print(booty.sort_items())
    print(booty.sort_items(deep=False))

if __name__ == "__main__":
    main()     