#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Repository cleanup analysis script.
Finds duplicate files and unnecessary files for cleanup.
"""

import os
import hashlib
from pathlib import Path
from collections import defaultdict
import json

def calculate_file_hash(file_path, chunk_size=8192):
    """Calculate SHA256 hash of a file."""
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except (IOError, OSError):
        return None

def is_duplicate_candidate(file_path):
    """Check if file is a candidate for duplicate analysis."""
    # Skip binary files and very large files
    if file_path.stat().st_size > 10 * 1024 * 1024:  # 10MB
        return False

    # Skip certain file types that are likely unique
    skip_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.woff', '.woff2', '.webp', '.avif'}
    if file_path.suffix.lower() in skip_extensions:
        return False

    return True

def is_unnecessary_file(file_path):
    """Check if file is unnecessary and can be removed."""
    file_name = file_path.name
    file_path_str = str(file_path)

    # Build artifacts and caches
    unnecessary_patterns = [
        '__pycache__',
        '.pytest_cache',
        '.mypy_cache',
        '.ruff_cache',
        'node_modules',
        '.next',
        '.out',
        'dist',
        'build',
        '.coverage',
        'coverage',
        '.nyc_output',
        'htmlcov',
        '.tox',
        '.nox',
        '*.egg-info',
        '.eggs',
        'pip-wheel-metadata',
        '.npm',
        '.pnpm-store',
        '.eslintcache',
        '*.tsbuildinfo',
        'npm-debug.log',
        'yarn-debug.log',
        'yarn-error.log',
        '*.log',
        '*.tmp',
        '*.temp',
        '.tmp',
        '*.orig',
        '*.map',
        '*.bak',
        '.DS_Store',
        'Thumbs.db',
        '*.swp',
        '*.swo',
        '*~',
        '.vscode',
        '.idea',
        '*.iml',
        'CMakeFiles',
        'CMakeCache.txt',
        'cmake-build-*',
        'compile_commands.json',
        '.gradle',
        'build.gradle.kts',
        'target',
        'vendor',
        '*.exe',
        '*.dll',
        '*.so',
        '*.dylib',
        '*.a',
        '*.lib',
        '*.zip',
        '*.tar.gz',
        '*.rar',
        '.local',
        '.config',
        '*.db',
        '*.sqlite',
        '*.sqlite3',
        '*.pkl',
        '*.h5',
        '*.pt',
        '*.pth',
        '*.bin',
        '*.index',
        '*.faiss',
        'checkpoints',
        'artifacts',
        'models',
        'reports',
        'bandit-report.json',
        'safety-report.json',
        'pytest-report.xml',
        'sbom.spdx.json',
        '.dockerignore',
        '*.env',
        '*.env.*',
        '!*.env.example',
        'assets_large',
        '.emergent',
        'services/adapters/memory',
        'services/adapters/models',
        'services/event_bus/storage',
        'services/adapters/templates/cache',
        'rag_index/*.bin',
        'rag_index/*.index',
        'models/*.bin',
        'models/*.safetensors'
    ]

    # Check if file matches any unnecessary pattern
    for pattern in unnecessary_patterns:
        if pattern.startswith('*'):
            if file_name.endswith(pattern[1:]):
                return True
        elif pattern.startswith('!'):
            continue  # Skip exclusion patterns
        elif pattern in file_path_str:
            return True

    # Check for specific file types that are often unnecessary
    if file_path.suffix in {'.pyc', '.pyo', '.pyd', '.pyo', '.pyc'}:
        return True

    return False

def analyze_repository(repo_path):
    """Analyze repository for duplicates and unnecessary files."""
    repo_path = Path(repo_path)

    print("Analyzing repository for duplicates and unnecessary files...")

    # Track files by hash
    hash_to_files = defaultdict(list)
    unnecessary_files = []
    total_files = 0
    total_size = 0

    # Directories to skip
    skip_dirs = {
        '.git', 'node_modules', '.venv', '__pycache__', 'assets_large',
        '.pytest_cache', '.mypy_cache', '.ruff_cache', 'dist', 'build',
        'coverage', 'htmlcov', '.tox', '.nox', '.next', '.out',
        'target', 'vendor', 'checkpoints', 'artifacts', 'models'
    }

    for file_path in repo_path.rglob('*'):
        if not file_path.is_file():
            continue

        # Skip if in skip directory
        if any(part in skip_dirs for part in file_path.parts):
            continue

        total_files += 1
        file_size = file_path.stat().st_size
        total_size += file_size

        # Check if unnecessary
        if is_unnecessary_file(file_path):
            unnecessary_files.append({
                'path': str(file_path),
                'size': file_size,
                'reason': 'matches unnecessary pattern'
            })
            continue

        # Check if candidate for duplicate analysis
        if not is_duplicate_candidate(file_path):
            continue

        # Calculate hash
        file_hash = calculate_file_hash(file_path)
        if file_hash:
            hash_to_files[file_hash].append({
                'path': str(file_path),
                'size': file_size
            })

    # Find duplicates
    duplicates = []
    for file_hash, files in hash_to_files.items():
        if len(files) > 1:
            # Sort by path length (shorter paths are often more canonical)
            files.sort(key=lambda x: len(x['path']))
            duplicates.append({
                'hash': file_hash,
                'files': files,
                'total_size': sum(f['size'] for f in files),
                'wasted_size': sum(f['size'] for f in files[1:])  # Size of duplicates
            })

    return {
        'total_files': total_files,
        'total_size': total_size,
        'duplicates': duplicates,
        'unnecessary_files': unnecessary_files,
        'duplicate_count': len(duplicates),
        'unnecessary_count': len(unnecessary_files),
        'total_wasted_size': sum(d['wasted_size'] for d in duplicates) + sum(f['size'] for f in unnecessary_files)
    }

def main():
    """Main function."""
    repo_path = Path.cwd()
    results = analyze_repository(repo_path)

    print(f"\nRepository Analysis Results:")
    print(f"Total files analyzed: {results['total_files']:,}")
    print(f"Total size: {results['total_size'] / (1024*1024):.2f} MB")
    print(f"Duplicate file groups: {results['duplicate_count']}")
    print(f"Unnecessary files: {results['unnecessary_count']}")
    print(f"Total wasted space: {results['total_wasted_size'] / (1024*1024):.2f} MB")

    # Report duplicates
    if results['duplicates']:
        print(f"\nDuplicate Files Found:")
        for i, dup in enumerate(results['duplicates'][:10]):  # Show first 10
            print(f"\n{i+1}. Hash: {dup['hash'][:12]}... ({len(dup['files'])} files, {dup['wasted_size']} bytes wasted)")
            for j, file_info in enumerate(dup['files']):
                marker = "CANONICAL" if j == 0 else "DUPLICATE"
                print(f"   {marker}: {file_info['path']} ({file_info['size']} bytes)")

        if len(results['duplicates']) > 10:
            print(f"   ... and {len(results['duplicates']) - 10} more duplicate groups")

    # Report unnecessary files
    if results['unnecessary_files']:
        print(f"\nUnnecessary Files Found:")
        for i, file_info in enumerate(results['unnecessary_files'][:20]):  # Show first 20
            print(f"{i+1:2d}. {file_info['path']} ({file_info['size']} bytes) - {file_info['reason']}")

        if len(results['unnecessary_files']) > 20:
            print(f"    ... and {len(results['unnecessary_files']) - 20} more unnecessary files")

    # Save detailed report
    report_file = repo_path / 'cleanup_report.json'
    with open(report_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nDetailed report saved to: {report_file}")

    # Generate cleanup commands
    print(f"\nCleanup Commands:")
    print("# Remove unnecessary files:")
    for file_info in results['unnecessary_files']:
        print(f"rm -f '{file_info['path']}'")

    print("\n# Remove duplicate files (keep first/canonical):")
    for dup in results['duplicates']:
        for file_info in dup['files'][1:]:  # Skip first (canonical)
            print(f"rm -f '{file_info['path']}'")

if __name__ == "__main__":
    main()
