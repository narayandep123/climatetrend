# Windows Setup and Run Guide

This project can be run locally on Windows by setting up both the Python backend and the React frontend.

## 1) Install required software

Make sure these are installed on the machine:

- Python 3.10 or newer
- Node.js 18 or newer
- npm (usually comes with Node.js)

You can check versions with:

```powershell
python --version
node --version
npm --version
```

## 2) Extract the project

Unzip the project folder to a location like:

```text
C:\Users\YourName\Desktop\CHTrendAnalyzer
```

## 3) Open PowerShell in the project folder

```powershell
cd C:\path\to\CHTrendAnalyzer
```

## 4) Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks scripts, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then retry the activation command.

## 5) Install backend dependencies

```powershell
pip install --upgrade pip
pip install -r .\backend\requirements.txt
```

## 6) Install frontend dependencies

```powershell
cd frontend
npm install
```

## 7) Run the backend

From the project root:

```powershell
cd ..
python .\backend\manage.py runserver 0.0.0.0:8000
```

The backend should start on:

```text
http://localhost:8000
```

## 8) Run the frontend

Open a second terminal and run:

```powershell
cd C:\path\to\CHTrendAnalyzer\frontend
npm run dev -- --host 0.0.0.0
```

The frontend should start on:

```text
http://localhost:5173
```

## 9) Open the app

Open your browser and go to:

```text
http://localhost:5173
```

## 10) Notes

- No MongoDB installation is required for local use because the app uses a lightweight local in-memory cache fallback.
- No API key is required for the current public weather data sources.
- If the frontend cannot connect to the backend, make sure both terminals are running and the backend is still active.
- If a package is missing, run `npm install` again inside the frontend folder.

## Quick summary

```powershell
cd C:\path\to\CHTrendAnalyzer
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r .\backend\requirements.txt
cd frontend
npm install
cd ..
python .\backend\manage.py runserver 0.0.0.0:8000
```

Then in a second terminal:

```powershell
cd C:\path\to\CHTrendAnalyzer\frontend
npm run dev -- --host 0.0.0.0
```
