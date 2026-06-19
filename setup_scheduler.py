"""
Windows Task Scheduler setup — runs the job agent every 30 minutes.
Run once as Administrator: python setup_scheduler.py

Options:
  --interval <minutes>   Default: 30
  --task-name <name>     Default: JobSearchAgent
  --delete               Remove the scheduled task
"""

import subprocess
import sys
import os
import argparse
from pathlib import Path

PYTHON_EXE   = sys.executable
SCRIPT_PATH  = str(Path(__file__).parent / "main.py")
WORKING_DIR  = str(Path(__file__).parent)
LOG_FILE     = str(Path(__file__).parent / "job_agent.log")


def create_task(task_name: str, interval_minutes: int):
    xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Job Search Agent — checks for new jobs every {interval_minutes} minutes</Description>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <Repetition>
        <Interval>PT{interval_minutes}M</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
      <StartBoundary>2026-01-01T07:00:00</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT10M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{PYTHON_EXE}</Command>
      <Arguments>"{SCRIPT_PATH}"</Arguments>
      <WorkingDirectory>{WORKING_DIR}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""

    xml_path = os.path.join(WORKING_DIR, "_task_tmp.xml")
    with open(xml_path, "w", encoding="utf-16") as f:
        f.write(xml)

    result = subprocess.run(
        ["schtasks", "/Create", "/TN", task_name, "/XML", xml_path, "/F"],
        capture_output=True, text=True
    )
    os.remove(xml_path)

    if result.returncode == 0:
        print(f"[OK] Task '{task_name}' created — runs every {interval_minutes} minutes.")
        print(f"     Log file: {LOG_FILE}")
        print(f"\nManage with:")
        print(f"  schtasks /Run    /TN {task_name}   (run now)")
        print(f"  schtasks /End    /TN {task_name}   (stop)")
        print(f"  schtasks /Delete /TN {task_name}   (remove)")
    else:
        print(f"[FAIL] Could not create task:\n{result.stderr}")
        print("Tip: run this script as Administrator.")


def delete_task(task_name: str):
    result = subprocess.run(
        ["schtasks", "/Delete", "/TN", task_name, "/F"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"[OK] Task '{task_name}' deleted.")
    else:
        print(f"[FAIL] {result.stderr.strip()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Schedule the job agent on Windows Task Scheduler")
    parser.add_argument("--interval", type=int, default=30, help="Interval in minutes (default: 30)")
    parser.add_argument("--task-name", default="JobSearchAgent", help="Task name (default: JobSearchAgent)")
    parser.add_argument("--delete", action="store_true", help="Remove the scheduled task")
    args = parser.parse_args()

    if args.delete:
        delete_task(args.task_name)
    else:
        create_task(args.task_name, args.interval)
