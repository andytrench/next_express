import sys
import os
import subprocess
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                            QCheckBox, QComboBox, QFileDialog, QGroupBox,
                            QMessageBox, QProgressBar, QTextEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from datetime import datetime
import webbrowser
import time
import signal
import json
import re

class ProjectSetupThread(QThread):
    progress = pyqtSignal(str)
    log = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    dev_server_started = pyqtSignal(bool)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.dev_server_process = None

    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log.emit(f"[{timestamp}] {message}")

    def run_command(self, command, cwd, description, env=None):
        """
        Run a command and stream its output to the log
        """
        self.log_message(f"Running: {description}")

        # Merge provided environment variables with the default
        if env is not None:
            final_env = os.environ.copy()
            final_env.update(env)
        else:
            final_env = None

        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            env=final_env
        )

        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                self.log_message(output.strip())

        # Wait for the process to complete
        stdout, stderr = process.communicate()

        # Log any remaining output
        if stdout:
            self.log_message(stdout)
        if stderr:
            self.log_message(stderr)

        # Check for errors
        if process.returncode != 0:
            raise Exception(f"{description} failed: {stderr}")

        return process.returncode

    def run_command_with_input(self, command, cwd, description, responses, env=None):
        """
        Run a command and handle interactive prompts
        """
        import re
        import os

        self.log_message(f"Running: {description}")

        # Merge provided environment variables with the default
        if env is not None:
            final_env = os.environ.copy()
            final_env.update(env)
        else:
            final_env = None

        # Compile regex to remove ANSI escape sequences
        ansi_escape = re.compile(r'''
            \x1B  # ESC
            (?:   # 7-bit C1 Fe
                [@-Z\\-_]
            |     # or [ for CSI sequences
                \[
                [0-?]*  # Parameter bytes
                [ -/]*  # Intermediate bytes
                [@-~]   # Final byte
            )
        ''', re.VERBOSE)

        buffer = ''

        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=final_env
        )

        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                # Remove ANSI escape sequences
                clean_output = ansi_escape.sub('', output.strip())
                self.log_message(clean_output)
                buffer += clean_output + '\n'

                # Check if any of our prompts are in the buffer
                for prompt, response in responses.items():
                    if prompt in clean_output:
                        self.log_message(f"Responding to prompt: {prompt}")
                        process.stdin.write(response)
                        process.stdin.flush()
                        buffer = ''  # Reset buffer after finding a prompt
                        break

        # Wait for the process to complete
        stdout, stderr = process.communicate()

        # Log any remaining output
        if stdout:
            self.log_message(stdout)
        if stderr:
            self.log_message(stderr)

        # Check for errors
        if process.returncode != 0:
            raise Exception(f"{description} failed: {stderr}")

        return process.returncode

    def remove_ansi_escape_sequences(self, text):
        """
        Remove ANSI escape sequences from the text for cleaner matching
        """
        import re
        ansi_escape = re.compile(r'''
            \x1B  # ESC
            (?:   # 7-bit C1 Fe
                [@-Z\\-_]
            |     # or [ for CSI sequences
                \[
                [0-?]*  # Parameter bytes
                [ -/]*  # Intermediate bytes
                [@-~]   # Final byte
            )
        ''', re.VERBOSE)
        return ansi_escape.sub('', text)

    def check_dependencies(self):
        """Check if all required dependencies are installed"""
        try:
            # Check Node.js and npm
            node_version = subprocess.run(['node', '--version'], capture_output=True, text=True)
            npm_version = subprocess.run(['npm', '--version'], capture_output=True, text=True)
            
            if node_version.returncode != 0 or npm_version.returncode != 0:
                raise Exception("Node.js and npm are required but not found")
            
            # Check required global packages
            required_globals = ['next', 'create-next-app', 'typescript']
            for pkg in required_globals:
                result = subprocess.run(['npm', 'list', '-g', pkg], capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"Required global package {pkg} not found")
                
            return True
            
        except Exception as e:
            self.log_message(f"Dependency check failed: {str(e)}")
            return False

    def run(self):
        try:
            project_path = Path(self.config['project_path']) / self.config['project_name']
            
            # Initial progress
            self.progress.emit("Checking dependencies...")
            if not self.check_dependencies():
                raise Exception("Required dependencies not found. Please run setup.py first")

            # Project creation progress
            self.progress.emit("Creating Next.js project structure...")
            self.log_message(f"Creating project at: {project_path}")
            
            # Build create-next-app command with progress updates
            create_command = [
                'npx',
                '--yes',
                'create-next-app@latest',
                self.config['project_name'],
                '--ts' if self.config['use_typescript'] else '--js',
                '--tailwind' if self.config['use_tailwind'] else '--no-tailwind',
                '--eslint' if self.config['use_eslint'] else '--no-eslint',
                '--src-dir' if self.config['use_src_dir'] else '--no-src-dir',
                '--app' if self.config['use_app_router'] else '--pages',
                '--import-alias' if self.config['custom_import_alias'] else '--no-import-alias',
                '--use-npm'
            ]

            if self.config['custom_import_alias']:
                create_command.extend(['--import-alias', self.config['import_alias']])

            self.log_message(f"Running command: {' '.join(create_command)}")
            
            # Execute with real-time progress updates
            process = subprocess.Popen(
                create_command,
                cwd=self.config['project_path'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**os.environ, 'CI': 'true', 'NEXT_TELEMETRY_DISABLED': '1'}
            )

            # Stream output with progress updates
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    output = output.strip()
                    self.log_message(output)
                    
                    # Update progress based on output content
                    if "Creating" in output:
                        self.progress.emit("Creating project structure...")
                    elif "Installing" in output:
                        self.progress.emit("Installing dependencies...")
                    elif "Success" in output:
                        self.progress.emit("Project structure created!")

            # Check for errors
            if process.returncode != 0:
                stderr = process.stderr.read()
                raise Exception(f"Project creation failed: {stderr}")

            # Additional features installation
            if any([
                self.config['use_redux'],
                self.config['use_axios'],
                self.config['use_router'],
                self.config['use_auth'],
                self.config['use_prisma'],
                self.config['use_forms'],
                self.config['use_query']
            ]):
                self.progress.emit("Installing additional features...")
                self.install_additional_features(project_path)

            # Setup shadcn/ui
            self.progress.emit("Setting up shadcn/ui components...")
            self.setup_shadcn_and_utilities(project_path)

            # Git initialization
            if self.config['init_git']:
                self.progress.emit("Initializing Git repository...")
                self.run_command(['git', 'init'], project_path, "Initializing Git")

            # Build project
            if self.config['build_project']:
                self.progress.emit("Building project...")
                self.run_command(['npm', 'run', 'build'], project_path, "Building project")

            # Open in VS Code
            if self.config['open_vscode']:
                self.progress.emit("Opening in VS Code...")
                self.run_command(['code', '.'], project_path, "Opening VS Code")

            # Start development server
            if self.config['start_dev']:
                self.progress.emit("Starting development server...")
                self.start_dev_server(project_path)

            self.progress.emit("Project creation completed! 🚀")
            self.finished.emit(True, "Project created successfully!")

        except Exception as e:
            self.log_message(f"Error: {str(e)}")
            self.progress.emit("Error occurred during project creation")
            self.finished.emit(False, f"Error: {str(e)}")

    def install_project_dependencies(self, project_path):
        """Install project-specific dependencies"""
        try:
            deps = [
                '@radix-ui/react-icons',
                '@radix-ui/react-slot',
                'class-variance-authority',
                'clsx',
                'tailwind-merge',
                'lucide-react',
                'tailwindcss-animate'
            ]
            
            install_command = ['npm', 'install', '--save-dev'] + deps
            self.run_command(install_command, project_path, "Installing project dependencies")
            
        except Exception as e:
            raise Exception(f"Failed to install project dependencies: {str(e)}")

    def setup_shadcn_and_utilities(self, project_path):
        try:
            self.log_message("Setting up shadcn/ui with selected options...")

            # Install base dependencies
            deps = [
                '@radix-ui/react-icons',
                '@radix-ui/react-slot',
                'class-variance-authority',
                'clsx',
                'tailwind-merge',
                'lucide-react',
                'tailwindcss-animate'
            ]

            install_command = ['npm', 'install', '--save-dev'] + deps
            self.run_command(install_command, project_path, "Installing dependencies")

            # Initialize shadcn/ui with user preferences
            init_command = [
                'npx',
                'shadcn@latest',
                'init'
            ]

            # Set environment variables to handle peer dependencies
            env = {'NPM_CONFIG_LEGACY_PEER_DEPS': 'true'}

            # Convert style names to shadcn format
            style_map = {
                'Default': 'default',
                'New York': 'new-york',
                'Zinc': 'zinc',
                'Slate': 'slate',
                'Stone': 'stone',
                'Gray': 'gray'
            }
            
            style_name = self.config['ui_style']
            color_name = self.config['ui_color']
            shadcn_style = style_map.get(style_name, 'default')

            responses = {
                "Which style would you like to use?": f"{shadcn_style}\n",
                "Which color would you like to use as the base color?": f"{color_name.lower()}\n",
                "Would you like to use CSS variables for theming?": "yes\n" if self.config['use_css_vars'] else "no\n",
                "How would you like to proceed?": f"{self.config['react_compat']}\n"
            }

            self.run_command_with_input(init_command, project_path, "Initializing shadcn/ui", responses, env=env)

            self.log_message("shadcn/ui has been initialized with selected settings.")

        except Exception as e:
            self.log_message(f"Error setting up shadcn/ui: {str(e)}")
            raise e

    def start_dev_server(self, project_path):
        self.log_message("Starting development server...")
        dev_command = ['npm', 'run', 'dev']
        
        self.dev_server_process = subprocess.Popen(
            dev_command,
            cwd=project_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Wait for server to be ready
        ready = False
        start_time = time.time()
        while not ready and (time.time() - start_time) < 30:
            output = self.dev_server_process.stdout.readline()
            if output:
                self.log_message(output.strip())
                if "ready - started server on" in output or "Local:" in output:
                    port = int(output.split("localhost:")[1].strip())
                    ready = True
                    time.sleep(2)
                    break

        if ready:
            self.log_message(f"Development server is ready on port {port}!")
            if self.config['open_browser']:
                self.log_message(f"Opening in browser at port {port}...")
                webbrowser.open(f'http://localhost:{port}')

    def stop_dev_server(self):
        if self.dev_server_process:
            try:
                if os.name == 'posix':  # macOS and Linux
                    # Kill all Next.js processes
                    subprocess.run(['pkill', '-f', 'next'], stderr=subprocess.DEVNULL)
                else:
                    self.dev_server_process.terminate()
                
                self.dev_server_process.wait(timeout=5)
                self.log_message("Development server stopped.")
            except Exception as e:
                self.log_message(f"Error stopping server: {str(e)}")

class NextMakerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Next.js Project Creator")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        self.setup_thread = None
        self.initUI()

    def initUI(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Split into left and right panels
        h_layout = QHBoxLayout()
        left_panel = QVBoxLayout()
        right_panel = QVBoxLayout()

        # Basic Settings (Left Panel)
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QVBoxLayout()

        # Project Name
        name_layout = QHBoxLayout()
        self.name_input = QLineEdit()
        name_layout.addWidget(QLabel("Project Name:"))
        name_layout.addWidget(self.name_input)
        basic_layout.addLayout(name_layout)

        # Project Path
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        path_button = QPushButton("Browse")
        path_button.clicked.connect(self.browse_path)
        path_layout.addWidget(QLabel("Project Path:"))
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(path_button)
        basic_layout.addLayout(path_layout)

        # Package Manager
        pm_layout = QHBoxLayout()
        self.pm_combo = QComboBox()
        self.pm_combo.addItems(['npm', 'yarn', 'pnpm'])
        pm_layout.addWidget(QLabel("Package Manager:"))
        pm_layout.addWidget(self.pm_combo)
        basic_layout.addLayout(pm_layout)

        basic_group.setLayout(basic_layout)
        left_panel.addWidget(basic_group)

        # Next.js Options
        nextjs_group = QGroupBox("Next.js Options")
        nextjs_layout = QVBoxLayout()

        self.typescript_check = QCheckBox("TypeScript")
        self.tailwind_check = QCheckBox("Tailwind CSS")
        self.eslint_check = QCheckBox("ESLint")
        self.src_dir_check = QCheckBox("src/ Directory")
        self.app_router_check = QCheckBox("App Router")
        self.turbo_check = QCheckBox("Turbopack")

        # Import Alias
        alias_layout = QHBoxLayout()
        self.alias_check = QCheckBox("Custom Import Alias")
        self.alias_input = QLineEdit("@/*")
        self.alias_input.setEnabled(False)
        self.alias_check.stateChanged.connect(
            lambda state: self.alias_input.setEnabled(state == Qt.Checked)
        )
        alias_layout.addWidget(self.alias_check)
        alias_layout.addWidget(self.alias_input)

        nextjs_layout.addWidget(self.typescript_check)
        nextjs_layout.addWidget(self.tailwind_check)
        nextjs_layout.addWidget(self.eslint_check)
        nextjs_layout.addWidget(self.src_dir_check)
        nextjs_layout.addWidget(self.app_router_check)
        nextjs_layout.addWidget(self.turbo_check)
        nextjs_layout.addLayout(alias_layout)

        nextjs_group.setLayout(nextjs_layout)
        left_panel.addWidget(nextjs_group)

        # Style Options
        style_group = QGroupBox("Style Options")
        style_layout = QVBoxLayout()
        
        # Style selector
        style_selector_layout = QHBoxLayout()
        self.style_combo = QComboBox()
        self.style_combo.addItems([
            'Default',
            'New York',
            'Zinc',
            'Slate', 
            'Stone',
            'Gray'
        ])
        style_selector_layout.addWidget(QLabel("UI Style:"))
        style_selector_layout.addWidget(self.style_combo)
        
        # Color selector
        color_selector_layout = QHBoxLayout()
        self.color_combo = QComboBox()
        self.color_combo.addItems(['Neutral', 'Gray', 'Zinc', 'Stone', 'Slate'])
        color_selector_layout.addWidget(QLabel("Base Color:"))
        color_selector_layout.addWidget(self.color_combo)
        
        # Add tooltip with descriptions
        style_tooltip = (
            "Default: Standard style with neutral colors and rounded corners\n"
            "New York: Professional style with squared corners\n"
            "Zinc: Similar to default with Zinc color palette\n"
            "Slate: Uses Slate color palette\n"
            "Stone: Uses Stone color palette\n"
            "Gray: Uses Gray color palette"
        )
        self.style_combo.setToolTip(style_tooltip)
        
        # Update color selector based on style selection
        def update_color_options(style_name):
            self.color_combo.clear()
            if style_name.lower() in ['zinc', 'slate', 'stone', 'gray']:
                # For palette-specific styles, only show that color
                self.color_combo.addItem(style_name)
                self.color_combo.setEnabled(False)
            else:
                # For Default and New York styles, show all color options
                self.color_combo.addItems(['Neutral', 'Gray', 'Zinc', 'Stone', 'Slate'])
                self.color_combo.setEnabled(True)
        
        # Connect the signal after both combo boxes are created
        self.style_combo.currentTextChanged.connect(update_color_options)
        
        # Initialize color options based on default selection
        update_color_options(self.style_combo.currentText())
        
        # CSS Variables option
        self.css_vars_check = QCheckBox("Use CSS Variables for Theming")
        self.css_vars_check.setChecked(True)
        
        # React compatibility option
        self.react_compat_combo = QComboBox()
        self.react_compat_combo.addItems(['Use --force', 'Use --legacy-peer-deps'])
        compat_layout = QHBoxLayout()
        compat_layout.addWidget(QLabel("React Compatibility:"))
        compat_layout.addWidget(self.react_compat_combo)
        
        # Add tooltips
        self.color_combo.setToolTip("Choose the base color for your theme")
        self.css_vars_check.setToolTip("Enable CSS variables for dynamic theming")
        self.react_compat_combo.setToolTip("Choose how to handle React peer dependencies")
        
        # Add all layouts to style group
        style_layout.addLayout(style_selector_layout)
        style_layout.addLayout(color_selector_layout)
        style_layout.addWidget(self.css_vars_check)
        style_layout.addLayout(compat_layout)
        
        style_group.setLayout(style_layout)
        left_panel.addWidget(style_group)

        # Additional Features (Left Panel)
        features_group = QGroupBox("Additional Features")
        features_layout = QVBoxLayout()

        self.redux_check = QCheckBox("Redux Toolkit")
        self.axios_check = QCheckBox("Axios")
        self.router_check = QCheckBox("Next Router")
        self.auth_check = QCheckBox("NextAuth.js")
        self.prisma_check = QCheckBox("Prisma ORM")
        self.forms_check = QCheckBox("React Hook Form")
        self.query_check = QCheckBox("React Query")

        features_layout.addWidget(self.redux_check)
        features_layout.addWidget(self.axios_check)
        features_layout.addWidget(self.router_check)
        features_layout.addWidget(self.auth_check)
        features_layout.addWidget(self.prisma_check)
        features_layout.addWidget(self.forms_check)
        features_layout.addWidget(self.query_check)

        features_group.setLayout(features_layout)
        left_panel.addWidget(features_group)

        # Options
        options_group = QGroupBox("Additional Options")
        options_layout = QVBoxLayout()

        self.git_check = QCheckBox("Initialize Git Repository")
        self.build_check = QCheckBox("Build Project After Creation")
        self.open_vscode_check = QCheckBox("Open in VS Code After Creation")
        self.start_dev_check = QCheckBox("Start Development Server")
        self.open_browser_check = QCheckBox("Open in Browser")

        # Set defaults
        self.git_check.setChecked(False)
        self.build_check.setChecked(True)
        self.open_vscode_check.setChecked(True)
        self.start_dev_check.setChecked(True)
        self.open_browser_check.setChecked(True)

        options_layout.addWidget(self.git_check)
        options_layout.addWidget(self.build_check)
        options_layout.addWidget(self.open_vscode_check)
        options_layout.addWidget(self.start_dev_check)
        options_layout.addWidget(self.open_browser_check)

        options_group.setLayout(options_layout)
        left_panel.addWidget(options_group)

        # Add left panel to horizontal layout
        h_layout.addLayout(left_panel)

        # Log Window (Right Panel)
        log_group = QGroupBox("Installation Log")
        log_layout = QVBoxLayout()
        self.log_window = QTextEdit()
        self.log_window.setReadOnly(True)
        log_layout.addWidget(self.log_window)
        log_group.setLayout(log_layout)
        right_panel.addWidget(log_group)

        # Progress Bar (Right Panel)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        right_panel.addWidget(self.progress_bar)

        # Create Button (Right Panel)
        create_button = QPushButton("Create Project")
        create_button.clicked.connect(self.create_project)
        right_panel.addWidget(create_button)

        # Add right panel to horizontal layout
        h_layout.addLayout(right_panel)

        # Add the horizontal layout to the main layout
        layout.addLayout(h_layout)

        # Set default values for Next.js Options
        self.typescript_check.setChecked(True)
        self.tailwind_check.setChecked(True)
        self.eslint_check.setChecked(True)
        self.src_dir_check.setChecked(True)
        self.app_router_check.setChecked(True)
        self.turbo_check.setChecked(False)
        
        # Set default Import Alias
        self.alias_check.setChecked(True)
        self.alias_input.setText("@/*")
        self.alias_input.setEnabled(True)

        # Set default Package Manager
        pm_index = self.pm_combo.findText('npm')
        if pm_index >= 0:
            self.pm_combo.setCurrentIndex(pm_index)

        # Set default Additional Features (all unchecked)
        self.redux_check.setChecked(False)
        self.axios_check.setChecked(False)
        self.router_check.setChecked(False)
        self.auth_check.setChecked(False)
        self.prisma_check.setChecked(False)
        self.forms_check.setChecked(False)
        self.query_check.setChecked(False)

        # Set default Additional Options
        self.git_check.setChecked(False)
        self.build_check.setChecked(True)
        self.open_vscode_check.setChecked(True)
        self.start_dev_check.setChecked(True)
        self.open_browser_check.setChecked(True)

    def log_message(self, message):
        self.log_window.append(message)

    def browse_path(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Project Location")
        if folder:
            self.path_input.setText(folder)

    def create_project(self):
        if not self.name_input.text() or not self.path_input.text():
            QMessageBox.warning(self, "Error", "Project name and path are required!")
            return

        config = {
            'project_name': self.name_input.text(),
            'project_path': self.path_input.text(),
            'package_manager': self.pm_combo.currentText(),
            'use_typescript': self.typescript_check.isChecked(),
            'use_tailwind': self.tailwind_check.isChecked(),
            'use_eslint': self.eslint_check.isChecked(),
            'use_src_dir': self.src_dir_check.isChecked(),
            'use_app_router': self.app_router_check.isChecked(),
            'use_turbo': self.turbo_check.isChecked(),
            'custom_import_alias': self.alias_check.isChecked(),
            'import_alias': self.alias_input.text() if self.alias_check.isChecked() else "@/*",
            'use_redux': self.redux_check.isChecked(),
            'use_axios': self.axios_check.isChecked(),
            'use_router': self.router_check.isChecked(),
            'use_auth': self.auth_check.isChecked(),
            'use_prisma': self.prisma_check.isChecked(),
            'use_forms': self.forms_check.isChecked(),
            'use_query': self.query_check.isChecked(),
            'init_git': self.git_check.isChecked(),
            'build_project': self.build_check.isChecked(),
            'additional_deps': True,
            'open_vscode': self.open_vscode_check.isChecked(),
            'start_dev': self.start_dev_check.isChecked(),
            'open_browser': self.open_browser_check.isChecked(),
            'ui_style': self.style_combo.currentText(),
            'ui_color': self.color_combo.currentText(),
            'use_css_vars': self.css_vars_check.isChecked(),
            'react_compat': self.react_compat_combo.currentText()
        }

        self.setup_thread = ProjectSetupThread(config)
        self.setup_thread.progress.connect(self.update_progress)
        self.setup_thread.log.connect(self.log_message)
        self.setup_thread.finished.connect(self.setup_finished)
        self.setup_thread.start()

    def update_progress(self, message):
        self.progress_bar.setFormat(message)

    def setup_finished(self, success, message):
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)

    def closeEvent(self, event):
        # Stop the development server when closing the application
        if self.setup_thread and self.setup_thread.dev_server_process:
            self.setup_thread.stop_dev_server()
        event.accept()

def main():
    try:
        app = QApplication(sys.argv)
        print("Creating GUI window...")  # Debug print
        window = NextMakerGUI()
        print("Showing window...")  # Debug print
        window.show()
        print("Starting event loop...")  # Debug print
        return app.exec_()
    except Exception as e:
        print(f"Error starting GUI: {e}")
        return 1

if __name__ == "__main__":
    print("Starting Next.js Project Creator GUI...")
    sys.exit(main())