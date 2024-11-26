# Next Express

A powerful GUI tool for creating optimized Next.js projects with shadcn/ui components and best practices for V0 and other projects.

## Prerequisites

- Python 3.8+
- Node.js 20+ (LTS recommended)
- npm 10+

## Complete Setup Guide

### 1. Python Environment Setup

```bash
# Create Python virtual environment
python -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Node.js Dependencies Setup

```bash
# Install required global packages
npm install -g next@latest create-next-app@latest typescript@latest shadcn-ui@latest

# Verify installations
node --version  # Should show 20.x.x
npm --version   # Should show 10.x.x
```

### 3. Launch Next Express

```bash
# Make sure your virtual environment is activated (.venv)
python next_express.py
```

### 4. Using the GUI

1. Enter your project details:
   - Project name
   - Project location (use "Browse" button)
   - Package manager (npm, yarn, or pnpm)

2. Configure Next.js options:
   - TypeScript (recommended)
   - Tailwind CSS
   - ESLint
   - src/ Directory
   - App Router
   - Custom Import Alias (@/*)

3. Select additional features:
   - Redux Toolkit
   - Axios
   - Next Router
   - NextAuth.js
   - Prisma ORM
   - React Hook Form
   - React Query

4. Choose build options:
   - Initialize Git Repository
   - Build Project After Creation
   - Open in VS Code
   - Start Development Server
   - Open in Browser

5. Click "Create Project" and monitor the installation log

### 5. Project Structure

Your generated project will include:
```
your-project/
├── src/
│   ├── app/              # Next.js App Router
│   ├── components/       # React components
│   │   ├── ui/          # shadcn/ui components
│   │   ├── layout/      # Layout components
│   │   └── forms/       # Form components
│   ├── lib/             # Utility functions
│   ├── styles/          # CSS and theme files
│   ├── types/           # TypeScript types
│   ├── hooks/           # React hooks
│   └── context/         # React context
└── package.json
```

## Troubleshooting

### Common Issues

1. **Virtual Environment Not Activating**
```bash
# If .venv activation fails, try:
deactivate  # If already in a venv
rm -rf .venv
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
```

2. **Dependencies Installation Fails**
```bash
# Clear pip cache
pip cache purge
pip install -r requirements.txt --no-cache-dir

# Clear npm cache
npm cache clean --force
npm install -g next@latest create-next-app@latest typescript@latest shadcn-ui@latest
```

3. **Port 3000 Already in Use**
```bash
# On macOS/Linux:
sudo kill -9 $(lsof -ti:3000)

# On Windows:
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

### Verification Steps

```bash
# 1. Check Python environment
python --version
pip list

# 2. Check Node.js setup
node --version
npm --version
npm list -g --depth=0

# 3. Verify project creation
cd your-project
npm run dev
```

## Development Commands

```bash
# Start development server
npm run dev

# Build project
npm run build

# Start production server
npm start

# Lint code
npm run lint

# Format code
npm run format
```

## Support

If you encounter any issues:
1. Check the installation log in the GUI
2. Verify all prerequisites are installed
3. Ensure your virtual environment is activated
4. Check Node.js and npm versions match requirements

## License

MIT License - feel free to use and modify for your needs.