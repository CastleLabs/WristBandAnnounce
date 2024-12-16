# Automated Announcement System Documentation

## Overview
This Python script manages an automated announcement system for a venue with inflatable attractions. It handles timed announcements for wristband expiration, rules, and advertisements using text-to-speech technology.

## Core Features

### Time-Based Announcements
- Manages scheduled announcements throughout operating hours
- Supports multiple announcement types:
  - Five-minute warnings for expiring wristbands (":55" announcements)
  - Expiration announcements (hour announcements)
  - Rules announcements
  - Advertisement messages

### Database Integration
- Connects to a Microsoft SQL Server database
- Retrieves color-coded wristband information
- Uses a complex query to determine current and upcoming wristband colors

### Text-to-Speech Capabilities
- Uses Microsoft Edge TTS for voice synthesis
- Supports multiple audio formats (MP3 and WAV)
- Includes audio format conversion capabilities using ffmpeg

## Technical Components

### Configuration Management
The script uses an INI-style configuration file with sections for:
- Database connection settings
- Announcement schedules
- Message templates
- TTS settings
- Rules content
- Advertisement messages

### Audio Processing
- Supports dynamic audio synthesis using Edge TTS
- Handles audio format conversion using ffmpeg
- Uses mpg123 for audio playback
- Manages temporary file creation and cleanup

### Logging System
- Comprehensive logging with both file and console output
- Debug-level logging available
- Tracks important events, errors, and system status

## Main Process Flow

1. Load configuration from INI file
2. Enter main loop:
   - Calculate next announcement time
   - Sleep until next scheduled announcement
   - Fetch color information from database (if needed)
   - Generate announcement audio using TTS
   - Play announcement
   - Clean up temporary files

## Error Handling
- Robust error handling for database connections
- Audio synthesis and playback error recovery
- Configuration validation
- Temporary file management

## Dependencies

### Required Python Packages
- edge_tts: Text-to-speech synthesis
- pymssql: Microsoft SQL Server connectivity
- asyncio: Asynchronous I/O support
- datetime: Date and time handling
- logging: System logging
- tempfile: Temporary file management
- pathlib: File path operations
- typing: Type hints

### System Requirements
- Python 3.x
- Microsoft SQL Server database
- ffmpeg installation
- mpg123 installation
- Network connectivity for database access
- Audio output capabilities

## Configuration File Structure

```ini
[database]
# Database connection settings
server = [REDACTED_IP]
database = [REDACTED_DB_NAME]
username = [REDACTED_USER]
password = [REDACTED_PASSWORD]

[times]
# Announcement times in 24-hour format (HH:MM) mapped to announcement types
# Example: 08:55 = :55 indicates an announcement type for 55 minutes past the hour
10:55 = :55
11:00 = hour
11:55 = :55
12:00 = hour
12:55 = :55
13:00 = hour
13:55 = :55
14:00 = hour
14:55 = :55
15:00 = hour
15:55 = :55
16:00 = hour
16:55 = :55
17:00 = hour
17:55 = :55
18:00 = hour
# Add more times as needed

[announcements]
# Announcement templates using placeholders {time} and {color}
# {time} will be replaced with the scheduled time
# {color} will be replaced with the color fetched from the database
fiftyfive = "Attention inflate-a-park guests: The time is now {time}, {color} wristbands will be expiring in five minutes!"
hour = "Attention inflate-a-park guests: The time is now {time}, {color} wristbands have expired. Please exit the inflate-a-park at this time."

[rules]
# Rules announcement content
# This will be read when a rules announcement is scheduled
rules_content = "Attention inflate-a-park guests! Please remember our safety rules: 1. No running in the inflate-a-park. 2. Follow staff instructions at all times. 3. One person per slide at a time. 4. No food, drinks, or shoes in the inflatables. 5. Adult supervision is required for children under 12."

[ad]
# Advertisement message content
# This will be read when an advertisement announcement is scheduled
ad_message = "Looking for more bounce time? Visit our front desk to purchase additional time on your wristband! We also offer party packages for birthdays and special events. Ask our staff for details!"

[tts]
# Text-to-Speech (TTS) configuration
# voice_id corresponds to the desired Edge TTS voice
# output_format determines the audio file format ('wav' or 'mp3')
voice_id = en-US-AndrewMultilingualNeural
output_format = wav
```

## Function Reference

### Core Functions

#### `load_config(config_path: str) -> Config`
Loads and validates configuration from the specified INI file.

#### `synthesize_speech_async(text: str, voice_id: str, output_path: str) -> bool`
Asynchronously generates speech audio from text using Edge TTS.

#### `play_sound(sound_path: str, output_format: str) -> bool`
Plays the generated announcement audio file.

#### `get_color_message_from_db(config: Config) -> Optional[str]`
Retrieves current wristband color information from the database.

#### `calculate_next_announcement(times: Dict[str, str], current_time: datetime.datetime) -> Optional[Tuple[datetime.datetime, str]]`
Determines the next scheduled announcement time and type.

### Utility Functions

#### `convert_to_12hr_format(time_str: str) -> str`
Converts 24-hour time format to 12-hour format with AM/PM.

#### `convert_audio_format(input_path: str, output_path: str, target_format: str) -> bool`
Converts audio files between different formats using ffmpeg.

## Error Logging

The system maintains detailed logs with the following information:
- Timestamp
- Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Event description
- Error details and stack traces when applicable

Logs are written to both:
- Console output (stdout)
- Log file (announcement_script.log)

## Maintenance and Troubleshooting

### Common Issues
1. Database Connection Failures
   - Check network connectivity
   - Verify database credentials
   - Confirm SQL Server is running

2. Audio Playback Issues
   - Verify ffmpeg installation
   - Check mpg123 installation
   - Confirm audio output device availability

3. Configuration Problems
   - Validate INI file syntax
   - Check file permissions
   - Verify all required sections are present

### Best Practices
1. Regular monitoring of log files
2. Periodic testing of database connectivity
3. Validation of announcement schedules
4. Regular backup of configuration files
5. Testing of audio output quality
