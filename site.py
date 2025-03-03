import json
import os.path
from flask import Flask, request, render_template, jsonify
from flask_cors import CORS
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Initialize Flask app with proper configuration
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Google API scopes
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# Define subclass levels for each class
dnd_subclass_levels = {
    "Barbarian": 3,
    "Bard": 3,
    "Illrigger": 3,
    "Cleric": 1,
    "Druid": 2,
    "Fighter": 3,
    "Jaeger": 3,
    "Monk": 3,
    "Paladin": 3,
    "Ranger": 3,
    "Rogue": 3,
    "Sorcerer": 3,
    "Warlock": 1,
    "Witch": 3,
    "Wizard": 2,
}

# Subclasses for each class
dnd_subclasses = {
    'Barbarian': ['Path of the Berserker', 'Path of the Totem Warrior'],
    'Bard': ['College of Lore', 'College of Valor'],
    'Cleric': ['Knowledge Domain', 'Life Domain', 'Light Domain', 'Nature Domain', 'Tempest Domain', 'Trickery Domain', 'War Domain'],
    'Druid': ['Circle of the Land', 'Circle of the Moon'],
    'Fighter': ['Champion', 'Battle Master', 'Eldritch Knight'],
    "Illrigger": ['Path of the Bloodrager', 'Path of the Soulblade', 'Path of the Warbringer'],
    'Jaeger': ['Sanguine', 'Salvation', 'Absolute', 'Heretic'],
    'Monk': ['Way of the Open Hand', 'Way of Shadow', 'Way of the Four Elements'],
    'Paladin': ['Oath of Devotion', 'Oath of the Ancients', 'Oath of Vengeance'],
    'Ranger': ['Hunter', 'Beast Master'],
    'Rogue': ['Thief', 'Assassin', 'Arcane Trickster'],
    'Sorcerer': ['Draconic Bloodline', 'Wild Magic'],
    'Warlock': ['The Archfey', 'The Fiend', 'The Great Old One'],
    'Witch': ['Black Magic', 'Blood Magic', 'Green Magic', 'Purple Magic', 'Red Magic', 'Steel Magic', 'Tea Magic', 'Technicolor Magic', 'White Magic', 'Yellow Magic'],
    'Wizard': ['School of Abjuration', 'School of Conjuration', 'School of Divination', 'School of Enchantment', 'School of Evocation', 'School of Illusion', 'School of Necromancy', 'School of Transmutation']
}

# Define DnD classes at the global scope
dnd_classes = [
    'Barbarian', 'Bard', 'Cleric', 'Druid', 'Fighter', 'Illrigger',
    'Monk', 'Paladin', 'Ranger', 'Jaeger', 'Rogue', 'Sorcerer',
    'Warlock', 'Witch', 'Wizard'
]

# Example spell data
dnd_spells = {
    "Wizard": {
        0: [],
        1: ["Magic Missile", "Shield"],
        2: ["Misty Step", "Scorching Ray"],
        3: [],
        4: [],
        5: [],
        6: [],
        7: [],
        8: [],
        9: [],
    },
    "Cleric": {
        0: [],
        1: ["Cure Wounds", "Guiding Bolt"],
        2: ["Lesser Restoration", "Spiritual Weapon"],
        3: [],
        4: [],
        5: [],
        6: [],
        7: [],
        8: [],
        9: [],
    },
    "Sorcerer": {
        0: [],
        1: ["Magic Missile", "Shield"],
        2: ["Misty Step", "Scorching Ray"],
        3: [],
        4: [],
        5: [],
        6: [],
        7: [],
        8: [],
        9: [],
    },
    "Warlock": {
        0: [],
        1: ["Hex", "Armor of Agathys"],
        2: ["Mirror Image", "Misty Step"],
        3: ["Counterspell", "Dispel Magic"],
        4: ["Banishment", "Dimension Door"],
        5: ["Hold Monster", "Wall of Force"],
        6: [],
        7: [],
        8: [],
        9: [],
    },
    "Bard": {
        0: ["Vicious Mockery", "Prestidigitation", "Minor Illusion"],
        1: ["Charm Person", "Healing Word", "Disguise Self"],
        2: ["Invisibility", "Suggestion", "Heat Metal"],
        3: ["Hypnotic Pattern", "Major Image", "Leomund’s Tiny Hut"],
        4: ["Dimension Door", "Polymorph"],
        5: ["Dominate Person", "Hold Monster"],
        6: ["Mass Suggestion", "Otto’s Irresistible Dance"],
        7: ["Forcecage", "Mirage Arcane"],
        8: ["Dominate Monster", "Power Word Stun"],
        9: ["Foresight", "True Polymorph"],
    },
    "Druid": {
        0: ["Druidcraft", "Guidance", "Produce Flame"],
        1: ["Entangle", "Faerie Fire", "Healing Word"],
        2: ["Flaming Sphere", "Moonbeam", "Spike Growth"],
        3: ["Call Lightning", "Plant Growth", "Wind Wall"],
        4: ["Polymorph", "Stone Shape"],
        5: ["Mass Cure Wounds", "Wall of Stone"],
        6: ["Move Earth", "Sunbeam"],
        7: ["Fire Storm", "Reverse Gravity"],
        8: ["Earthquake", "Sunburst"],
        9: ["Shapechange", "Mass Heal"],
    },
    "Ranger": {
        0: ["Hunter’s Mark", "Druidcraft"],
        1: ["Hunter’s Mark", "Cure Wounds"],
        2: ["Pass without Trace", "Spike Growth"],
        3: ["Conjure Animals", "Lightning Arrow"],
        4: ["Freedom of Movement", "Grasping Vine"],
        5: ["Swift Quiver", "Steel Wind Strike"],
        6: [],
        7: [],
        8: [],
        9: [],
    },
    "Paladin": {
        0: [],
        1: ["Shield of Faith", "Cure Wounds"],
        2: ["Lesser Restoration", "Magic Weapon"],
        3: ["Aura of Vitality", "Revivify"],
        4: ["Death Ward", "Staggering Smite"],
        5: ["Greater Restoration", "Raise Dead"],
        6: [],
        7: [],
        8: [],
        9: [],
    },
    "Witch": {
        0: [],
        1: ["Hex", "Mage Armor"],
        2: ["Blindness/Deafness", "Hold Person"],
        3: ["Counterspell", "Dispel Magic"],
        4: ["Banishment", "Dimension Door"],
        5: ["Hold Monster", "Wall of Force"],
        6: [],
        7: [],
        8: [],
        9: [],
    },
    "Barbarian": {
        0: [],
        1: [],  # Barbarians typically do not have spells
        # ...additional levels if needed...
    },
    "Fighter": {
        0: [],
        1: [],  # Fighters may gain spells at higher levels or via subclasses
        # ...additional levels if needed...
    },
    "Monk": {
        0: [],
        1: [],  # Monks typically do not have spells
        # ...additional levels if needed...
    },
    "Rogue": {
        0: [],
        1: [],  # Rogues typically do not have spells
        # ...additional levels if needed...
    },
    # Add other classes as needed
}

# Define caster progression for each class
caster_progression = {
    "Wizard": {
        1: {"1st": 2},
        2: {"1st": 3},
        3: {"1st": 4, "2nd": 2},
        4: {"1st": 4, "2nd": 3},
        5: {"1st": 4, "2nd": 3, "3rd": 2},
        6: {"1st": 4, "2nd": 3, "3rd": 3},
        7: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 1},
        8: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 2},
        9: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 1},
        10: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2},
        11: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1},
        12: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1},
        13: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1},
        14: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1},
        15: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1},
        16: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1},
        17: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1, "9th": 1},
        18: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1, "9th": 1},
        19: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1, "9th": 1},
        20: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1, "9th": 1},
    },
    "Cleric": {
        1: {"1st": 2},
        2: {"1st": 3},
        3: {"1st": 4, "2nd": 2},
        4: {"1st": 4, "2nd": 3},
        5: {"1st": 4, "2nd": 3, "3rd": 2},
        6: {"1st": 4, "2nd": 3, "3rd": 3},
        7: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 1},
        8: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 2},
        9: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 1},
        10: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2},
        11: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1},
        12: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1},
        13: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1},
        14: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1},
        15: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1},
        16: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1},
        17: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1, "9th": 1},
        18: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1, "9th": 1},
        19: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1, "9th": 1},
        20: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1, "9th": 1},
    },
    "Druid": {
        1: {"1st": 2},
        2: {"1st": 3},
        3: {"1st": 4, "2nd": 2},
        4: {"1st": 4, "2nd": 3},
        5: {"1st": 4, "2nd": 3, "3rd": 2},
        6: {"1st": 4, "2nd": 3, "3rd": 3},
        7: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 1},
        8: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 2},
        9: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 1},
        10: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2},
        11: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1},
        12: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1},
        13: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1},
        14: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1},
        15: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1},
        16: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1},
        17: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1, "9th": 1},
        18: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1, "9th": 1},
        19: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1, "9th": 1},
        20: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1, "9th": 1},
    },
    "Bard": {
        1: {"1st": 2},
        2: {"1st": 3},
        3: {"1st": 4, "2nd": 2},
        4: {"1st": 4, "2nd": 3},
        5: {"1st": 4, "2nd": 3, "3rd": 2},
        6: {"1st": 4, "2nd": 3, "3rd": 3},
        7: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 1},
        8: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 2},
        9: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 1},
        10: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2},
        11: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1},
        12: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1},
        13: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1},
        14: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1},
        15: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1},
        16: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1},
        17: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1, "9th": 1},
        18: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1, "9th": 1},
        19: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1, "9th": 1},
        20: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1, "9th": 1},
    },
    "Sorcerer": {
        1: {"1st": 2},
        2: {"1st": 3},
        3: {"1st": 4, "2nd": 2},
        4: {"1st": 4, "2nd": 3},
        5: {"1st": 4, "2nd": 3, "3rd": 2},
        6: {"1st": 4, "2nd": 3, "3rd": 3},
        7: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 1},
        8: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 2},
        9: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 1},
        10: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2},
        11: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1},
        12: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1},
        13: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1},
        14: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1},
        15: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1},
        16: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1},
        17: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1, "9th": 1},
        18: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1, "9th": 1},
        19: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1, "9th": 1},
        20: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1, "9th": 1},
    },
    # Add other caster classes as needed
}


def get_google_credentials():
    """Get or refresh Google API credentials."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds

def calculate_point_buy(scores):
    MIN_SCORE = 6
    MAX_SCORE = 18

    def calculate_points(score):
        # This formula calculates the point cost for a given ability score based on a custom polynomial equation.
        return round(0.01515 * score ** 3 - 0.4196 * score ** 2 + 4.739 * score - 18.701)

    if not all(MIN_SCORE <= score <= MAX_SCORE for score in scores):
        return {'is_valid': False, 'total': 0, 'individual_costs': []}
    individual_costs = [calculate_points(score) for score in scores]
    total = sum(individual_costs)
    return {
        'is_valid': total <= 35,
        'total': total,
        'individual_costs': individual_costs
    }

def process_request(form_data):
    character_name = form_data.get('character_name')
    primary_class_data = extract_primary_class_data(form_data)
    multiclass_data = extract_multiclass_data(form_data)
    class_string = primary_class_data
    if multiclass_data:
        class_string += f", {multiclass_data}"
    new_sheet_id = copy_entire_sheet('1Mx-R-sDVDcV-tEMXz0KrMlKij2BejMXD9AYxp3O6OX4', character_name)
    if new_sheet_id:
        update_character_sheet(character_name, class_string, form_data, new_sheet_id)
    else:
        print("Failed to copy the sheet.")
        return None
    return new_sheet_id

def extract_primary_class_data(form_data):
    class_data = form_data.get('class_data', [])
    if class_data:
        primary = class_data[0]
        character_class = primary.get('class')
        character_level = primary.get('level')
        character_subclass = primary.get('subclass')

        if character_class:
            if character_subclass:
                primary_class_data = f"{character_subclass} {character_class} {character_level}"
            else:
                primary_class_data = f"{character_class} {character_level}"
            print(f"Added primary class: {primary_class_data}")
            return primary_class_data
    print("No primary class provided")
    return ""

def extract_multiclass_data(form_data):
    class_data = form_data.get('class_data', [])
    if len(class_data) > 1:
        multiclass_entries = class_data[1:]
        class_string = ", ".join([
            f"{entry['subclass']} {entry['class']} {entry['level']}" if entry.get('subclass') else f"{entry['class']} {entry['level']}"
            for entry in multiclass_entries
        ])
        print(f"Generated multiclass string: {class_string}")
        return class_string
    return ""

def copy_entire_sheet(spreadsheet_id, new_spreadsheet_title):
    creds = get_google_credentials()
    if creds is None:
        print("Failed to obtain Google credentials.")
        return None

    try:
        service = build('drive', 'v3', credentials=creds)
        # Copy the entire spreadsheet
        copied_sheet = service.files().copy(
            fileId=spreadsheet_id,
            body={'name': new_spreadsheet_title}
        ).execute()
        print(f"Copied sheet ID: {copied_sheet['id']}")
        return copied_sheet['id']
    except HttpError as err:
        print(f"An error occurred: {err}")
        return None

@app.route('/copy_sheet', methods=['POST'])
def copy_sheet_route():
    data = request.json
    spreadsheet_id = data.get('spreadsheet_id')
    new_spreadsheet_title = data.get('new_spreadsheet_title')
    new_sheet_id = copy_entire_sheet(spreadsheet_id, new_spreadsheet_title)
    if new_sheet_id:
        return jsonify({'new_sheet_id': new_sheet_id}), 200
    else:
        return jsonify({'error': 'Failed to copy sheet'}), 500

def update_character_sheet(character_name, class_string, form_data, spreadsheet_id):
    creds = get_google_credentials()
    try:
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()

        sheet_metadata = sheet.get(spreadsheetId=spreadsheet_id).execute()
        sheet_name = sheet_metadata['sheets'][0]['properties']['title']

        # Update character name and class
        update_sheet_value(sheet, spreadsheet_id, f'{sheet_name}!C6', character_name)
        update_sheet_value(sheet, spreadsheet_id, f'{sheet_name}!T5', class_string)

        # Update ability scores
        ability_scores = [
            ('C16', int(form_data.get('strength'))),
            ('C21', int(form_data.get('dexterity'))),
            ('C26', int(form_data.get('constitution'))),
            ('C31', int(form_data.get('intelligence'))),
            ('C36', int(form_data.get('wisdom'))),
            ('C41', int(form_data.get('charisma')))
        ]

        for cell, value in ability_scores:
            update_sheet_value(sheet, spreadsheet_id, f'{sheet_name}!{cell}', value)

        # Update spells
        spells = form_data.get('spells', [])
        print(f"Raw spells: {spells}")

        try:
            # Group spells by level
            spell_groups = {}
            for spell in spells:
                if ':' in spell:
                    level, spell_name = spell.split(':', 1)
                    level = level.strip()
                    spell_name = spell_name.strip()
                    if level not in spell_groups:
                        spell_groups[level] = []
                    spell_groups[level].append(spell_name)
            
            print(f"Grouped spells: {spell_groups}")

            # Define spell cell mappings
            spell_cells = {
                '1': ['D100:J100', 'N100:T100', 'X100:AD100', 'D101:J101', 
                      'D102:J102', 'D103:J103', 'D104:J104', 'N104:T104', 'N101:T101', 'N102:T102', 'N103:T103', 
                      'X101:AD101', 'X102:AD102', 'X103:AD103', 'X104:AD104'],
                '2': ['N106:T106', 'N107:T107', 'N108:T108', 'N109:T109', 'N110:T110', "X106:AD106", "X107:AD107", "X108:AD108", "X109:AD109", "X110:AD110", "AH106:AN106", "AH107:AN107", "AH108:AN108", "AH109:AN109", ""],
            }

            # Update spells for each level
            for level, level_spells in spell_groups.items():
                if level in spell_cells:
                    cells = spell_cells[level]
                    for idx, spell in enumerate(level_spells):
                        if idx < len(cells):
                            cell_range = f'{sheet_name}!{cells[idx]}'
                            print(f"Updating {level} spell: {spell} in cell {cell_range}")
                            update_sheet_value(sheet, spreadsheet_id, cell_range, spell)

        except Exception as err:
            print(f"Error processing spells: {err}")
            print(f"Error details: {str(err)}")

    except HttpError as err:
        print(f"An error occurred: {err}")

def update_sheet_value(sheet, spreadsheet_id, cell_range, value):
    try:
        sheet.values().update(
            spreadsheetId=spreadsheet_id,
            range=cell_range,
            valueInputOption='RAW',
            body={'values': [[value]]}
        ).execute()
    except HttpError as err:
        print(f"An error occurred while updating the sheet: {err}")

@app.route('/validate_points', methods=['POST'])
def validate_points():
    scores = request.json.get('scores', [])
    if not isinstance(scores, list) or not all(isinstance(score, int) for score in scores):
        return jsonify({'error': 'Invalid input. Scores must be a list of integers.'}), 400
    result = calculate_point_buy(scores)
    return jsonify(result)

@app.route('/get_subclasses/<string:class_name>', methods=['GET'])
def get_subclasses(class_name):
    """Return subclasses for a specific class."""
    subclasses = dnd_subclasses.get(class_name, [])
    subclass_level = dnd_subclass_levels.get(class_name, 0)
    return jsonify({'subclasses': subclasses, 'level_required': subclass_level})

@app.route('/get_spells/<string:class_name>', methods=['GET'])
def get_spells_route(class_name):
    return get_spells(class_name)

def get_spells(class_name):
    """Endpoint to get spells for a given class."""
    spells = dnd_spells.get(class_name, {})
    # Example response structure
    response = {
        "level_required": 1,  # Adjust as needed per class
        "spells": spells
    }
    return jsonify(response)

def get_combined_spells(class_names):
    """Return combined spells for a list of classes."""
    combined_spells = []
    for class_name in class_names:
        spells = dnd_spells.get(class_name, {})
        for level, spell_list in spells.items():
            for spell in spell_list:
                combined_spells.append(f"Level {level}: {spell}")
    # Remove duplicates and sort
    combined_spells = sorted(list(set(combined_spells)))
    return combined_spells

@app.route('/get_combined_spells', methods=['POST'])
def get_combined_spells_route():
    data = request.json
    class_names = data.get('class_names', [])
    if not isinstance(class_names, list) or not all(isinstance(cls, str) for cls in class_names):
        return jsonify({'error': 'Invalid input. class_names must be a list of strings.'}), 400
    spells = get_combined_spells(class_names)
    return jsonify({'spells': spells})

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            form_data = request.get_json()
            print(f"Received form data: {form_data}")
            new_sheet_id = process_request(form_data)
            return jsonify({'character_name': form_data.get('character_name'), 'sheet_id': new_sheet_id})
        except Exception as e:
            print(f"Error occurred: {e}")
            return jsonify({'error': str(e)}), 500
    else:
        return render_template('index.html', classes=dnd_classes, subclasses=dnd_subclasses)

@app.route('/result')
def result():
    sheet_id = request.args.get('sheet_id')
    character_name = request.args.get('character_name')
    return render_template('result.html', sheet_id=sheet_id, character_name=character_name)

@app.errorhandler(Exception)
def handle_error(error):
    """Global error handler."""
    print(f"Error occurred: {str(error)}")
    return render_template('index.html', error=str(error), classes=dnd_classes)

if __name__ == '__main__':
    app.run(debug=True)
