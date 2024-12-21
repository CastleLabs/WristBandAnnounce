import asyncio
import edge_tts
import pymssql
import datetime
import time
import sys
import os
import logging
import subprocess
import threading
from typing import Optional, Tuple, Dict
import tempfile
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("announcement_script.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

class Config:
    def __init__(self):
        self.database = {
            "server": "",
            "database": "",
            "username": "",
            "password": ""
        }
        self.times = {}
        self.announcements = {
            "fiftyfive": "",
            "hour": "",
            "rules": "",
            "ad": ""
        }
        self.tts = {
            "voice_id": "",
            "output_format": "mp3"
        }

def load_config(config_path: str = "config.ini") -> Config:
    config = Config()
    current_section = None

    try:
        if not os.path.exists(config_path):
            logging.error(f"Config file not found: {config_path}")
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('[') and line.endswith(']'):
                    current_section = line[1:-1].lower()
                    continue
                if '=' not in line:
                    continue
                key, value = [x.strip() for x in line.split('=', 1)]
                clean_value = value.strip('"\'')
                if current_section == 'database':
                    config.database[key.lower()] = clean_value
                elif current_section == 'times':
                    config.times[key] = clean_value
                elif current_section == 'announcements':
                    config.announcements[key.lower()] = clean_value
                elif current_section == 'tts':
                    if key.lower() == 'voice_id':
                        config.tts['voice_id'] = clean_value
                    elif key.lower() == 'output_format':
                        config.tts['output_format'] = clean_value.lower()

        if not all([config.database['server'], config.database['database'],
                   config.database['username'], config.database['password']]):
            raise ValueError("Missing required database configuration")
        if not config.tts['voice_id']:
            raise ValueError("Missing required TTS voice_id configuration")

        logging.info("Configuration loaded successfully")
        return config
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        raise

def get_color_message_from_db(config: Config) -> Optional[Dict[str, Dict[str, str]]]:
    """Fetch color intervals from the database."""
    try:
        logging.info(f"Connecting to database: {config.database['server']}")
        with pymssql.connect(
            server=config.database['server'],
            user=config.database['username'],
            password=config.database['password'],
            database=config.database['database'],
            timeout=30
        ) as conn:
            with conn.cursor() as cursor:
                # Simplified query to get colors directly
                query = """
                WITH ColorMapping AS (
                    SELECT
                        ROW_NUMBER() OVER (ORDER BY corder) as interval_num,
                        CASE color
                            WHEN -65536 THEN 'Red'
                            WHEN -256 THEN 'Yellow'
                            WHEN -16711681 THEN 'Blue'
                            WHEN -16711936 THEN 'Green'
                            WHEN -23296 THEN 'Orange'
                            ELSE 'Unknown'
                        END as color_name,
                        color as raw_color,
                        corder
                    FROM ticketprintergroupcolors
                    WHERE ticketprintergroupno = 1
                )
                SELECT
                    interval_num,
                    color_name,
                    raw_color
                FROM ColorMapping
                ORDER BY interval_num;
                """

                cursor.execute(query)
                rows = cursor.fetchall()

                if not rows:
                    logging.error("No colors found in database")
                    return None

                color_data = {}
                for interval_num, color_name, raw_color in rows:
                    logging.info(f"Color {interval_num}: {color_name} (Raw: {raw_color})")
                    color_data[f'color{interval_num}'] = {
                        'color': str(color_name).strip(),
                        'time': f'Interval {interval_num}'  # Simplified time representation
                    }

                logging.info(f"Retrieved color data: {color_data}")
                return color_data

    except Exception as e:
        logging.error(f"Database error in get_color_message_from_db: {e}")
        logging.exception("Full traceback:")
        return None

async def synthesize_speech_async(text: str, voice_id: str, output_path: str) -> bool:
    try:
        logging.info(f"Synthesizing speech: {text[:50]}...")
        communicate = edge_tts.Communicate(text, voice_id)
        await communicate.save(output_path)

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logging.info("Speech synthesis successful")
            return True
        else:
            logging.error("Speech synthesis failed - output file empty or missing")
            return False
    except Exception as e:
        logging.error(f"Error during speech synthesis: {e}")
        return False

def play_sound(sound_path: str, output_format: str) -> bool:
    if not sound_path or not os.path.exists(sound_path):
        logging.error(f"Invalid sound path: {sound_path}")
        return False

    try:
        logging.info(f"Playing sound file: {sound_path}")
        if not subprocess.run(['which', 'mpg123'], capture_output=True).returncode == 0:
            logging.error("mpg123 is not installed")
            return False

        subprocess.run(['mpg123', '-q', sound_path], check=True)
        logging.info("Sound played successfully")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Error playing sound: {e}")
        return False
    except Exception as e:
        logging.error(f"Error playing sound: {e}")
        return False
    finally:
        try:
            os.remove(sound_path)
            logging.debug(f"Cleaned up sound file: {sound_path}")
        except Exception as e:
            logging.warning(f"Failed to clean up file {sound_path}: {e}")

def convert_to_12hr_format(time_str: str) -> str:
    try:
        hour, minute = map(int, time_str.split(':'))
        period = "PM" if hour >= 12 else "AM"
        if hour > 12:
            hour -= 12
        elif hour == 0:
            hour = 12
        return f"{hour}:{minute:02d} {period}"
    except Exception as e:
        logging.error(f"Error converting time format: {e}")
        return time_str

def calculate_next_announcement(times: Dict[str, str], current_time: datetime.datetime) -> Optional[Tuple[datetime.datetime, str]]:
    announcement_times = []
    for time_str, announcement_type in times.items():
        try:
            hour, minute = map(int, time_str.split(':'))
            announcement_time = current_time.replace(
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0
            )
            if announcement_time > current_time:
                announcement_times.append((announcement_time, announcement_type))
        except ValueError:
            logging.warning(f"Invalid time format in configuration: {time_str}")
            continue

    if not announcement_times:
        return None

    return min(announcement_times, key=lambda x: x[0])

def synthesize_announcement(template: str, announcement_type: str, time_str: str, color: str, config: Config) -> Optional[str]:
    try:
        time_12hr = convert_to_12hr_format(time_str)
        logging.info(f"Processing announcement type: {announcement_type}")

        # Get color data for ALL announcement types since templates use color variables
        color_data = get_color_message_from_db(config)
        if not color_data:
            logging.warning("No color data available from database")
            # Create default color data to prevent template errors
            color_data = {
                'color1': {'color': 'unknown'},
                'color2': {'color': 'unknown'},
                'color3': {'color': 'unknown'},
                'color4': {'color': 'unknown'}
            }

        # Create format variables dictionary with all possible variables
        format_vars = {
            'time': time_12hr,
            'color': color,  # Keep original color variable
            'color1': color_data.get('color1', {}).get('color', 'unknown'),
            'color2': color_data.get('color2', {}).get('color', 'unknown'),
            'color3': color_data.get('color3', {}).get('color', 'unknown'),
            'color4': color_data.get('color4', {}).get('color', 'unknown')
        }

        logging.info(f"Template before formatting: {template}")
        logging.info(f"Format variables: {format_vars}")

        # Apply template formatting for all announcement types
        try:
            announcement_text = template.format(**format_vars)
            logging.info(f"Generated announcement text: {announcement_text}")
        except KeyError as e:
            logging.error(f"Template format error - missing key: {e}")
            return None
        except Exception as e:
            logging.error(f"Template format error: {e}")
            return None

        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = temp_file.name

        success = asyncio.run(
            synthesize_speech_async(announcement_text, config.tts['voice_id'], temp_path)
        )

        if success:
            return temp_path
        else:
            return None
    except Exception as e:
        logging.error(f"Error generating announcement: {e}")
        return None

def main():
    if not hasattr(main, 'shutdown_event'):
        main.shutdown_event = threading.Event()

    try:
        while True:
            try:
                config = load_config()
            except Exception as e:
                logging.error("Failed to load config. Waiting 60s and retrying.")
                if main.shutdown_event.wait(timeout=60):
                    return
                continue

            if not config.times:
                logging.warning("No announcements. Checking again in 60s.")
                if main.shutdown_event.wait(timeout=60):
                    return
                continue

            current_time = datetime.datetime.now()
            next_announcement = calculate_next_announcement(config.times, current_time)

            if not next_announcement:
                logging.info("No upcoming announcements. Checking again in 60s.")
                if main.shutdown_event.wait(timeout=60):
                    return
                continue

            next_time, announcement_type = next_announcement
            sleep_seconds = (next_time - current_time).total_seconds()
            if sleep_seconds > 0:
                if main.shutdown_event.wait(timeout=sleep_seconds):
                    return

            color = "unknown"
            if announcement_type in [":55", "hour"]:
                color_data = get_color_message_from_db(config)
                if color_data:
                    if announcement_type == ":55":
                        color = color_data['color3']['color']
                        logging.info(f"Using color3 for :55 announcement: {color}")
                    elif announcement_type == "hour":
                        color = color_data['color4']['color']
                        logging.info(f"Using color4 for hour announcement: {color}")
                else:
                    logging.warning("No color data returned from database, using 'unknown'")

            template_mapping = {
                ":55": "fiftyfive",
                "hour": "hour",
                "rules": "rules",
                "ad": "ad"
            }

            template_key = template_mapping.get(announcement_type, "hour")
            if announcement_type.startswith("custom:"):
                custom_name = announcement_type.replace("custom:", "")
                template_key = f"custom_{custom_name}"

            template = config.announcements.get(template_key, "Attention! It's {time}.")
            logging.info(f"Using template: {template_key} -> {template}")

            announcement_path = synthesize_announcement(
                template=template,
                announcement_type=announcement_type,
                time_str=next_time.strftime("%H:%M"),
                color=color,
                config=config
            )

            if announcement_path:
                played = play_sound(announcement_path, config.tts['output_format'])
                if not played:
                    logging.error("Failed to play announcement.")
            else:
                logging.error("Failed to create announcement audio.")

            if main.shutdown_event.wait(timeout=1):
                return

    except Exception as e:
        logging.critical(f"Unhandled exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
