from pathlib import Path

text = Path("elmetron/config.py").read_text(encoding="utf-8")
needle = "    scheduled_commands: list[ScheduledCommandConfig]"
start = text.index(needle)
end_marker = "        }\n\n\n@dataclass"
end = text.index(end_marker, start) + len("        }\n")
print(text[start:end])
