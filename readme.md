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
server = <server_address>
database = <database_name>
username = <username>
password = <password>

[times]
# Announcement times in 24-hour format
10:55 = :55
11:00 = hour
# ... additional times

[announcements]
fiftyfive = "Attention inflate-a-park guests: The time is now {time}, {color} wristbands will be expiring in five minutes!"
hour = "Attention inflate-a-park guests: The time is now {time}, {color} wristbands have expired. Please exit the inflate-a-park at this time."

[tts]
voice_id = en-US-AndrewMultilingualNeural
output_format = mp3
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
