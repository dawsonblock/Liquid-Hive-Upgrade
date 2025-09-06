#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Targeted repository cleanup script.
Removes only actual build artifacts and generated files.
"""

import os
import shutil
from pathlib import Path

def should_remove_file(file_path):
    """Check if file should be removed based on specific patterns."""
    file_name = file_path.name
    file_path_str = str(file_path)

    # Build artifacts and generated files that are safe to remove
    remove_patterns = [
        # TypeScript build artifacts
        '*.d.ts.map',
        '*.js.map',
        'tsconfig.tsbuildinfo',

        # Vite build artifacts
        'vite.config.d.ts',
        'vite.config.d.ts.map',
        'vite.config.js',
        'vite.config.js.map',

        # Jest config (generated)
        'jest.config.cjs',

        # ESLint config (generated)
        'eslint.config.js',

        # Build reports
        'build_verification_report.json',

        # IDE settings
        '.vscode/settings.json',

        # Test artifacts
        '*.test.d.ts.map',
        '*.test.js.map',

        # Service mocks (generated)
        'frontend/src/test/__mocks__/',

        # Memory graph (generated)
        'services/adapters/memory_graph.py',

        # Dataset build (generated)
        'src/hivemind/training/dataset_build.py',
    ]

    # Check patterns
    for pattern in remove_patterns:
        if pattern.endswith('*'):
            if file_name.startswith(pattern[:-1]):
                return True
        elif pattern.endswith('/'):
            if file_path_str.endswith(pattern[:-1]):
                return True
        elif pattern in file_path_str:
            return True

    return False

def cleanup_repository():
    """Clean up the repository by removing unnecessary files."""
    repo_path = Path.cwd()
    removed_files = []
    total_size_removed = 0

    print("Starting targeted cleanup...")

    # Find and remove files
    for file_path in repo_path.rglob('*'):
        if not file_path.is_file():
            continue

        if should_remove_file(file_path):
            try:
                file_size = file_path.stat().st_size
                print(f"Removing: {file_path} ({file_size} bytes)")
                file_path.unlink()
                removed_files.append(str(file_path))
                total_size_removed += file_size
            except Exception as e:
                print(f"Error removing {file_path}: {e}")

    # Remove duplicate docker-compose file (keep .yaml, remove .yml symlink)
    docker_compose_yml = repo_path / 'docker-compose.yml'
    if docker_compose_yml.exists() and docker_compose_yml.is_symlink():
        try:
            print(f"Removing symlink: {docker_compose_yml}")
            docker_compose_yml.unlink()
            removed_files.append(str(docker_compose_yml))
        except Exception as e:
            print(f"Error removing symlink {docker_compose_yml}: {e}")

    print(f"\nCleanup completed!")
    print(f"Files removed: {len(removed_files)}")
    print(f"Total size removed: {total_size_removed / (1024*1024):.2f} MB")

    # Save cleanup log
    log_file = repo_path / 'cleanup_log.txt'
    with open(log_file, 'w') as f:
        f.write("Repository Cleanup Log\n")
        f.write("====================\n\n")
        f.write(f"Files removed: {len(removed_files)}\n")
        f.write(f"Total size removed: {total_size_removed / (1024*1024):.2f} MB\n\n")
        f.write("Removed files:\n")
        for file_path in removed_files:
            f.write(f"  - {file_path}\n")

    print(f"Cleanup log saved to: {log_file}")

if __name__ == "__main__":
    cleanup_repository()
