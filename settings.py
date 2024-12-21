"""
Flask application for managing announcement system configuration.
Provides a web interface for managing announcements, schedules, and system settings.
Handles real-time updates and persistence of configuration data.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import threading
from announcer import main as announcement_main
import os
import logging
import subprocess
from typing import Dict, Any, Optional
import json
import tempfile
import asyncio
import announcer

# Initialize Flask application
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this in production

# Global variable to store the announcement thread
announcement_thread = None

class ConfigHandler:
    """
    Handles reading, writing, and managing configuration data for the announcement system.
    Provides methods for parsing and updating configuration files.
    """

    def __init__(self, config_file: str = "config.ini"):
        """
        Initialize the ConfigHandler with default configuration structure.

        Args:
            config_file (str): Path to the configuration file
        """
        self.config_file = config_file
        self.config = {
            'database': {
                'server': '',
                'database': '',
                'username': '',
                'password': ''
            },
            'times': {},
            'announcements': {
                'fiftyfive': '',
                'hour': '',
                'rules': '',
                'ad': ''
            },
            'tts': {
                'voice_id': ''
            }
        }

    def read_config(self) -> Dict[str, Any]:
        """
        Read and parse the configuration file.
        Handles both standard and custom announcement types.

        Returns:
            Dict[str, Any]: Parsed configuration data
        """
        try:
            current_section = None
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue

                        if line.startswith('[') and line.endswith(']'):
                            current_section = line[1:-1].lower()
                            continue

                        if '=' in line:
                            key, value = [x.strip() for x in line.split('=', 1)]
                            # Handle different configuration sections
                            if current_section == 'times':
                                self.config['times'][key] = value
                            elif current_section == 'announcements':
                                # Handle both standard and custom announcement types
                                clean_value = value.strip('"\'')
                                if key.startswith('custom_') or key in ['fiftyfive', 'hour', 'rules', 'ad']:
                                    self.config['announcements'][key] = clean_value
                            elif current_section in self.config:
                                if key.lower() in self.config[current_section]:
                                    clean_value = value.strip('"\'')
                                    self.config[current_section][key.lower()] = clean_value
            return self.config
        except Exception as e:
            logging.error(f"Error reading config: {e}")
            return self.config

    def write_config(self) -> None:
        """
        Write the current configuration back to file.
        Handles proper formatting and escaping of values.
        """
        try:
            with open(self.config_file, 'w') as f:
                # Write database section
                f.write("[database]\n")
                for key, value in self.config['database'].items():
                    f.write(f"{key} = {value}\n")
                f.write("\n")

                # Write times section
                f.write("[times]\n")
                for time, value in sorted(self.config['times'].items()):
                    f.write(f"{time} = {value}\n")
                f.write("\n")

                # Write announcements section
                f.write("[announcements]\n")
                # Standard announcements first
                standard_types = ['fiftyfive', 'hour', 'rules', 'ad']
                for key in standard_types:
                    if key in self.config['announcements']:
                        value = self.config['announcements'][key]
                        f.write(f"{key} = {value}\n")

                # Custom announcements
                for key, value in self.config['announcements'].items():
                    if key.startswith('custom_'):
                        # Ensure proper escaping of value
                        escaped_value = value.replace('\n', '\\n').replace('"', '\\"')
                        f.write(f"{key} = \"{escaped_value}\"\n")
                f.write("\n")

                # Write TTS section
                f.write("[tts]\n")
                f.write(f"voice_id = {self.config['tts']['voice_id']}\n")

        except Exception as e:
            logging.error(f"Error writing config: {e}")
            raise

def restart_services() -> bool:
    """
    Restart the announcer service.

    Returns:
        bool: True if restart successful, False otherwise
    """
    try:
        subprocess.run(['sudo', 'systemctl', 'restart', 'announcer.service'], check=True)
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Error restarting services: {e}")
        return False

@app.route('/get_state', methods=['GET'])
def get_state():
    """
    Get current state of announcements and custom types.
    Used for real-time UI updates.

    Returns:
        JSON response with current state or error message
    """
    try:
        config_handler = ConfigHandler()
        config = config_handler.read_config()

        # Format custom types for frontend
        custom_types = {
            k.replace('custom_', ''): v
            for k, v in config['announcements'].items()
            if k.startswith('custom_')
        }

        # Get scheduled times
        times = config['times']

        return jsonify({
            'custom_types': custom_types,
            'times': times
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/add_custom_type', methods=['POST'])
def add_custom_type():
    """
    Add a new custom announcement type.
    Handles validation and persistence of new types.
    """
    try:
        data = request.get_json()
        name = data.get('name')
        template = data.get('template')

        if not name or not template:
            return jsonify({'error': 'Missing name or template'}), 400

        # Clean the name
        clean_name = ''.join(c.lower() if c.isalnum() or c.isspace() else '_' for c in name)
        clean_name = clean_name.replace(' ', '_')

        config_handler = ConfigHandler()
        config = config_handler.read_config()

        # Add to announcements with custom_ prefix
        config['announcements'][f'custom_{clean_name}'] = template

        config_handler.config = config
        config_handler.write_config()

        if restart_services():
            return jsonify({'message': 'Custom type added successfully'}), 200
        else:
            return jsonify({'error': 'Failed to restart services'}), 500

    except Exception as e:
        logging.error(f"Error adding custom type: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete_custom_type', methods=['POST'])
def delete_custom_type():
    """
    Delete a custom announcement type.
    Also removes any scheduled announcements using this type.
    """
    try:
        data = request.get_json()
        name = data.get('name')

        if not name:
            return jsonify({'error': 'Missing name'}), 400

        config_handler = ConfigHandler()
        config = config_handler.read_config()

        # Remove from announcements
        key = f'custom_{name}'
        if key in config['announcements']:
            del config['announcements'][key]

            # Remove scheduled times using this type
            times_to_remove = []
            for time, announcement_type in config['times'].items():
                if announcement_type == f'custom:{name}':
                    times_to_remove.append(time)

            for time in times_to_remove:
                del config['times'][time]

        config_handler.config = config
        config_handler.write_config()

        if restart_services():
            return jsonify({'message': 'Custom type deleted successfully'}), 200
        else:
            return jsonify({'error': 'Failed to restart services'}), 500

    except Exception as e:
        logging.error(f"Error deleting custom type: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/add_time', methods=['POST'])
def add_time():
    """
    Add a new scheduled announcement time.
    Validates time format and announcement type.
    """
    try:
        data = request.get_json()
        time = data.get('time')
        type_ = data.get('type')

        if not time or not type_:
            return jsonify({'error': 'Missing time or type'}), 400

        config_handler = ConfigHandler()
        config = config_handler.read_config()

        # Validate custom type template exists
        if type_.startswith('custom:'):
            custom_name = type_.replace('custom:', '')
            template_key = f'custom_{custom_name}'
            if template_key not in config['announcements']:
                return jsonify({'error': f'Custom template {custom_name} not found'}), 400

        config['times'][time] = type_
        config_handler.config = config
        config_handler.write_config()

        if restart_services():
            return jsonify({'message': 'Time added successfully'}), 200
        else:
            return jsonify({'error': 'Failed to restart services'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/play_instant', methods=['POST'])
def play_instant():
    """
    Play an instant announcement.
    Synthesizes and plays announcement immediately.
    """
    try:
        data = request.get_json()
        text = data.get('text')

        if not text:
            return jsonify({'error': 'Missing announcement text'}), 400

        config_handler = ConfigHandler()
        config = config_handler.read_config()

        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = temp_file.name

        success = asyncio.run(
            announcer.synthesize_speech_async(
                text=text,
                voice_id=config['tts']['voice_id'],
                output_path=temp_path
            )
        )

        if not success:
            return jsonify({'error': 'Failed to synthesize speech'}), 500

        if not announcer.play_sound(temp_path, 'mp3'):
            return jsonify({'error': 'Failed to play announcement'}), 500

        return jsonify({'message': 'Announcement played successfully'}), 200

    except Exception as e:
        logging.error(f"Error playing instant announcement: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete_time', methods=['POST'])
def delete_time():
    """
    Delete a scheduled announcement time.
    """
    try:
        data = request.get_json()
        time = data.get('time')

        if not time:
            return jsonify({'error': 'Missing time'}), 400

        config_handler = ConfigHandler()
        config = config_handler.read_config()

        if time in config['times']:
            del config['times'][time]
            config_handler.write_config()

            if restart_services():
                return jsonify({'message': 'Time deleted successfully'}), 200
            else:
                return jsonify({'error': 'Failed to restart services'}), 500
        else:
            return jsonify({'error': 'Time not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    """
    Display the main configuration interface.
    Loads and formats current configuration for display.
    """
    config_handler = ConfigHandler()
    config = config_handler.read_config()

    # Format times for display
    times_str = '\n'.join(f"{time} = {announcement_type}"
                         for time, announcement_type in sorted(config['times'].items()))

    # Get custom types
    custom_types = {
        key.replace('custom_', ''): value
        for key, value in config['announcements'].items()
        if key.startswith('custom_')
    }
    custom_types_str = '\n'.join(f"{name} = {template}"
                                for name, template in sorted(custom_types.items()))

    return render_template('config.html',
                         database=config['database'],
                         times=times_str,
                         announcements=config['announcements'],
                         tts=config['tts'],
                         custom_types=custom_types_str)

@app.route('/save_config', methods=['POST'])
def save_config():
    """
    Save the complete configuration and restart the system.
    Handles form submission and configuration persistence.
    """
    try:
        logging.info("Processing save configuration request")
        config_handler = ConfigHandler()
        config = config_handler.config

        # Database section
        config['database'] = {
            'server': request.form['db_server'],
            'database': request.form['db_name'],
            'username': request.form['db_username'],
            'password': request.form['db_password']
        }

        # Times section
        config['times'] = {}
        times_str = request.form['times'].strip()
        if times_str:
            for line in times_str.split('\n'):
                if '=' in line:
                    time_, type_ = [part.strip() for part in line.split('=', 1)]
                    config['times'][time_] = type_

        # Standard announcements
        config['announcements'].update({
            'fiftyfive': request.form['fiftyfive_template'],
            'hour': request.form['hour_template'],
            'rules': request.form['rules_template'],
            'ad': request.form['ad_template']
        })

        # Custom types
        custom_types_str = request.form.get('customTypes', '').strip()
        # Clear old custom types first
        config['announcements'] = {k: v for k, v in config['announcements'].items()
                                 if not k.startswith('custom_')}
        if custom_types_str:
            for line in custom_types_str.split('\n'):
                if '=' in line:
                    name, template = [part.strip() for part in line.split('=', 1)]
                    config['announcements'][f'custom_{name}'] = template

        # TTS section
        config['tts']['voice_id'] = request.form['voice_id']

        # Write and restart
        config_handler.config = config
        config_handler.write_config()

        if restart_services():
            flash('Configuration saved and announcer service restarted successfully!', 'success')
        else:
            flash('Configuration saved but service restart failed. Please restart manually.', 'error')

        return redirect(url_for('index'))

    except Exception as e:
        logging.error(f"Error saving configuration: {e}")
        flash(f'Error saving configuration: {str(e)}', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
