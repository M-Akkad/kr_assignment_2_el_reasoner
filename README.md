# EL Reasoner Shell Script

## Prerequisites

- Python 3.8+
- Java Runtime Environment (JRE)

## Setup Instructions

### 1. Create a Virtual Environment

It's recommended to use a virtual environment to manage dependencies:

```bash
# For Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# For Windows (Command Prompt)
python -m venv venv
venv\Scripts\activate.bat

# For Unix/macOS
python3 -m venv venv
source venv/bin/activate
```

> [!NOTE]
> If you encounter permission issues on Unix/macOS, you might need to use `python` instead of `python3`, depending on your Python installation.

### 2. Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

### 3. Make the Script Executable

#### For Unix/macOS:

```bash
chmod +x run
```

#### For Windows:

```powershell
# No additional steps needed - Windows uses .bat or .ps1 scripts
```

## Usage

### Unix/macOS:

```bash
./run Ontology.owl ClassName
```

### Windows:

```powershell
# Use the appropriate script based on your shell
.\run.bat Ontology.owl ClassName
# or
.\run.ps1 Ontology.owl ClassName
```

### Example

```bash
# Unix/macOS
./run ontologies/pizza.owl Margherita

# Windows
.\run Ontology.owl Margherita
```

## Script Functionality

The script performs the following operations:

- Validates the number of input arguments
- Checks for the existence of required files
- Launches a Java server using `dl4python-0.1.2-jar-with-dependencies.jar`
- Executes the `El_reasoner.py` Python script with provided arguments
- Terminates the Java server after reasoning is complete

## Troubleshooting

### Common Issues

1. **Virtual Environment**

   - Ensure you've activated the virtual environment before running the script
   - Verify Python version compatibility (`python --version`)

2. **Dependencies**

   - Confirm all requirements are installed: `pip list`
   - Reinstall requirements if needed: `pip install -r requirements.txt`

3. **Java Runtime**

   - Check Java installation: `java -version`
   - Ensure Java is in your system PATH

4. **Script Execution**

   - Verify file permissions on Unix/macOS
   - Check script compatibility with your shell (Bash, PowerShell, etc.)

5. **File Paths**

   - Use absolute paths if relative paths cause issues
   - Ensure `dl4python-0.1.2-jar-with-dependencies.jar` is in the correct directory

## Platform-Specific Notes

### Windows

- Use PowerShell or Command Prompt for script execution
- Some Unix-style commands may require alternative Windows commands

### Unix/macOS

- Bash or Zsh shells are recommended
- Ensure executable permissions are set

## Potential Modifications

You might want to create platform-specific wrapper scripts:

- `run.bat` for Windows
- `run.sh` for Unix/macOS

These scripts can handle platform-specific nuances in script execution.
