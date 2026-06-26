Report-app startup flow:

cd D:\my-app\report-app
.\venv\Scripts\activate
python app.py

Fix it step by step
1) Check if Python exists

Run:

py --version

or

python --version

If both fail → install Python.

2) Install Python properly

Download Python from:

Python official website

While installing:

✅ Check "Add Python to PATH"
✅ Choose Install Now

This is the step most people miss.

3) Disable Microsoft Store alias (if needed)

Your screenshot shows:

"run without arguments to install from Microsoft Store"

Disable that shortcut:

Settings → Apps → Advanced App Settings → App Execution Aliases

Turn OFF:

python.exe
python3.exe
4) Restart PowerShell

Close PowerShell completely and reopen it.

Then verify:

python --version
pip --version

You should see version numbers.

5) Create virtual environment

Inside your project folder:

python -m venv venv
6) Activate virtual environment

In PowerShell:

.\venv\Scripts\Activate

If PowerShell blocks scripts:

Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

Then run activation again.

7) Install Flask
pip install flask
Full correct flow
python --version
python -m venv venv
.\venv\Scripts\Activate
pip install flask

8) Install pandas inside your active venv:

pip install pandas

pip install python-docx openpyxl reportlab pillow requests

pip install streamlit

RCA
"""""""""
pip install nltk scikit-learn

Converter
"""""""""
pip install python-pptx python-docx pdf2image pillow

pip install python-pptx 
pip install pdf2image
pip install python-docx

Operations Center
"""""""""""""""""
pip install selenium webdriver-manager
pip install pywin32
pip install msal requests --> email notifier

Windchill monitoring
""""""""""""""""""""
pip install beautifulsoup4 lxml
pip install pyperclip


#############-----------------------------------------##############################

Backup or sync with GITHUB
""""""""""""""""""""""""""
1) Open terminal / command prompt

Navigate to your project folder:

cd path/to/my-app

Example:

cd C:\Users\YourName\Projects\my-app

or on Mac/Linux:

cd ~/Projects/my-app
2) Initialize Git (if not already initialized)
git init

This creates a local Git repository.

3) Check files
git status

You’ll see all untracked files.

4) Add a .gitignore file (important)

Avoid pushing unnecessary files like virtual environments, build folders, secrets, etc.

Example for Python app:

venv/
__pycache__/
.env
*.pyc

Example for Node/React app:

node_modules/
.env
dist/
build/

Create it:

touch .gitignore

(Windows users can create manually in Notepad.)

5) Add files to Git
git add .
6) Commit files
git commit -m "Initial commit"
7) Create a new repository on GitHub

Go to:

GitHub → New Repository

Give repo name (e.g. my-app)
Keep it public/private as needed
Don’t add README/gitignore/license if your local project already has files

Click Create repository

8) Connect local project to GitHub repo

Copy the repo URL from GitHub and run:

git remote add origin https://github.com/yourusername/my-app.git
9) Push code to GitHub

For newer Git versions:

git branch -M main
git push -u origin main

If your branch is master:

git push -u origin master


Typical workflow after you change code locally:
#See what changed.
git status

#Stage changes.
git add .

#Save changes locally.
git commit -m "Describe what changed"

#Upload changes to GitHub.
git push

#To pull changes from GitHub to another machine
git pull