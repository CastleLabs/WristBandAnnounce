import asyncio
import edge_tts
import pymssql
import datetime
import time
import sys
import os
import logging
import subprocess
from typing import Optional, Tuple, Dict
import tempfile
from pathlib import Path

# Configure logging to both file and console
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for detailed logs
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
        self.templates = {
            "fiftyfive": "",
            "hour": "",
            "rules": "",
            "ad": ""
        }
        self.tts = {
            "voice_id": "",
            "output_format": "mp3"  # Changed to 'mp3' for compatibility
        }
        self.rules = {
            "rules_content": ""
        }
        self.ad = {
            "ad_message": ""
        }

def load_config(config_path: str = "config.ini") -> Config:
    """
    Load configuration from a config.ini file.
    """
    config = Config()
    current_section = None
    
    try:
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
                
                if current_section == 'database':
                    config.database[key.lower()] = value
                elif current_section == 'times':
                    config.times[key] = value
                elif current_section == 'announcements':
                    config.templates[key.lower()] = value
                elif current_section == 'rules':
                    config.rules[key.lower()] = value
                elif current_section == 'ad':
                    config.ad[key.lower()] = value
                elif current_section == 'tts':
                    if key.lower() == 'voice_id':
                        config.tts['voice_id'] = value
                    elif key.lower() == 'output_format':
                        config.tts['output_format'] = value.lower()
    
        # Validate required config sections
        required_db_keys = ['server', 'database', 'username', 'password']
        for key in required_db_keys:
            if not config.database.get(key):
                raise ValueError(f"Missing database configuration key: {key}")
        
        if not config.tts['voice_id']:
            raise ValueError("Missing TTS configuration key: voice_id")
        
        if config.tts['output_format'] not in ['wav', 'mp3']:
            logging.warning(f"Unsupported output format '{config.tts['output_format']}'. Defaulting to 'mp3'.")
            config.tts['output_format'] = 'mp3'
        
        # Ensure rules and ad content are present
        if not config.rules.get('rules_content'):
            logging.warning("No rules content found in config. Using default rules.")
            config.rules['rules_content'] = "1. No running. 2. Follow instructions. 3. Stay safe."
        
        if not config.ad.get('ad_message'):
            logging.warning("No ad message found in config. Using default ad message.")
            config.ad['ad_message'] = "Don't miss our special offer on wristbands today!"
        
        return config
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        raise

async def synthesize_speech_async(text: str, voice_id: str, output_path: str) -> bool:
    """
    Asynchronously synthesize speech using Edge TTS and save to output_path.
    Returns True if successful, False otherwise.
    """
    try:
        logging.info(f"Attempting to synthesize speech with voice_id: {voice_id}")
        logging.debug(f"Text to synthesize: {text}")
        logging.debug(f"Output path: {output_path}")
        
        communicate = edge_tts.Communicate(text, voice_id)
        await communicate.save(output_path)
        
        # Verify file exists and has content
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            logging.info(f"Generated audio file size: {file_size} bytes")
            if file_size == 0:
                logging.error("Generated audio file is empty")
                return False
        else:
            logging.error("Audio file was not created")
            return False
            
        return True
    except Exception as e:
        logging.error(f"Error during speech synthesis: {str(e)}")
        logging.error(f"Exception type: {type(e).__name__}")
        return False

def convert_audio_format(input_path: str, output_path: str, target_format: str = 'mp3') -> bool:
    """
    Convert audio file to the target format using ffmpeg.
    """
    try:
        logging.info(f"Converting audio from {input_path} to {output_path} with format {target_format}")
        subprocess.run(['ffmpeg', '-y', '-i', input_path, '-ac', '1', '-ar', '16000', output_path],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info("Audio conversion successful")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Audio conversion failed: {e}")
        return False

def play_sound(sound_path: str, output_format: str) -> bool:
    """
    Play the announcement using mpg123 and clean up the temporary file.
    """
    if not sound_path or not os.path.exists(sound_path):
        logging.error(f"Invalid sound path: {sound_path}")
        return False
        
    try:
        logging.info(f"Attempting to play sound from: {sound_path}")
        logging.debug(f"File format: {output_format}")
        logging.debug(f"File size: {os.path.getsize(sound_path)} bytes")
        
        if output_format == 'mp3':
            # Use 'mpg123' for MP3 files
            logging.info("Playing MP3 file using mpg123...")
            subprocess.run(['mpg123', '-q', sound_path], check=True)
        elif output_format == 'wav':
            # Convert WAV to MP3 for consistent playback using mpg123
            converted_path = sound_path.replace('.wav', '_converted.mp3')
            conversion_success = convert_audio_format(sound_path, converted_path, 'mp3')
            if conversion_success:
                logging.info("Playing converted MP3 file using mpg123...")
                subprocess.run(['mpg123', '-q', converted_path], check=True)
                os.remove(converted_path)
            else:
                logging.error("Failed to convert WAV to MP3. Skipping playback.")
                return False
        else:
            logging.warning(f"Unsupported output format '{output_format}'. Attempting to use 'mpg123'...")
            subprocess.run(['mpg123', '-q', sound_path], check=True)
                
        logging.info("Successfully played announcement")
        return True
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Error playing sound with subprocess: {e}")
        return False
    except Exception as e:
        logging.error(f"Error playing sound: {str(e)}")
        logging.error(f"Exception type: {type(e).__name__}")
        return False
    finally:
        try:
            os.remove(sound_path)
            logging.debug(f"Cleaned up temporary file: {sound_path}")
        except Exception as e:
            logging.warning(f"Failed to clean up temporary file {sound_path}: {e}")

def get_color_message_from_db(config: Config) -> Optional[str]:
    """
    Fetch the color message from the database using the complex query.
    """
    try:
        with pymssql.connect(
            server=config.database['server'],
            user=config.database['username'],
            password=config.database['password'],
            database=config.database['database'],
            timeout=30
        ) as conn:
            with conn.cursor() as cursor:
                query = """
                SET NOCOUNT ON;
                
                DECLARE @IntervalsAhead INT = 0;
                DECLARE @PrinterGroup INT = 1;
                DECLARE @TimeFormat VARCHAR(max) = 'hh:mm';

                DECLARE @Colors TABLE (
                    code INT,
                    NAME VARCHAR(max)
                );

                INSERT INTO @Colors
                VALUES 
                    (-65536, 'Red'),
                    (-256, 'Yellow'),
                    (-16711681, 'Blue'),
                    (-16711936, 'Green'),
                    (-23296, 'Orange');

                DECLARE @NumGroups INT;
                DECLARE @NumColors INT;
                DECLARE @ShiftDateChangeTime TIME;

                SELECT @NumGroups = 1440 / timeincrement 
                FROM ticketprintergroups 
                WHERE ticketprintergroupno = @PrinterGroup;

                SELECT @NumColors = Count(0)
                FROM ticketprintergroupcolors
                WHERE ticketprintergroupno = @PrinterGroup;

                SELECT @ShiftDateChangeTime = shiftdatechangetime
                FROM applicationinfo;

                DECLARE @Intervals TABLE (
                    starttime TIME,
                    color VARCHAR(max)
                );

                WITH nums AS (
                    SELECT 0 AS value
                    UNION ALL
                    SELECT value + 1 AS value
                    FROM nums
                    WHERE nums.value < @NumGroups - 1
                )
                INSERT INTO @Intervals
                SELECT 
                    DATEADD(minute, n.value * 30, @ShiftDateChangeTime),
                    COALESCE(o.NAME, 'Unknown')
                FROM nums n
                JOIN ticketprintergroupcolors c
                    ON c.ticketprintergroupno = @PrinterGroup
                    AND c.corder = value % @NumColors
                LEFT OUTER JOIN @Colors o
                    ON c.color = o.code;

                SELECT TOP 1 
                    color + ' wristbands will be expiring at ' + FORMAT(CAST(starttime AS DATETIME), @TimeFormat) + '!'
                FROM @Intervals
                WHERE starttime > CAST(DATEADD(minute, 30 * @IntervalsAhead, CURRENT_TIMESTAMP) AS TIME)
                    OR CAST(DATEADD(minute, 30 * @IntervalsAhead, CURRENT_TIMESTAMP) AS TIME) > 
                        (SELECT MAX(starttime) FROM @Intervals)
                ORDER BY starttime;
                """
                cursor.execute(query)
                row = cursor.fetchone()
                if row:
                    return str(row[0]).strip()
                logging.warning("No color data returned from database")
                return None
    except pymssql.InterfaceError as e:
        logging.error(f"Database connection error: {e}")
        return None
    except pymssql.DatabaseError as e:
        logging.error(f"Database error: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error in database query: {e}")
        return None

def calculate_next_announcement(times: Dict[str, str], current_time: datetime.datetime) -> Optional[Tuple[datetime.datetime, str]]:
    """
    Calculate the next announcement time and type.
    """
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
            
            if announcement_time <= current_time:
                continue
                
            announcement_times.append((announcement_time, announcement_type))
        except ValueError:
            logging.warning(f"Invalid time format in configuration: {time_str}")
            continue
    
    if not announcement_times:
        return None
        
    return min(announcement_times, key=lambda x: x[0])

def convert_to_12hr_format(time_str: str) -> str:
    """
    Convert time from 24-hour format (HH:MM) to 12-hour format with AM/PM.
    """
    try:
        # Parse the time string
        hour, minute = map(int, time_str.split(':'))
        
        # Determine AM/PM
        period = "PM" if hour >= 12 else "AM"
        
        # Convert hour to 12-hour format
        if hour > 12:
            hour -= 12
        elif hour == 0:
            hour = 12
            
        return f"{hour}:{minute:02d} {period}"
    except Exception as e:
        logging.error(f"Error converting time format: {e}")
        return time_str  # Return original string if conversion fails

def synthesize_announcement(template: str, announcement_type: str, time_str: str, color: str, config: Config, dynamic_content: Dict[str, str] = None) -> Optional[str]:
    """
    Generate an announcement audio file using Edge TTS.
    """
    try:
        # Convert time to 12-hour format
        time_12hr = convert_to_12hr_format(time_str)
        
        # Generate announcement text based on type
        if announcement_type in ["rules", "ad"] and dynamic_content:
            announcement_text = template.format(**dynamic_content)
            logging.info(f"Generated announcement text: {announcement_text}")
        else:
            # For :55 and hour announcements
            announcement_text = template.format(time=time_12hr, color=color)
            logging.info(f"Generated announcement text: {announcement_text}")

        # Create a temporary file with the specified output format
        suffix = f".{config.tts['output_format']}"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_path = temp_file.name

        # Synthesize speech using Edge TTS
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
    try:
        config = load_config()
        
        if not config.times:
            raise ValueError("No valid announcement times found in configuration")

        logging.info("Starting scheduled announcement player...")
        logging.info("Loaded announcement times:")
        for t, t_type in config.times.items():
            logging.info(f"  {t} -> {t_type}")

        # Define mapping for announcement types to templates
        template_mapping = {
            ":55": "fiftyfive",
            "hour": "hour",
            "rules": "rules",
            "ad": "ad"
        }

        while True:
            current_time = datetime.datetime.now()
            next_announcement = calculate_next_announcement(config.times, current_time)
            
            if not next_announcement:
                tomorrow = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
                sleep_seconds = (tomorrow - current_time).total_seconds()
                logging.info(f"No more announcements today. Sleeping until midnight ({sleep_seconds} seconds)")
                time.sleep(sleep_seconds)
                continue
                
            next_time, announcement_type = next_announcement
            sleep_seconds = (next_time - current_time).total_seconds()
            
            if sleep_seconds > 0:
                logging.debug(f"Sleeping for {sleep_seconds} seconds until next announcement at {next_time}")
                time.sleep(sleep_seconds)
            
            # Select template based on announcement_type
            template_key = template_mapping.get(announcement_type, "hour")  # Default to 'hour' if type not found
            template = config.templates.get(template_key, "Attention! It's {time}.")  # Default template
            
            # Handle dynamic content for 'rules' and 'ad'
            dynamic_content = {}
            if announcement_type == "rules":
                dynamic_content = {"rules_content": config.rules.get("rules_content", "1. No running. 2. Follow instructions. 3. Stay safe.")}
            elif announcement_type == "ad":
                dynamic_content = {"ad_message": config.ad.get("ad_message", "Don't miss our special offer on wristbands today!")}
            else:
                # For ':55' and 'hour' announcements, fetch color message from DB
                color_message = get_color_message_from_db(config)
                if not color_message:
                    color = "unknown"
                    logging.warning(f"No color data returned. Using fallback 'unknown'")
                else:
                    # Extract just the color from the message
                    color = color_message.split()[0]  # Get the first word (the color)

            # Generate the announcement
            if announcement_type in ["rules", "ad"]:
                announcement_path = synthesize_announcement(
                    template=template,
                    announcement_type=announcement_type,
                    time_str=next_time.strftime("%H:%M"),
                    color="",  # Not used for rules and ad
                    config=config,
                    dynamic_content=dynamic_content
                )
            else:
                announcement_path = synthesize_announcement(
                    template=template,
                    announcement_type=announcement_type,
                    time_str=next_time.strftime("%H:%M"),
                    color=color,
                    config=config
                )
            
            if announcement_path:
                success = play_sound(announcement_path, config.tts['output_format'])
                if not success:
                    logging.error("Failed to play announcement")
            
            # Sleep a bit to avoid immediate next loop iteration
            time.sleep(1)

    except Exception as e:
        logging.critical(f"Unhandled exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
