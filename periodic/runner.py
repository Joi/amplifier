#!/usr/bin/env python3
"""
Periodic Job Runner - Runs scheduled scripts and logs results.

Can be triggered by:
1. launchd (automatic, background)
2. Manual invocation
3. Weekly review recipe

Usage:
    python runner.py run              # Run all due jobs
    python runner.py run kimono-sync  # Run specific job
    python runner.py status           # Show job status
    python runner.py list             # List all jobs
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yaml

JOBS_FILE = Path(__file__).parent / "jobs.yaml"
LOG_DIR = Path(__file__).parent / "logs"
VENV_PYTHON = Path.home() / "amplifier" / ".venv" / "bin" / "python"


def load_jobs() -> dict:
    """Load jobs configuration."""
    with open(JOBS_FILE) as f:
        return yaml.safe_load(f)


def save_jobs(data: dict):
    """Save jobs configuration."""
    with open(JOBS_FILE, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def is_due(job: dict) -> bool:
    """Check if job is due to run."""
    last_run = job.get('last_run')
    if not last_run:
        return True
    
    schedule = job.get('schedule', 'monthly')
    last_dt = datetime.fromisoformat(last_run)
    now = datetime.now()
    
    if schedule == 'daily':
        return (now - last_dt) >= timedelta(days=1)
    elif schedule == 'weekly':
        return (now - last_dt) >= timedelta(weeks=1)
    elif schedule == 'monthly':
        return (now - last_dt) >= timedelta(days=28)
    elif schedule == 'quarterly':
        return (now - last_dt) >= timedelta(days=90)
    
    return False


def run_job(name: str, job: dict, force: bool = False) -> dict:
    """Run a single job."""
    if not force and not is_due(job):
        return {'status': 'skipped', 'reason': 'not due'}
    
    script = os.path.expanduser(job['script'])
    
    # Ensure log directory exists
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    try:
        # Run script with venv python
        result = subprocess.run(
            [str(VENV_PYTHON), *script.split()],
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout
        )
        
        # Log output
        with open(log_file, 'w') as f:
            f.write(f"Job: {name}\n")
            f.write(f"Script: {script}\n")
            f.write(f"Time: {datetime.now().isoformat()}\n")
            f.write(f"Exit code: {result.returncode}\n")
            f.write(f"\n--- STDOUT ---\n{result.stdout}\n")
            if result.stderr:
                f.write(f"\n--- STDERR ---\n{result.stderr}\n")
        
        return {
            'status': 'success' if result.returncode == 0 else 'failed',
            'exit_code': result.returncode,
            'log': str(log_file),
            'output': result.stdout[:500]  # First 500 chars
        }
    
    except subprocess.TimeoutExpired:
        return {'status': 'timeout', 'log': str(log_file)}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_run(args):
    """Run jobs."""
    data = load_jobs()
    jobs = data.get('jobs', {})
    
    if args.job:
        # Run specific job
        if args.job not in jobs:
            print(f"Unknown job: {args.job}")
            sys.exit(1)
        to_run = {args.job: jobs[args.job]}
    else:
        # Run all due jobs
        to_run = jobs
    
    for name, job in to_run.items():
        print(f"Running {name}...", end=' ')
        result = run_job(name, job, force=args.force)
        
        if result['status'] == 'success':
            # Update last_run
            data['jobs'][name]['last_run'] = datetime.now().isoformat()
            save_jobs(data)
            print(f"✓ {result.get('output', '')[:50]}")
        elif result['status'] == 'skipped':
            print(f"⏭ skipped ({result['reason']})")
        else:
            print(f"✗ {result['status']}: {result.get('error', result.get('exit_code', ''))}")


def cmd_status(args):
    """Show job status."""
    data = load_jobs()
    jobs = data.get('jobs', {})
    
    print(f"{'Job':<20} {'Schedule':<10} {'Last Run':<20} {'Status'}")
    print("-" * 65)
    
    for name, job in jobs.items():
        last_run = job.get('last_run')
        if last_run:
            last_run_str = datetime.fromisoformat(last_run).strftime('%Y-%m-%d %H:%M')
        else:
            last_run_str = 'never'
        
        due = "DUE" if is_due(job) else "ok"
        print(f"{name:<20} {job.get('schedule', 'monthly'):<10} {last_run_str:<20} {due}")


def cmd_list(args):
    """List all jobs."""
    data = load_jobs()
    jobs = data.get('jobs', {})
    
    for name, job in jobs.items():
        print(f"\n{name}:")
        print(f"  Description: {job.get('description', 'N/A')}")
        print(f"  Script: {job.get('script')}")
        print(f"  Schedule: {job.get('schedule', 'monthly')}")


def main():
    parser = argparse.ArgumentParser(description="Periodic job runner")
    subparsers = parser.add_subparsers(dest='command')
    
    # run
    run_parser = subparsers.add_parser('run', help='Run jobs')
    run_parser.add_argument('job', nargs='?', help='Specific job to run')
    run_parser.add_argument('--force', action='store_true', help='Run even if not due')
    
    # status
    subparsers.add_parser('status', help='Show job status')
    
    # list
    subparsers.add_parser('list', help='List all jobs')
    
    args = parser.parse_args()
    
    if args.command == 'run':
        cmd_run(args)
    elif args.command == 'status':
        cmd_status(args)
    elif args.command == 'list':
        cmd_list(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
