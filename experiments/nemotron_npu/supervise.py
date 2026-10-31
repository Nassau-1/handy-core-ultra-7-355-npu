"""Bound native compiler lifetime and collect process CPU/memory evidence."""
import argparse
import json
import subprocess
import time
from pathlib import Path

import psutil


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=300)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command or args.seconds <= 0:
        parser.error('A command and positive time budget are required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    peak_memory = cpu_seconds = 0
    reason = 'completed'
    with args.output.with_suffix('.stdout.log').open('wb') as stdout, args.output.with_suffix('.stderr.log').open('wb') as stderr:
        child = subprocess.Popen(command, stdout=stdout, stderr=stderr)
        process = psutil.Process(child.pid)
        try:
            if hasattr(psutil, 'BELOW_NORMAL_PRIORITY_CLASS'):
                process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            while child.poll() is None:
                tree = [process, *process.children(recursive=True)]
                memory = cpu = 0
                for member in tree:
                    try:
                        memory += member.memory_info().rss
                        usage = member.cpu_times()
                        cpu += usage.user + usage.system
                    except psutil.NoSuchProcess:
                        pass
                peak_memory = max(memory, peak_memory)
                cpu_seconds = max(cpu, cpu_seconds)
                if time.perf_counter()-started >= args.seconds:
                    reason = 'timeout'
                    break
                time.sleep(0.5)
        except KeyboardInterrupt:
            reason = 'cancelled'
        finally:
            if child.poll() is None:
                # Kill this experiment's descendants only, including venv launchers.
                for member in reversed([process, *process.children(recursive=True)]):
                    try:
                        member.kill()
                    except psutil.NoSuchProcess:
                        pass
            child.wait()
    result = {'reason': reason, 'exit_code': child.returncode,
              'wall_seconds': time.perf_counter()-started,
              'sampled_cpu_seconds': cpu_seconds, 'peak_tree_rss_bytes': peak_memory}
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result), flush=True)
    if reason != 'completed' or child.returncode:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
