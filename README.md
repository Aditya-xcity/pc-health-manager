# PC Health Manager

A lightweight desktop utility for Windows built with Tkinter and psutil to monitor system health in real time.

## Features

- Live CPU, RAM, and disk usage dashboard
- Color-coded status indicators (healthy, moderate, high)
- Top heavy process list with CPU and memory usage
- Smart suggestions when system load is high
- One-click process termination for selected tasks
- Manual refresh support

## Requirements

- Python 3.9+
- psutil
- Windows (recommended)

## Installation

1. (Optional) Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install psutil
```

## Run

From the project root:

```bash
python pc_health_manager.py
```

## Notes

- On Windows, process termination uses `taskkill /T /F` for reliable force kill and child-process cleanup.
- Tkinter is included with most standard Python installations on Windows.

## File Structure

```text
.
|-- pc_health_manager.py
|-- README.md
|-- .gitignore
```

## License

No license file is currently included. Add one if you plan to distribute this project.
