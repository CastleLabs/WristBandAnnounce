from flask import Flask, render_template, request, redirect, url_for, flash
import threading
from announcer import main as announcement_main
import os
import logging
from typing import Dict, Any

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

def format_times(times: Dict[str, str]) -> str:
    """Format times dictionary to string format."""
    return '\n'.join(f"{time} = {announcement_type}"
                    for time, announcement_type in sorted(times.items()))

def parse_times(times_str: str) -> Dict[str, str]:
    """Parse times from string format to dictionary."""
    times = {}
    for line in times_str.strip().split('\n'):
        if '=' in line:
            time, announcement_type = line.split('=')
            times[time.strip()] = announcement_type.strip()
    return times

@app.route('/')
def index():
    """Display the configuration form."""
    config_handler = ConfigHandler()
    config = config_handler.read_config()

    # Format times for display
    times_str = format_times(config['times'])

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
        config['times'] = parse_times(request.form['times'])

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

        # Restart announcement system
        restart_announcement_system()

        flash('Configuration saved successfully!', 'success')
        return redirect(url_for('index'))

    except Exception as e:
        flash(f'Error saving configuration: {str(e)}', 'error')
        return redirect(url_for('index'))

def restart_announcement_system():
    """Restart the announcement system thread."""
    global announcement_thread

    # Add event to signal thread shutdown
    if not hasattr(announcement_main, 'shutdown_event'):
        announcement_main.shutdown_event = threading.Event()

    # Stop existing thread if running
    if announcement_thread and announcement_thread.is_alive():
        logging.info("Stopping existing announcement thread...")
        announcement_main.shutdown_event.set()  # Signal the thread to stop
        announcement_thread.join(timeout=5)     # Wait up to 5 seconds for thread to stop
        if announcement_thread.is_alive():
            logging.warning("Thread did not stop gracefully, forcing restart...")

    # Reset shutdown event
    announcement_main.shutdown_event.clear()

    # Start new thread
    logging.info("Starting new announcement thread...")
    announcement_thread = threading.Thread(target=announcement_main, daemon=True)
    announcement_thread.start()

if __name__ == '__main__':
    # Start the announcement system in a separate thread
    announcement_thread = threading.Thread(target=announcement_main, daemon=True)
    announcement_thread.start()

    # Run the Flask application
    app.run(host='0.0.0.0', port=5000, debug=True)