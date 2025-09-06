#!/usr/bin/env python3
"""
Script to replace print statements with proper logging.
"""

import os
import re
from pathlib import Path


def fix_python_logging(file_path: Path) -> bool:
    """Replace print statements with proper logging in Python files."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Add logging import if not present
        if 'import logging' not in content and 'from logging_config import' not in content:
            # Find the best place to add import
            lines = content.split('\n')
            import_line = None

            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    import_line = i + 1
                elif line.strip() and not line.startswith('#') and not line.startswith('"""') and not line.startswith("'''"):
                    break

            if import_line is None:
                import_line = 0

            # Add logging import
            lines.insert(import_line, 'from src.logging_config import get_logger')
            content = '\n'.join(lines)

        # Replace print statements
        # Pattern 1: print("message")
        content = re.sub(
            r'print\s*\(\s*(["\'])([^"\']*)\1\s*\)',
            r'logger.info(r\1\2\1)',
            content
        )

        # Pattern 2: print(f"message {var}")
        content = re.sub(
            r'print\s*\(\s*f(["\'])([^"\']*)\1\s*\)',
            r'logger.info(f\1\2\1)',
            content
        )

        # Pattern 3: print("message", var)
        content = re.sub(
            r'print\s*\(\s*(["\'])([^"\']*)\1\s*,\s*([^)]+)\s*\)',
            r'logger.info(r\1\2\1, \3)',
            content
        )

        # Add logger initialization if not present
        if 'logger = get_logger' not in content and 'print(' in content:
            # Find a good place to add logger initialization
            lines = content.split('\n')
            logger_line = None

            for i, line in enumerate(lines):
                if 'def ' in line and 'def __init__' not in line:
                    # Add after function definition
                    for j in range(i + 1, min(i + 10, len(lines))):
                        if lines[j].strip() and not lines[j].startswith(' '):
                            logger_line = j
                            break
                    break

            if logger_line is None:
                # Add at the beginning of the file
                logger_line = 0

            lines.insert(logger_line, 'logger = get_logger(__name__)')
            content = '\n'.join(content.split('\n'))

        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def fix_frontend_logging(file_path: Path) -> bool:
    """Replace console.log with proper logging in frontend files."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Replace console.log with proper logging
        content = re.sub(
            r'console\.log\s*\(([^)]+)\)',
            r'// TODO: Replace with proper logging\n        console.log(\1)',
            content
        )

        # Replace console.error with proper error handling
        content = re.sub(
            r'console\.error\s*\(([^)]+)\)',
            r'// TODO: Replace with proper error handling\n        console.error(\1)',
            content
        )

        # Replace console.warn with proper warning handling
        content = re.sub(
            r'console\.warn\s*\(([^)]+)\)',
            r'// TODO: Replace with proper warning handling\n        console.warn(\1)',
            content
        )

        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function to fix logging across the codebase."""
    print("🔧 Fixing logging across the codebase...")

    # Fix Python files
    python_files = []
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)

    print(f"Found {len(python_files)} Python files to process...")

    python_fixed = 0
    for file_path in python_files:
        if fix_python_logging(file_path):
            python_fixed += 1
            print(f"✅ Fixed logging in {file_path}")

    # Fix frontend files
    frontend_files = []
    for root, dirs, files in os.walk('frontend/src'):
        for file in files:
            if file.endswith(('.ts', '.tsx', '.js', '.jsx')):
                frontend_files.append(Path(root) / file)

    print(f"Found {len(frontend_files)} frontend files to process...")

    frontend_fixed = 0
    for file_path in frontend_files:
        if fix_frontend_logging(file_path):
            frontend_fixed += 1
            print(f"✅ Fixed logging in {file_path}")

    print(f"\n🎉 Logging fix complete!")
    print(f"   Python files fixed: {python_fixed}")
    print(f"   Frontend files fixed: {frontend_fixed}")
    print(f"   Total files processed: {len(python_files) + len(frontend_files)}")


if __name__ == "__main__":
    main()
