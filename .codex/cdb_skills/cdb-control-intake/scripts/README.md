# Scripts

Automation scripts for the cdb-control-intake skill.

Scripts extend what the skill can do beyond prompt instructions.
They run via `python scripts/<name>.py` from the skill root.

## Guidelines

- Each script should have a docstring, argparse CLI, and explicit exit codes
- Use the Result dataclass pattern (see script-template.py in SkillForge assets)
- Exit 0 = success, 1 = failure, 2 = bad args, 10 = validation fail
