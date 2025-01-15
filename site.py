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
    'Wizard': {
        1: ['Magic Missile', 'Shield'],
        2: ['Misty Step', 'Scorching Ray'],
        # ...additional levels and spells...
    },
    'Cleric': {
        1: ['Cure Wounds', 'Guiding Bolt'],
        2: ['Lesser Restoration', 'Spiritual Weapon'],
        # ...additional levels and spells...
    },
    # ...additional classes and spells...
}

def get_google_credentials():
    """
    Get or refresh Google API credentials.

    This function checks for existing Google API credentials in a file named 'token.json'.
    If the credentials are not found or are invalid, it initiates an OAuth2 flow to obtain new credentials.
    The credentials are then saved to 'token.json' for future use.

    Returns:
        Credentials: The Google API credentials.
    """
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
    elif not creds.valid:
        if creds.expired and creds.refresh_token:
            creds = flow.run_local_server(port=0, authorization_prompt_message='Please visit this URL to authorize this application: {url}')
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
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
        if score < 8:
            return score - 6
        elif score < 14:
            return score - 8
        else:
            return 2 * (score - 14) + 7

    if not all(MIN_SCORE <= score <= MAX_SCORE for score in scores):
        raise ValueError(f"Scores must be between {MIN_SCORE} and {MAX_SCORE}.")
    
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
    character_class = form_data.get('character_class')
    character_level = form_data.get('class_level')
    character_subclass = form_data.get('subclass')

    if character_class:
        if character_subclass:
            primary_class_data = f"{character_subclass} {character_class} {character_level}"
        else:
            primary_class_data = f"{character_class} {character_level}"
        print(f"Added primary class: {primary_class_data}")
    else:
        primary_class_data = ""
        print("No primary class provided")

    return primary_class_data  # Ensure primary_class_data is returned

def extract_multiclass_data(form_data):
    class_string = ""
    multiclass_count = 1
    while True:
        multiclass_key = f"multiclass_{multiclass_count}"
        multiclass_level_key = f"multiclass_level_{multiclass_count}"
        multiclass_subclass_key = f"subclass_{multiclass_count}"

        if multiclass_key in form_data and multiclass_level_key in form_data:
            multiclass = form_data.get(multiclass_key)
            multiclass_level = form_data.get(multiclass_level_key)
            multiclass_subclass = form_data.get(multiclass_subclass_key)

            if multiclass_subclass:
                multiclass_data = f"{multiclass_subclass} {multiclass} {multiclass_level}"
            else:
                multiclass_data = f"{multiclass} {multiclass_level}"

            print(f"Added multiclass: {multiclass_data}")
            if class_string:
                class_string += f", {multiclass_data}"
            else:
                class_string = multiclass_data
            multiclass_count += 1
        else:
            break

    print(f"Generated class string: {class_string}")
    return class_string

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

        # Update character name, class string, and ability scores
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
        spells_str = form_data.get('spells', '[]')
        print(f"Raw spells string: {spells_str}")
        
        try:
            spells = json.loads(spells_str)
            print(f"Parsed spells: {spells}")
            
            # Define cell mappings for different spell levels
            spell_cells = {
                '1': ['D100:J100', 'N100:T100', 'X100:AD100', 'D101:J101', 
                      'D102:J102', 'D103:J103', 'D104:J104'],
                '2': ['N104:T104', 'N101:T101', 'N102:T102', 'N103:T103', 
                      'X101:AD101', 'X102:AD102', 'X103:AD103', 'X104:AD104']
            }

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

            # Update spells for each level
            for level, level_spells in spell_groups.items():
                if level in spell_cells:
                    for cell, spell in zip(spell_cells[level], level_spells):
                        print(f"Updating {level} spell: {spell} in cell {cell}")
                        update_sheet_value(sheet, spreadsheet_id, f'{sheet_name}!{cell}', spell)

        except json.JSONDecodeError as err:
            print(f"JSON decode error: {err}")
            print(f"Problematic string: {spells_str}")
        except Exception as err:
            print(f"Error processing spells: {err}")

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
def get_spells(class_name):
    """Return spells for a specific class."""
    spells = dnd_spells.get(class_name, {})
    if not spells:
        return jsonify({'error': 'Class not found or no spells available for this class'}), 404
    return jsonify(spells)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            form_data = request.form
            new_sheet_id = process_request(form_data)
            return render_template('result.html', character_name=form_data.get('character_name'), sheet_id=new_sheet_id)
        except Exception as e:
            print(f"Error occurred: {e}")
            return render_template('index.html', error=str(e), classes=dnd_classes, subclasses=dnd_subclasses)
    else:
        return render_template('index.html', classes=dnd_classes, subclasses=dnd_subclasses)

@app.errorhandler(Exception)
def handle_error(error):
    """Global error handler."""
    print(f"Error occurred: {str(error)}")
    return render_template('index.html', error=str(error), classes=dnd_classes)

if __name__ == '__main__':
    app.run(debug=True)
