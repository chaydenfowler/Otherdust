import os
from flask import Flask, jsonify, render_template, request, json, session
from loot import json_roller
from loot.json_roller import RangeDict, PlunderTable, Table, Entry, Item
import jsonpickle


app = Flask(__name__)
app.secret_key = os.urandom(12).hex()

table_dict = json_roller.make_tables() # global tables
button_funcs = [#'plunder', 
                'merge_items', 
                'deep_merge_items', 
                'sort_entries', 
                'deep_sort_items',
                'delete_table',
                'roll_conditions',
                'each_roll_conditions'] # dumb way to remember which functions to pass into url_for()


def get_session_plunder():
    for name,table in table_dict.items():
        print(name)
        json_roller.save_json(f"loot/json/{name}.json", table)
    if 'plunder' not in session:
        print("plunder not in session")
        plunder = PlunderTable()
        session["plunder"] = jsonpickle.encode(plunder)
        session.permanent = True # default lasts 31 days
    else:
        print("plunder in session")
        plunder = jsonpickle.decode(session["plunder"])
    return plunder

def set_session_plunder(plunder):
    session["plunder"] = jsonpickle.encode(plunder)

@app.route('/')
def index():
    plunder = get_session_plunder()
    return render_template('roller.html', table_dict=table_dict, plunder=plunder, button_funcs=button_funcs)

@app.route('/plunder', methods=['POST'])
def plunder():
    plunder = get_session_plunder()
    loot_ID = request.form['plunder_ID']
    plunder.add_entry(json_roller.plunder(table_dict, loot_ID), str(len(plunder.entries.keys())))
    set_session_plunder(plunder)
    return render_template('plunder.html', plunder=plunder)

@app.route('/merge_items', methods=['POST'])
def merge_items():
    plunder = get_session_plunder()
    plunder = plunder.merge_items(deep=False, deep_ID=None)
    set_session_plunder(plunder)
    return render_template('plunder.html', plunder=plunder)

@app.route('/deep_merge_items', methods=['POST'])
def deep_merge_items():
    plunder = get_session_plunder()
    plunder = plunder.merge_items(deep=True, deep_ID="Merged Items")
    set_session_plunder(plunder)
    return render_template('plunder.html', plunder=plunder)

@app.route('/sort_entries', methods=['POST'])
def sort_entries():
    plunder = get_session_plunder()
    plunder = plunder.sort_items(deep=False)
    set_session_plunder(plunder)
    return render_template('plunder.html', plunder=plunder)

@app.route('/deep_sort_items', methods=['POST'])
def deep_sort_items():
    plunder = get_session_plunder()
    plunder = plunder.sort_items(deep=True)
    set_session_plunder(plunder)
    return render_template('plunder.html', plunder=plunder)

@app.route('/delete_table', methods=['POST'])
def delete_table():
    plunder = PlunderTable()
    set_session_plunder(plunder)
    return render_template('plunder.html', plunder=plunder)

@app.route('/roll_conditions', methods=['POST'])
def roll_conditions():
    plunder = get_session_plunder()
    plunder = plunder.roll_condition(table_dict, for_each=False)
    set_session_plunder(plunder)
    return render_template('plunder.html', plunder=plunder)

@app.route('/each_roll_conditions', methods=['POST'])
def each_roll_conditions():
    plunder = get_session_plunder()
    plunder = plunder.roll_condition(table_dict, for_each=True)
    set_session_plunder(plunder)
    return render_template('plunder.html', plunder=plunder)

if __name__ == "__main__":
    app.run(debug=True)