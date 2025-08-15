# 📊 Copilot Usage Analysis Web Tool

A sleek, real-time web application for analyzing Microsoft Copilot usage reports. This tool processes all data in-memory, provides live progress updates, and allows for direct downloads of generated Excel and HTML reports.

https://github.com/mc0l85/cpl-web/blob/d59d849187ca82202ee0849ca42a0ce01eb021f1/screenshot.jpg
*(A snapshot of the web application's user interface)*

I removed the extra parentheses around the URL to ensure proper rendering. Let me know if you'd like help embedding this in a README or documentation page.

---

## ✨ Features

* **Modern Web UI**: A responsive, dark-themed interface built with Bootstrap.
* **In-Memory Processing**: No files are stored on the server, ensuring privacy and efficiency.
* **Real-Time Updates**: See the status of your analysis live, powered by WebSockets.
* **Dynamic Filtering**: Interactively filter user data by company, department, location, or manager.
* **Automated User Classification**: Users are automatically categorized into five groups: **Power User**, **Consistent User**, **Coaching Opportunity**, **New User**, and **License Recapture**.
* **Direct Downloads**: Download the comprehensive Excel report and interactive HTML leaderboard directly from your browser.
* **User Deep Dive**: Search for a specific user to see detailed stats and a usage trend chart.

---

## 🛠️ Requirements

* A Linux environment (like Ubuntu, Debian, etc.)
* **Python 3.8** or newer
* The `pip` package installer for Python
* The `git` command-line tool

Most modern Linux distributions come with these pre-installed. You can check by opening a terminal and running `python3 --version`, `pip --version`, and `git --version`.

---

## 🚀 Getting Started

Follow these steps in your Linux terminal to get the application running on your local machine.

### Step 1: Clone the Repository

First, you need to download the project files. We'll use **git** to "clone" the repository from its source.

```bash
# This command downloads the project into a new folder called "copilot-web-app"
git clone <repository_url>

# Now, move into the newly created project directory
cd copilot-web-app
```

### Step 2: Install Dependencies

It's highly recommended to use a Python virtual environment to manage project dependencies. This prevents conflicts with other Python projects on your system.

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install the required Python packages
pip install pandas numpy matplotlib openpyxl flask flask-socketio eventlet
```

Remember to activate the virtual environment (`source venv/bin/activate`) every time you open a new terminal and want to work on this project. To deactivate it, simply run `deactivate`.

---

## 🧪 Testing

This project uses `pytest` for testing. All tests are located in the `tests/` directory.

To run the tests, make sure you have `pytest` installed (`pip install pytest`) and then run the following command from the root of the project:

```bash
pytest
```
