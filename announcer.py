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

# Configure logging to both file and console with detailed formatting
logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level to DEBUG to capture all levels of log messages
    format="%(asctime)s [%(levelname)s] %(message)s",  # Define the log message format
    datefmt="%Y-%m-%d %H:%M:%S",  # Specify the date format in logs
    handlers=[
        logging.FileHandler("announcement_script.log"),  # Log messages to a file named 'announcement_script.log'
        logging.StreamHandler(sys.stdout)  # Also output log messages to the console (standard output)
    ]
)

class Config:
    """
    Configuration class to hold all configuration parameters for the announcement system.
    
    Attributes:
        database (Dict[str, str]): Database connection parameters including server, database name, username, and password.
        times (Dict[str, str]): Scheduled times for announcements mapped to their types.
        announcements (Dict[str, str]): Announcement templates for different announcement types.
        tts (Dict[str, str]): Text-to-speech settings including voice ID and output audio format.
    """
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
    """
    Load configuration parameters from a configuration file.
    
    This function reads the specified configuration file (defaulting to 'config.ini'),
    parses its content, and populates a Config object with the necessary parameters.
    It also validates the presence of required configuration keys.
    
    Args:
        config_path (str): The path to the configuration file. Defaults to 'config.ini'.
    
    Returns:
        Config: An instance of the Config class populated with configuration data.
    
    Raises:
        ValueError: If any required configuration key is missing or invalid.
        Exception: For any other exceptions encountered while loading the configuration.
    """
    config = Config()
    current_section = None

    try:
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()  # Remove leading and trailing whitespace
                if not line or line.startswith('#'):
                    continue  # Skip empty lines and comments

                # Detect section headers enclosed in [ ]
                if line.startswith('[') and line.endswith(']'):
                    current_section = line[1:-1].lower()
                    continue

                if '=' not in line:
                    continue  # Skip lines that don't contain key=value pairs

                key, value = [x.strip() for x in line.split('=', 1)]  # Split key and value

                # Assign values to the appropriate section in the Config object
                if current_section == 'database':
                    config.database[key.lower()] = value
                elif current_section == 'times':
                    config.times[key] = value
                elif current_section == 'announcements':
                    config.announcements[key.lower()] = value
                elif current_section == 'tts':
                    if key.lower() == 'voice_id':
                        config.tts['voice_id'] = value
                    elif key.lower() == 'output_format':
                        config.tts['output_format'] = value.lower()

        # Validate required database configuration keys
        required_db_keys = ['server', 'database', 'username', 'password']
        for key in required_db_keys:
            if not config.database.get(key):
                raise ValueError(f"Missing database configuration key: {key}")

        # Validate Text-to-Speech (TTS) configuration
        if not config.tts['voice_id']:
            raise ValueError("Missing TTS configuration key: voice_id")

        if config.tts['output_format'] not in ['wav', 'mp3']:
            logging.warning(f"Unsupported output format '{config.tts['output_format']}'. Defaulting to 'mp3'.")
            config.tts['output_format'] = 'mp3'

        return config
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        raise  # Re-raise the exception after logging

async def synthesize_speech_async(text: str, voice_id: str, output_path: str) -> bool:
    """
    Asynchronously synthesize speech from text using Edge TTS and save the audio to a file.
    
    This function utilizes the Edge TTS library to convert the provided text into speech,
    saving the resulting audio to the specified output path.
    
    Args:
        text (str): The text to be converted into speech.
        voice_id (str): The identifier for the desired voice in Edge TTS.
        output_path (str): The file path where the synthesized audio will be saved.
    
    Returns:
        bool: True if synthesis and file creation are successful, False otherwise.
    """
    try:
        logging.info(f"Attempting to synthesize speech with voice_id: {voice_id}")
        logging.debug(f"Text to synthesize: {text}")
        logging.debug(f"Output path: {output_path}")

        # Initialize the Edge TTS communication object with the text and voice ID
        communicate = edge_tts.Communicate(text, voice_id)
        await communicate.save(output_path)  # Save the synthesized speech to the output path

        # Verify that the audio file was created and is not empty
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
    Convert an audio file from one format to another using FFmpeg.
    
    This function leverages the FFmpeg tool to convert the input audio file to the desired target format.
    It specifically sets the audio channels to mono and the sampling rate to 16kHz.
    
    Args:
        input_path (str): The path to the input audio file.
        output_path (str): The path where the converted audio file will be saved.
        target_format (str): The desired audio format (default is 'mp3').
    
    Returns:
        bool: True if the conversion is successful, False otherwise.
    """
    try:
        logging.info(f"Converting audio from {input_path} to {output_path} with format {target_format}")
        # Execute the FFmpeg command to perform the conversion
        subprocess.run(
            ['ffmpeg', '-y', '-i', input_path, '-ac', '1', '-ar', '16000', output_path],
            check=True,  # Raise CalledProcessError if FFmpeg fails
            stdout=subprocess.PIPE,  # Suppress standard output
            stderr=subprocess.PIPE   # Suppress standard error
        )
        logging.info("Audio conversion successful")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Audio conversion failed: {e}")
        return False

def play_sound(sound_path: str, output_format: str) -> bool:
    """
    Play an audio file using mpg123 and handle cleanup of temporary files.
    
    Depending on the audio format, this function may convert WAV files to MP3 before playback.
    After playing the sound, it ensures that temporary files are removed to prevent clutter.
    
    Args:
        sound_path (str): The path to the audio file to be played.
        output_format (str): The format of the audio file (e.g., 'mp3', 'wav').
    
    Returns:
        bool: True if the sound was played successfully, False otherwise.
    """
    # Check if the sound file exists and is valid
    if not sound_path or not os.path.exists(sound_path):
        logging.error(f"Invalid sound path: {sound_path}")
        return False

    try:
        logging.info(f"Attempting to play sound from: {sound_path}")
        logging.debug(f"File format: {output_format}")
        logging.debug(f"File size: {os.path.getsize(sound_path)} bytes")

        if output_format == 'mp3':
            logging.info("Playing MP3 file using mpg123...")
            # Play the MP3 file quietly (-q flag) without verbose output
            subprocess.run(['mpg123', '-q', sound_path], check=True)
        elif output_format == 'wav':
            # Convert WAV to MP3 before playback
            converted_path = sound_path.replace('.wav', '_converted.mp3')
            conversion_success = convert_audio_format(sound_path, converted_path, 'mp3')
            if conversion_success:
                logging.info("Playing converted MP3 file using mpg123...")
                subprocess.run(['mpg123', '-q', converted_path], check=True)
                os.remove(converted_path)  # Remove the converted MP3 file after playback
            else:
                logging.error("Failed to convert WAV to MP3. Skipping playback.")
                return False
        else:
            # Attempt to play unsupported formats directly
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
        # Attempt to remove the sound file to clean up temporary files
        try:
            os.remove(sound_path)
            logging.debug(f"Cleaned up temporary file: {sound_path}")
        except Exception as e:
            logging.warning(f"Failed to clean up temporary file {sound_path}: {e}")

def get_color_message_from_db(config: Config) -> Optional[str]:
    """
    Fetch the color message from the database using a predefined complex SQL query.
    
    This function connects to the specified MSSQL database, executes a complex query to retrieve
    the next color message for wristband expirations, and returns the result.
    
    Args:
        config (Config): The configuration object containing database connection parameters.
    
    Returns:
        Optional[str]: The color message if retrieved successfully, None otherwise.
    """
    try:
        # Establish a connection to the MSSQL database using the provided configuration
        with pymssql.connect(
            server=config.database['server'],
            user=config.database['username'],
            password=config.database['password'],
            database=config.database['database'],
            timeout=30  # Set connection timeout to 30 seconds
        ) as conn:
            with conn.cursor() as cursor:
                # Define the SQL query to fetch the color message
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
                cursor.execute(query)  # Execute the SQL query
                row = cursor.fetchone()  # Fetch the first result row
                if row:
                    return str(row[0]).strip()  # Return the color message as a string
                logging.warning("No color data returned from database")
                return None
    except Exception as e:
        logging.error(f"Database error: {e}")
        return None

def calculate_next_announcement(times: Dict[str, str], current_time: datetime.datetime) -> Optional[Tuple[datetime.datetime, str]]:
    """
    Calculate the next scheduled announcement time and its type based on the current time.
    
    This function iterates through all configured announcement times, compares them with the current time,
    and determines which announcement is scheduled to occur next.
    
    Args:
        times (Dict[str, str]): A dictionary mapping time strings (HH:MM) to announcement types.
        current_time (datetime.datetime): The current datetime for comparison.
    
    Returns:
        Optional[Tuple[datetime.datetime, str]]: A tuple containing the next announcement time and its type,
                                                 or None if no upcoming announcements are found.
    """
    announcement_times = []  # List to store potential next announcements

    for time_str, announcement_type in times.items():
        try:
            # Parse the time string into hour and minute
            hour, minute = map(int, time_str.split(':'))
            # Create a datetime object for the announcement time today
            announcement_time = current_time.replace(
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0
            )

            if announcement_time <= current_time:
                continue  # Skip times that have already passed today

            announcement_times.append((announcement_time, announcement_type))
        except ValueError:
            logging.warning(f"Invalid time format in configuration: {time_str}")
            continue  # Skip invalid time formats

    if not announcement_times:
        return None  # No upcoming announcements found

    # Return the announcement with the earliest time
    return min(announcement_times, key=lambda x: x[0])

def convert_to_12hr_format(time_str: str) -> str:
    """
    Convert a time string from 24-hour format (HH:MM) to 12-hour format with AM/PM.
    
    This function parses the input time string, adjusts the hour to 12-hour format,
    and appends the appropriate AM or PM suffix.
    
    Args:
        time_str (str): The time string in 24-hour format (e.g., '14:30').
    
    Returns:
        str: The time string converted to 12-hour format with AM/PM (e.g., '2:30 PM').
    """
    try:
        hour, minute = map(int, time_str.split(':'))  # Split into hour and minute
        period = "PM" if hour >= 12 else "AM"  # Determine AM or PM
        if hour > 12:
            hour -= 12  # Adjust hour for 12-hour format
        elif hour == 0:
            hour = 12  # Midnight is represented as 12 AM
        return f"{hour}:{minute:02d} {period}"
    except Exception as e:
        logging.error(f"Error converting time format: {e}")
        return time_str  # Return the original string if conversion fails

def synthesize_announcement(template: str, announcement_type: str, time_str: str, color: str, config: Config) -> Optional[str]:
    """
    Generate an announcement audio file using Edge TTS based on the provided template and parameters.
    
    This function formats the announcement text, synthesizes speech using Edge TTS, and saves the
    resulting audio to a temporary file.
    
    Args:
        template (str): The template string for the announcement, potentially containing placeholders.
        announcement_type (str): The type of announcement (e.g., 'hour', 'ad', 'rules').
        time_str (str): The time string in 'HH:MM' format for inclusion in the announcement.
        color (str): The color associated with the announcement, used in certain announcement types.
        config (Config): The configuration object containing TTS settings.
    
    Returns:
        Optional[str]: The path to the synthesized announcement audio file if successful, None otherwise.
    """
    try:
        time_12hr = convert_to_12hr_format(time_str)  # Convert time to 12-hour format

        # Generate announcement text based on the type
        if announcement_type in ["rules", "ad"]:
            announcement_text = template  # Use the template as-is for 'rules' and 'ad'
        else:
            # For other types, format the template with time and color
            announcement_text = template.format(time=time_12hr, color=color)

        logging.info(f"Generated announcement text: {announcement_text}")

        # Determine the file suffix based on the desired output format
        suffix = f".{config.tts['output_format']}"
        # Create a temporary file to store the synthesized audio
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_path = temp_file.name

        # Synthesize speech asynchronously and save to the temporary file
        success = asyncio.run(
            synthesize_speech_async(announcement_text, config.tts['voice_id'], temp_path)
        )

        if success:
            return temp_path  # Return the path to the synthesized audio file
        else:
            return None  # Return None if synthesis failed
    except Exception as e:
        logging.error(f"Error generating announcement: {e}")
        return None

def main():
    """
    The main function orchestrates the loading of configurations, scheduling of announcements,
    synthesis of speech, and playback of audio files in a continuous loop.
    
    It handles shutdown signals gracefully and ensures that all resources are cleaned up
    appropriately upon termination.
    """
    # Add shutdown event if it doesn't exist to handle graceful termination
    if not hasattr(main, 'shutdown_event'):
        main.shutdown_event = threading.Event()

    try:
        config = load_config()  # Load configuration from 'config.ini'

        if not config.times:
            raise ValueError("No valid announcement times found in configuration")

        logging.info("Starting scheduled announcement player...")
        logging.info("Loaded announcement times:")
        for t, t_type in config.times.items():
            logging.info(f"  {t} -> {t_type}")

        # Define mapping for announcement types to their corresponding templates
        template_mapping = {
            ":55": "fiftyfive",
            "hour": "hour",
            "rules": "rules",
            "ad": "ad"
        }

        while True:
            current_time = datetime.datetime.now()  # Get the current datetime
            next_announcement = calculate_next_announcement(config.times, current_time)  # Determine the next announcement

            if not next_announcement:
                # If no more announcements today, calculate time until midnight
                tomorrow = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
                sleep_seconds = (tomorrow - current_time).total_seconds()
                logging.info(f"No more announcements today. Sleeping until midnight ({sleep_seconds} seconds)")
                # Wait until midnight or until a shutdown signal is received
                if main.shutdown_event.wait(timeout=sleep_seconds):
                    logging.info("Shutdown signal received, stopping announcement system...")
                    return
                continue  # Continue to the next iteration after waking up

            next_time, announcement_type = next_announcement  # Unpack the next announcement details
            sleep_seconds = (next_time - current_time).total_seconds()  # Calculate how long to sleep until the announcement

            if sleep_seconds > 0:
                logging.debug(f"Sleeping for {sleep_seconds} seconds until next announcement at {next_time}")
                # Use wait instead of sleep to allow for shutdown during the wait
                if main.shutdown_event.wait(timeout=sleep_seconds):
                    logging.info("Shutdown signal received, stopping announcement system...")
                    return  # Exit the loop and terminate the program

            # Select the appropriate template based on the announcement type
            template_key = template_mapping.get(announcement_type, "hour")
            template = config.announcements.get(template_key, "Attention! It's {time}.")

            # Initialize color message for specific announcement types
            color_message = ""
            if announcement_type in [":55", "hour"]:
                color_message = get_color_message_from_db(config)  # Fetch color message from the database
                if not color_message:
                    color = "unknown"  # Fallback color if database query fails
                    logging.warning(f"No color data returned. Using fallback 'unknown'")
                else:
                    # Extract just the color name from the message
                    color = color_message.split()[0]  # Assumes the color is the first word in the message

            # Generate the announcement audio file
            announcement_path = synthesize_announcement(
                template=template,
                announcement_type=announcement_type,
                time_str=next_time.strftime("%H:%M"),  # Format time as 'HH:MM'
                color=color if announcement_type in [":55", "hour"] else "",
                config=config
            )

            if announcement_path:
                # Play the synthesized announcement sound
                success = play_sound(announcement_path, config.tts['output_format'])
                if not success:
                    logging.error("Failed to play announcement")

            # Sleep briefly to avoid immediate next loop iteration
            time.sleep(1)

    except Exception as e:
        # Log any unhandled exceptions and exit the program with a critical error
        logging.critical(f"Unhandled exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()  # Execute the main function when the script is run directly
