# Automated Announcement System Documentation

## Overview
This Python script manages an automated announcement system for a venue with inflatable attractions. It handles timed announcements for wristband expiration, rules, and advertisements using text-to-speech technology. The system includes both a core announcement engine and a web-based configuration interface.

## System Components

### 1. Announcement Engine (announcer.py)
- Handles the core announcement functionality
- Manages scheduled announcements
- Interfaces with the database
- Controls text-to-speech operations

### 2. Web Configuration Interface (settings.py)
- Provides a browser-based configuration interface
- Allows real-time configuration updates
- Supports immediate configuration changes without system restart
- Features a modern, dark-themed user interface

### 3. Configuration Template (config.html)
- Responsive web interface for system configuration
- Real-time form validation
- Modern dark mode design
- Floating save button for easy access

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

### Web Interface Features
- Real-time configuration updates
- Live preview of changes
- Secure configuration storage
- Automatic service restart on save
- User-friendly form validation

## Configuration Management

### Web Interface Sections
1. Database Configuration
   - Server address
   - Database name
   - Username
   - Password

2. Announcement Times
   - Time schedule editor
   - Support for multiple announcement types
   - Format: HH:MM = type

3. Announcement Templates
   - 55-minute warning template
   - Hour announcement template
   - Rules announcement template
   - Advertisement template

4. TTS Configuration
   - Voice ID selection
   - Output format settings

### Configuration File Structure
```ini
[database]
server = 192.168.1.2
database = CenterEdge
username = Tech
password = yourpassword

[times]
10:55 = :55
11:00 = hour
# Additional times...

[announcements]
fiftyfive = Attention inflate-a-park guests: The time is now {time}, {color} wristbands will be expiring in five minutes!
hour = Attention inflate-a-park guests: The time is now {time}, {color} wristbands have expired.
rules = Attention! Here are the rules: {rules_content}
ad = Announcement! {ad_message}

[tts]
voice_id = en-US-AndrewMultilingualNeural
```

## Installation and Setup

### Prerequisites
- Python 3.x
- Required Python packages:
  ```bash
  pip install flask edge-tts pymssql
  ```
- System requirements:
  - ffmpeg
  - mpg123
  - Network connectivity
  - Audio output capabilities

### Directory Structure
```
/your_installation_directory/
├── announcer.py
├── settings.py
├── config.ini
└── templates/
    └── config.html
```

### Starting the System
1. Start the web interface:
   ```bash
   python settings.py
   ```
2. Access the configuration interface:
   ```
   http://localhost:5000
   ```

## Web Interface Usage

### Making Configuration Changes
1. Navigate to the web interface
2. Modify desired settings
3. Click the floating "Save Configuration" button
4. Wait for confirmation of successful save

### Configuration Sections
1. **Database Settings**
   - Configure database connection parameters
   - All fields are required

2. **Announcement Times**
   - Add/remove announcement times
   - Format: HH:MM = type
   - Supported types: :55, hour, rules, ad

3. **Announcement Templates**
   - Edit message templates
   - No quotes required around messages
   - Supports placeholders: {time}, {color}

4. **TTS Settings**
   - Configure voice settings
   - Select voice ID

## Technical Details

### Threading Model
- Main announcement thread runs as daemon
- Web interface runs in main thread
- Configuration changes trigger clean restart
- Thread synchronization via Events

### Configuration Handling
- Real-time configuration file parsing
- Clean shutdown and restart on changes
- Quote-aware string handling
- Automatic format validation

### Security Considerations
- Password fields are masked
- Form validation prevents injection
- Configuration file permissions should be restricted

## Troubleshooting

### Common Issues
1. Configuration Not Updating
   - Check file permissions
   - Verify save operation success
   - Check logs for errors

2. Web Interface Not Accessible
   - Verify port 5000 is available
   - Check Python process is running
   - Confirm network connectivity

3. Announcements Not Playing
   - Check audio device configuration
   - Verify database connectivity
   - Check log files for errors

### Logging
- Web interface logs to console/debug mode
- Announcement system logs to announcement_script.log
- Both components log error conditions

## Best Practices
1. Regular backup of configuration
2. Monitor log files
3. Test configuration changes during non-peak hours
4. Maintain secure database credentials
5. Regular system updates
