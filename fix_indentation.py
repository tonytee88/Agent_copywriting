
from pathlib import Path

file_path = Path("email_orchestrator/tools/campaign_tools.py")
lines = file_path.read_text(encoding="utf-8").splitlines()

# Target Range: 289 to 460 (1-indexed) -> 288 to 460 (0-indexed slice)
# Note: typically range end is exclusive in Python slicing
start_idx = 289 - 1
end_idx = 460  # Inclusive of line 460, so slice up to 460

new_lines = []
for i, line in enumerate(lines):
    if start_idx <= i < end_idx:
        # Check if line is empty string to avoid adding spaces to blank lines (optional but clean)
        if line.strip():
            new_lines.append("    " + line)
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

output_text = "\n".join(new_lines) + "\n" # Ensure trailing newline
file_path.write_text(output_text, encoding="utf-8")

print(f"Indented lines {start_idx+1} to {end_idx} in {file_path}")
