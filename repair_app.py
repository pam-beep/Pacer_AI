import os

file_path = 'app.py'
with open(file_path, 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    # Add import if missing
    if "from persistence import" in line:
        new_lines.append(line)
        if "from styles import GLOBAL_STYLES" not in "".join(lines):
            new_lines.append("from styles import GLOBAL_STYLES\n")
        continue

    # Detect start of broken block
    if line.strip() == "<style>":
        new_lines.append("st.markdown(GLOBAL_STYLES, unsafe_allow_html=True)\n")
        skip = True
        continue
    
    # Detect end of broken block
    if skip and '""", unsafe_allow_html=True)' in line:
        skip = False
        continue

    if not skip:
        new_lines.append(line)

with open(file_path, 'w') as f:
    f.writelines(new_lines)

print("Fixed app.py")
