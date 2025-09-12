# 📊 Copilot Usage Analysis Web Tool

A sleek, real-time web application for analyzing Microsoft Copilot usage reports. This tool processes all data in-memory, provides live progress updates, and allows for direct downloads of generated Excel and HTML reports.



---

## ✨ Features

*   **Modern Web UI**: A responsive, dark-themed interface built with Bootstrap.
*   **In-Memory Processing**: No files are stored on the server, ensuring privacy and efficiency.
*   **Real-Time Updates**: See the status of your analysis live, powered by WebSockets.
*   **Dynamic Filtering**: Interactively filter user data by company, department, location, or manager.
*   **Automated User Classification**: Users are automatically categorized into five groups: **Power User**, **Consistent User**, **Coaching Opportunity**, **New User**, and **License Recapture**.
*   **NEW: Relative Use Index (RUI)**: Fair license usage assessment using manager-based peer comparisons. Users are scored 0-100 based on recency, frequency, breadth, and trend relative to their immediate team.
*   **Direct Downloads**: Download the comprehensive Excel report and interactive HTML leaderboard directly from your browser. The Excel report now includes:
    * **RUI Analysis** sheet with individual scores and license risk levels
    * **Manager Summary** sheet showing team-level metrics
    * **Usage_Trend** sheet with a graph showing **Average Tools Used Over Time**
*   **User Deep Dive**: Search for a specific user to see detailed stats and a usage trend chart of their **average tools used**.

---

## 🛠️ Requirements

*   A Linux environment (like Ubuntu, Debian, etc.)
*   **Python 3.8** or newer
*   The `pip` package installer for Python
*   The `git` command-line tool

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
pip install -r requirements.txt
```

Remember to activate the virtual environment (`source venv/bin/activate`) every time you open a new terminal and want to work on this project. To deactivate it, simply run `deactivate`.

### Step 3: Running the Application

Once the dependencies are installed, you can start the Flask development server.

```bash
# Make sure your virtual environment is activated
python3 app.py
```

The application will typically be accessible at `http://127.0.0.1:5000` in your web browser.

---

## 🧪 Testing

This project uses `pytest` for testing. All tests are located in the `tests/` directory.

To run the tests, make sure your virtual environment is activated and then run the following command from the root of the project:

```bash
pytest
```

---

## 📊 Relative Use Index (RUI) System

The RUI system provides a fairer approach to license management by comparing users to their immediate peers rather than using arbitrary thresholds.

### How RUI Works

Each user receives a score from 0-100 based on four components:

1. **Recency (40%)**: How recently tools were used (30-day half-life decay)
2. **Frequency (30%)**: How consistently tools are used across reporting periods  
3. **Breadth (20%)**: Diversity of tool usage (average tools per report)
4. **Trend (10%)**: Whether usage is growing, stable, or declining

### Peer Group Formation

Users are compared to others reporting to the same manager (minimum 5 users). If a manager has fewer than 5 direct reports, the system automatically walks up the management hierarchy until a sufficient peer group is found.

### License Risk Categories

- **New User (< 90 days)**: Protected during 90-day grace period for onboarding
- **Low Risk (RUI ≥ 40)**: License should be retained
- **Medium Risk (RUI 20-39)**: User should be notified to increase usage
- **High Risk (RUI < 20)**: License is a candidate for reclamation (except new users)

### Excel Report Tabs

**RUI Analysis Tab**
- Individual RUI scores and risk levels
- Peer ranking (e.g., "3 of 8")
- Manager and department information
- Usage trend indicators

**Manager Summary Tab**
- Team-level aggregations
- Average team RUI scores
- Count of users in each risk category
- Action items for managers
