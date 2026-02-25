#!/usr/bin/env python3
"""Fix dashboard.py to only serve React build"""

with open('/root/trading-bot/dashboard.py', 'r') as f:
    lines = f.readlines()

# Find and modify the index() function
output = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Replace index() function
    if '@app.route("/")' in line and i+1 < len(lines) and 'def index()' in lines[i+1]:
        output.append('@app.route("/")\n')
        output.append('def index():\n')
        output.append('    """Serve React dashboard"""\n')
        output.append('    return send_from_directory(REACT_BUILD_DIR, \'index.html\')\n')
        # Skip old lines until next route
        i += 1
        while i < len(lines) and not lines[i].strip().startswith('@app.route'):
            i += 1
        continue
    
    # Replace serve_react_static function
    if "@app.route('/<path:filename>')" in line:
        output.append("@app.route('/<path:filename>')\n")
        output.append("def serve_react_static(filename):\n")
        output.append("    \"\"\"Serve React static files\"\"\"\n")
        output.append("    return send_from_directory(REACT_BUILD_DIR, filename)\n")
        # Skip old lines
        i += 1
        while i < len(lines) and not lines[i].strip().startswith('@app.route'):
            i += 1
        continue
    
    output.append(line)
    i += 1

with open('/root/trading-bot/dashboard.py', 'w') as f:
    f.writelines(output)

print("dashboard.py fixed")
