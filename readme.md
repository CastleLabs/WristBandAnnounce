# Automated Announcement System Documentation

## Overview
This Python script manages an automated announcement system for a venue with inflatable attractions. It handles timed announcements for wristband expiration, rules, and advertisements using text-to-speech technology. The system runs as systemd services, providing reliable operation and automatic restart capabilities.

## System Components

### 1. Announcement Engine (announcer.service)
- Runs as a systemd service
- Handles the core announcement functionality
- Manages scheduled announcements
- Interfaces with the database
- Controls text-to-speech operations

### 2. Web Configuration Interface (settings.service)
- Runs as a systemd service
- Provides a browser-based configuration interface
- Allows real-time configuration updates
- Automatically restarts announcer service when changes are made
- Features a modern, dark-themed user interface

### 3. Configuration Template (config.html)
- Responsive web interface for system configuration
- Real-time form validation
- Modern dark mode design
- Color-coded announcement types
- Dynamic schedule management

## Core Features

### Time-Based Announcements
- Manages scheduled announcements throughout operating hours
- Supports multiple announcement types:
  - Five-minute warnings for expiring wristbands (":55" announcements)
  - Expiration announcements (hour announcements)
  - Rules announcements
  - Advertisement messages
- Automatic service restart ensures immediate schedule updates

### Database Integration
- Connects to a Microsoft SQL Server database
- Retrieves color-coded wristband information
- Uses a complex query to determine current and upcoming wristband colors
- Maintains persistent database connection with error handling

### Text-to-Speech Capabilities
- Uses Microsoft Edge TTS for voice synthesis
- Supports MP3 audio format
- Includes automatic file cleanup after playback
- Handles multiple concurrent announcements

### Web Interface Features
- Immediate configuration updates
- Service auto-restart on changes
- Color-coded announcement types
- Real-time schedule management
- Secure configuration storage

## Installation and Setup

### Prerequisites
- Raspberry Pi OS or similar Linux system
- Python 3.x
- Required Python packages:
  ```bash
  pip3 install flask edge-tts pymssql
  ```
- System requirements:
  ```bash
  sudo apt-get install mpg123 ffmpeg
  ```

### Service Setup
1. Create service files:
```bash
sudo nano /etc/systemd/system/announcer.service
sudo nano /etc/systemd/system/settings.service
```

2. Configure services:
```ini
# announcer.service
[Unit]
Description=Wristband Announcer Service
After=network.target

[Service]
Type=simple
User=tech
Group=tech
WorkingDirectory=/home/tech
Environment=PYTHONUNBUFFERED=1
ExecStart=/usr/bin/python3 /home/tech/announcer.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```ini
# settings.service
[Unit]
Description=Wristband Settings Web Interface
After=network.target

[Service]
Type=simple
User=tech
Group=tech
WorkingDirectory=/home/tech
Environment=FLASK_APP=settings.py
Environment=FLASK_ENV=production
Environment=PYTHONUNBUFFERED=1
ExecStart=/usr/bin/python3 /home/tech/settings.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Set up permissions:
```bash
sudo visudo -f /etc/sudoers.d/announcer
```
Add:
```
tech ALL=(ALL) NOPASSWD: /bin/systemctl restart announcer.service
```

4. Enable and start services:
```bash
sudo systemctl enable announcer.service settings.service
sudo systemctl start announcer.service settings.service
```

### Directory Structure
```
/home/tech/
├── announcer.py
├── settings.py
├── config.ini
└── templates/
    └── config.html
```

## Service Management

### Common Commands
```bash
# Check service status
sudo systemctl status announcer.service
sudo systemctl status settings.service

# Restart services
sudo systemctl restart announcer.service
sudo systemctl restart settings.service

# View logs
sudo journalctl -u announcer.service -f
sudo journalctl -u settings.service -f
```

## Web Interface Usage

### Making Configuration Changes
1. Access the web interface at `http://your-pi-ip:5000`
2. Changes are applied immediately upon saving
3. Announcer service automatically restarts to pick up changes
4. Color-coded schedule items for easy identification

### Schedule Management
- Add announcements using the time picker and type selector
- Delete announcements with the X button
- Times automatically sort chronologically
- Color-coded by announcement type:
  - Color Warning (:55) - Blue
  - Color Change (hour) - Purple
  - Rules - Green
  - Advertisement - Orange

## Troubleshooting

### Common Issues
1. Service Not Starting
   - Check service status with systemctl
   - Review journal logs
   - Verify file permissions

2. Web Interface Not Accessible
   - Confirm settings service is running
   - Check network connectivity
   - Verify port 5000 is not blocked

3. Announcements Not Playing
   - Check audio device configuration
   - Verify database connectivity
   - Review announcer service logs

### Logging
- Services log to systemd journal
- Access logs with journalctl
- Each service has separate log stream

## Best Practices
1. Regular monitoring of service status
2. Check logs for any errors
3. Test new announcements during quiet periods
4. Keep database credentials secure
5. Regular system updates
6. Backup config.ini regularly
