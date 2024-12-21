// Loading overlay functions
function showLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.add('active');
    }
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
}

// Utility Functions
function formatTime(time) {
    const [hours, minutes] = time.split(':').map(Number);
    const period = hours >= 12 ? 'PM' : 'AM';
    const displayHours = hours % 12 || 12;
    return `${displayHours}:${minutes.toString().padStart(2, '0')} ${period}`;
}

function formatMinutes(minutes) {
    return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
}

// Update clock
function updateClock() {
    const clockElement = document.getElementById('clock');
    if (!clockElement) {
        console.error('Clock element not found');
        return;
    }

    const now = new Date();
    let hours = now.getHours();
    const minutes = now.getMinutes().toString().padStart(2, '0');
    const seconds = now.getSeconds().toString().padStart(2, '0');
    const ampm = hours >= 12 ? 'PM' : 'AM';

    hours = hours % 12;
    hours = hours ? hours : 12;
    hours = hours.toString().padStart(2, '0');

    clockElement.textContent = `${hours}:${minutes}:${seconds} ${ampm}`;
}

// Schedule Editor object
const scheduleEditor = {
    times: new Map(),

    init: function() {
        console.log('Initializing schedule editor...');
        this.setupEventListeners();
        this.updateScheduleList();
    },

    setupEventListeners: function() {
        const addTimeBtn = document.getElementById('addTimeBtn');
        if (addTimeBtn) {
            addTimeBtn.addEventListener('click', () => this.addTime());
            console.log('Add time button listener added');
        } else {
            console.error('Add time button not found');
        }
    },

    addTime: async function() {
        const timeInput = document.getElementById('newTime');
        const typeSelect = document.getElementById('newType');

        if (!timeInput || !typeSelect) {
            console.error('Time input or type select not found');
            return;
        }

        const time = timeInput.value;
        const type = typeSelect.value;

        if (!time || !type) {
            alert('Please select both time and announcement type');
            return;
        }

        showLoading();
        try {
            const response = await fetch('/add_time', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ time, type })
            });

            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || 'Failed to add time');
            }

            console.log('Time added successfully');
            await refreshState();
        } catch (error) {
            console.error('Error adding time:', error);
            alert(error.message);
        } finally {
            hideLoading();
        }
    },

    deleteTime: async function(time) {
        if (!confirm(`Are you sure you want to delete the ${time} announcement?`)) {
            return;
        }

        showLoading();
        try {
            const response = await fetch('/delete_time', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ time })
            });

            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || 'Failed to delete time');
            }

            console.log('Time deleted successfully');
            await refreshState();
        } catch (error) {
            console.error('Error deleting time:', error);
            alert(error.message);
        } finally {
            hideLoading();
        }
    },

    updateScheduleList: function() {
        const scheduleList = document.getElementById('scheduleList');
        const timesTextarea = document.getElementById('times');
        if (!scheduleList || !timesTextarea) {
            console.error('Schedule list or times textarea not found');
            return;
        }

        const timeEntries = [...this.times.entries()].sort();
        let html = '';

        timeEntries.forEach(([time, type]) => {
            const typeLabel = type.startsWith('custom:')
                ? `Custom: ${type.replace('custom:', '')}`
                : {
                    ':55': 'Color Warning',
                    'hour': 'Color Change',
                    'rules': 'Rules',
                    'ad': 'Advertisement'
                }[type] || type;

            html += `
                <div class="schedule-item" data-type="${type}">
                    <span class="time">${formatTime(time)}</span>
                    <span class="type">${typeLabel}</span>
                    <div class="actions">
                        <button type="button" class="btn-icon" onclick="scheduleEditor.deleteTime('${time}')">
                            🗑️
                        </button>
                    </div>
                </div>
            `;
        });

        scheduleList.innerHTML = html || '<div class="schedule-item"><span class="type">No announcements scheduled</span></div>';
        timesTextarea.value = timeEntries.map(([time, type]) => `${time} = ${type}`).join('\n');
    }
};

// Custom Types object
const customTypes = {
    types: new Map(),

    init: function() {
        console.log('Initializing custom types...');
        this.setupEventListeners();
        this.updateTypesList();
        this.updateTypeDropdown();
    },

    setupEventListeners: function() {
        const addTypeBtn = document.getElementById('addTypeBtn');
        if (addTypeBtn) {
            addTypeBtn.addEventListener('click', () => this.addType());
            console.log('Add type button listener added');
        } else {
            console.error('Add type button not found');
        }
    },

    addType: async function() {
        const nameInput = document.getElementById('newTypeName');
        const templateInput = document.getElementById('newTypeTemplate');

        if (!nameInput || !templateInput) {
            console.error('Name input or template input not found');
            return;
        }

        const name = nameInput.value.trim();
        const template = templateInput.value.trim();

        if (!name || !template) {
            alert('Please enter both name and template');
            return;
        }

        showLoading();
        try {
            const response = await fetch('/add_custom_type', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, template })
            });

            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || 'Failed to add custom type');
            }

            // Clear inputs and update lists
            nameInput.value = '';
            templateInput.value = '';
            console.log('Custom type added successfully');
            await refreshState();
        } catch (error) {
            console.error('Error adding custom type:', error);
            alert(error.message);
        } finally {
            hideLoading();
        }
    },

    updateTypesList: function() {
        const typesList = document.getElementById('customTypesList');
        const typesTextarea = document.getElementById('customTypes');
        if (!typesList || !typesTextarea) {
            console.error('Types list or types textarea not found');
            return;
        }

        let html = '';
        this.types.forEach((template, name) => {
            html += `
                <div class="custom-type-item">
                    <span class="name">${name}</span>
                    <span class="template">${template}</span>
                </div>
            `;
        });

        typesList.innerHTML = html || '<div class="custom-type-item"><span class="type">No custom types defined</span></div>';
        typesTextarea.value = [...this.types.entries()].map(([name, template]) => `${name} = ${template}`).join('\n');
    },

    updateTypeDropdown: function() {
        const typeSelect = document.getElementById('newType');
        if (!typeSelect) {
            console.error('Type select not found');
            return;
        }

        // Keep existing built-in options
        const builtInOptions = Array.from(typeSelect.options)
            .filter(option => !option.value.startsWith('custom:'));

        // Clear dropdown and add built-in options back
        typeSelect.innerHTML = '';
        builtInOptions.forEach(option => typeSelect.add(option));

        // Add custom types
        this.types.forEach((_, name) => {
            const option = new Option(`Custom: ${name}`, `custom:${name}`);
            typeSelect.add(option);
        });
    }
};

// Update upcoming announcements
function updateUpcomingAnnouncements(colorData = null) {
    console.log('Updating upcoming announcements...');
    const container = document.getElementById('upcomingList');
    if (!container) {
        console.error('Upcoming list container not found');
        return;
    }

    const timesTextarea = document.getElementById('times');
    if (!timesTextarea) {
        console.error('Times textarea not found');
        return;
    }

    const now = new Date();
    const lines = timesTextarea.value.trim().split('\n');
    container.innerHTML = '';

    const typeLabels = {
        ':55': 'Color Warning',
        'hour': 'Color Change',
        'rules': 'Rules',
        'ad': 'Advertisement'
    };

    const upcoming = lines
        .filter(line => line.trim())
        .map(line => {
            const [timeStr, type] = line.split('=').map(part => part.trim());
            const [hours, minutes] = timeStr.split(':').map(Number);
            const scheduleTime = new Date(now);
            scheduleTime.setHours(hours, minutes, 0, 0);

            if (scheduleTime < now) {
                scheduleTime.setDate(scheduleTime.getDate() + 1);
            }

            const minutesUntil = Math.round((scheduleTime - now) / 1000 / 60);

            if (minutesUntil <= 60) {
                return {
                    time: timeStr,
                    type,
                    minutesUntil,
                    scheduleTime
                };
            }
            return null;
        })
        .filter(item => item !== null)
        .sort((a, b) => a.scheduleTime - b.scheduleTime);

    if (upcoming.length === 0) {
        container.innerHTML = '<div class="upcoming-item"><span class="type">No announcements scheduled for the next hour</span></div>';
        return;
    }

    upcoming.forEach(({ time, type, minutesUntil }) => {
        const item = document.createElement('div');
        item.className = 'upcoming-item';
        item.dataset.type = type;

        const typeLabel = type.startsWith('custom:')
            ? `Custom: ${type.replace('custom:', '')}`
            : typeLabels[type] || type;

        let colorInfo = '';
        if (colorData && (type === ':55' || type === 'hour')) {
            const colorKey = type === ':55' ? 'color3' : 'color4';
            if (colorData[colorKey] && colorData[colorKey].color) {
                colorInfo = ` (${colorData[colorKey].color})`;
            }
        }

        item.innerHTML = `
            <span class="time">${formatTime(time)}</span>
            <span class="type">${typeLabel}${colorInfo}</span>
            <span class="countdown">in ${formatMinutes(minutesUntil)}</span>
        `;

        container.appendChild(item);
    });
    console.log('Upcoming announcements updated');
}

// Initialize instant announcement functionality
function setupInstantAnnouncement() {
    console.log('Setting up instant announcement...');
    const instantText = document.getElementById('instantText');
    const playInstantBtn = document.getElementById('playInstantBtn');
    const instantStatus = document.getElementById('instantStatus');

    if (!instantText || !playInstantBtn || !instantStatus) {
        console.error('Missing instant announcement elements:', {
            text: !!instantText,
            button: !!playInstantBtn,
            status: !!instantStatus
        });
        return;
    }

    playInstantBtn.addEventListener('click', async () => {
        const text = instantText.value.trim();
        if (!text) {
            instantStatus.textContent = 'Please enter announcement text';
            instantStatus.className = 'status-message error';
            return;
        }

        try {
            playInstantBtn.disabled = true;
            instantStatus.textContent = 'Playing announcement...';
            instantStatus.className = 'status-message';
            showLoading();

            const response = await fetch('/play_instant', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            instantStatus.textContent = 'Announcement played successfully';
            instantStatus.className = 'status-message success';
            instantText.value = '';
        } catch (error) {
            console.error('Error playing announcement:', error);
            instantStatus.textContent = `Error: ${error.message}`;
            instantStatus.className = 'status-message error';
        } finally {
            playInstantBtn.disabled = false;
            hideLoading();
        }
    });
    console.log('Instant announcement setup complete');
}

// Set up card toggling
function setupCardToggling() {
    console.log('Setting up card toggling...');
    document.querySelectorAll('.card h2').forEach(header => {
        header.addEventListener('click', () => {
            const card = header.closest('.card');
            if (card) {
                card.classList.toggle('collapsed');
                const icon = header.querySelector('.toggle-icon');
                if (icon) {
                    icon.textContent = card.classList.contains('collapsed') ? '▶' : '▼';
                }
            }
        });
    });
    console.log('Card toggling setup complete');
}

// Refresh state
async function refreshState() {
    console.log('Refreshing application state...');
    showLoading();
    try {
        const response = await fetch('/get_state');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log('Received state data:', data);

        // Update upcoming announcements
        updateUpcomingAnnouncements(data.color_data);

        // Update custom types
        if (data.custom_types) {
            customTypes.types = new Map(Object.entries(data.custom_types));
            customTypes.updateTypesList();
            customTypes.updateTypeDropdown();
        }

        // Update schedule
        if (data.times) {
            scheduleEditor.times = new Map(Object.entries(data.times));
            scheduleEditor.updateScheduleList();
        }

    } catch (error) {
        console.error('Failed to refresh state:', error);
        // Add visual error indication
        const upcomingList = document.getElementById('upcomingList');
        if (upcomingList) {
            upcomingList.innerHTML = `<div class="upcoming-item error">
                <span class="type">Error loading announcements: ${error.message}</span>
            </div>`;
        }
    } finally {
        hideLoading();
    }
}

// Initialize everything when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing application...');

    try {
        // Initialize clock
        updateClock();
        setInterval(updateClock, 1000);
        console.log('Clock initialized');

        // Setup components
        setupCardToggling();
        setupInstantAnnouncement();
        console.log('Components initialized');

        // Initialize main objects
        if (typeof scheduleEditor !== 'undefined') {
            scheduleEditor.init();
            console.log('Schedule editor initialized');
        } else {
            console.error('Schedule editor not defined');
        }

        if (typeof customTypes !== 'undefined') {
            customTypes.init();
            console.log('Custom types initialized');
        } else {
            console.error('Custom types not defined');
        }

        // Set up form submission handler
        const configForm = document.getElementById('configForm');
        if (configForm) {
            configForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                showLoading();

                try {
                    const formData = new FormData(configForm);

                    // Debug log form data
                    for (let [key, value] of formData.entries()) {
                        console.log(`Form data - ${key}: ${value}`);
                    }

                    const response = await fetch('/save_config', {
                        method: 'POST',
                        body: formData
                    });

                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.error || 'Failed to save configuration');
                    }

                    // Success handling
                    alert('Configuration saved successfully!');
                    window.location.reload();
                } catch (error) {
                    console.error('Error saving configuration:', error);
                    alert(`Error saving configuration: ${error.message}`);
                    hideLoading();
                }
            });
            console.log('Form submission handler initialized');
        } else {
            console.error('Config form not found');
        }

        // Initial state refresh
        refreshState();

        // Set up periodic refreshes
        setInterval(refreshState, 30000); // Every 30 seconds
        setInterval(() => updateUpcomingAnnouncements(), 10000); // Every 10 seconds

        console.log('All initialization complete');
    } catch (error) {
        console.error('Error during initialization:', error);
        alert('Error initializing application. Check console for details.');
    }
});
