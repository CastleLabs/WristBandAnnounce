from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import threading
from announcer import main as announcement_main
import os
import logging
import subprocess
from typing import Dict, Any
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a secure secret key

# Global variable to store the announcement thread
announcement_thread = None

class ConfigHandler:
    def __init__(self, config_file: str = "config.ini"):
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
        """Read and parse the configuration file manually."""
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
                            if current_section == 'times':
                                self.config['times'][key] = value
                            elif current_section in self.config:
                                if key.lower() in self.config[current_section]:
                                    # Remove any surrounding quotes if they exist
                                    clean_value = value.strip()
                                    if (clean_value.startswith('"') and clean_value.endswith('"')) or \
                                       (clean_value.startswith("'") and clean_value.endswith("'")):
                                        clean_value = clean_value[1:-1]
                                    self.config[current_section][key.lower()] = clean_value
            return self.config
        except Exception as e:
            logging.error(f"Error reading config: {e}")
            return self.config

    def write_config(self) -> None:
        """Write the configuration back to file."""
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
                for key, value in self.config['announcements'].items():
                    # Remove any existing quotes before writing
                    clean_value = str(value).strip()
                    if (clean_value.startswith('"') and clean_value.endswith('"')) or \
                       (clean_value.startswith("'") and clean_value.endswith("'")):
                        clean_value = clean_value[1:-1]
                    f.write(f"{key} = {clean_value}\n")
                f.write("\n")

                # Write tts section
                f.write("[tts]\n")
                f.write(f"voice_id = {self.config['tts']['voice_id']}\n")

        except Exception as e:
            logging.error(f"Error writing config: {e}")
            raise

def restart_services():
    """Restart only the announcer service."""
    try:
        subprocess.run(['sudo', 'systemctl', 'restart', 'announcer.service'], check=True)
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Error restarting services: {e}")
        return False

@app.route('/add_time', methods=['POST'])
def add_time():
    """Add a new time entry to the configuration."""
    try:
        data = request.get_json()
        time = data.get('time')
        type_ = data.get('type')

        if not time or not type_:
            return jsonify({'error': 'Missing time or type'}), 400

        config_handler = ConfigHandler()
        config_handler.read_config()
        config_handler.config['times'][time] = type_
        config_handler.write_config()

        # Restart services after adding time
        if restart_services():
            return jsonify({'message': 'Time added successfully'}), 200
        else:
            return jsonify({'error': 'Failed to restart services'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete_time', methods=['POST'])
def delete_time():
    """Delete a time entry from the configuration."""
    try:
        data = request.get_json()
        time = data.get('time')

        if not time:
            return jsonify({'error': 'Missing time'}), 400

        config_handler = ConfigHandler()
        config_handler.read_config()

        if time in config_handler.config['times']:
            del config_handler.config['times'][time]
            config_handler.write_config()

            # Restart services after deleting time
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
    """Display the configuration form."""
    config_handler = ConfigHandler()
    config = config_handler.read_config()

    # Format times for display
    times_str = '\n'.join(f"{time} = {announcement_type}"
                         for time, announcement_type in sorted(config['times'].items()))

    return render_template('config.html',
                         database=config['database'],
                         times=times_str,
                         announcements=config['announcements'],
                         tts=config['tts'])

@app.route('/save', methods=['POST'])
def save_config():
    """Save the configuration and restart the announcement system."""
    try:
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
        config['times'] = {k.strip(): v.strip()
                         for k, v in [line.split('=')
                         for line in request.form['times'].strip().split('\n')
                         if '=' in line]}

        # Announcements section
        config['announcements'] = {
            'fiftyfive': request.form['fiftyfive_template'],
            'hour': request.form['hour_template'],
            'rules': request.form['rules_template'],
            'ad': request.form['ad_template']
        }

        # TTS section
        config['tts'] = {
            'voice_id': request.form['voice_id']
        }

        # Write to file
        config_handler.config = config
        config_handler.write_config()

        # Only restart the announcer service
        if restart_services():
            flash('Configuration saved and announcer service restarted successfully!', 'success')
        else:
            flash('Configuration saved but service restart failed. Please restart manually.', 'error')

        return redirect(url_for('index'))

    except Exception as e:
        flash(f'Error saving configuration: {str(e)}', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
