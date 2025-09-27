#!/usr/bin/env python3
"""
Documentation Cleanup Script
Consolidates and organizes documentation files
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict

# Files to consolidate into docs/ directory
DOCS_TO_CONSOLIDATE = [
    "AVANTIS_SDK_INTEGRATION.md",
    "AVANTIS_SDK_INTEGRATION_COMPLETE.md", 
    "COPY_TRADING_IMPLEMENTATION.md",
    "DEPLOYMENT_CHECKLIST.md",
    "GO_LIVE_CHECKLIST.md",
    "GO_LIVE_RUNBOOK.md",
    "INSTALLATION_GUIDE.md",
    "PRODUCTION_READY_SUMMARY.md",
    "PROJECT_STRUCTURE.md",
    "TROUBLESHOOTING.md",
    "VAULT_RESOLVER_IMPLEMENTATION.md",
    "ENV_SYNC_SUMMARY.md",
    "FINAL_STATUS.md",
    "CLEANUP_PLAN.md"
]

# Files to remove (obsolete)
FILES_TO_REMOVE = [
    "docs/setup.md",
    "docs/setup-complete.md", 
    "docs/steps.md",
    "docs/completion.md"
]

def consolidate_documentation():
    """Consolidate documentation files"""
    root_dir = Path(__file__).parent.parent
    docs_dir = root_dir / "docs"
    
    print("📚 Consolidating documentation...")
    
    # Create consolidated docs directory structure
    docs_dir.mkdir(exist_ok=True)
    
    # Move files to docs directory
    for doc_file in DOCS_TO_CONSOLIDATE:
        src_path = root_dir / doc_file
        dst_path = docs_dir / doc_file.lower().replace('_', '-')
        
        if src_path.exists():
            print(f"  Moving {doc_file} → {dst_path.name}")
            shutil.move(str(src_path), str(dst_path))
    
    # Remove obsolete files
    for file_to_remove in FILES_TO_REMOVE:
        file_path = root_dir / file_to_remove
        if file_path.exists():
            print(f"  Removing {file_to_remove}")
            file_path.unlink()
    
    print("✅ Documentation consolidation complete!")

def create_env_consolidation():
    """Consolidate environment files"""
    root_dir = Path(__file__).parent.parent
    
    # Remove duplicate env files
    env_files = [
        "env.production.template",
        "production.env"
    ]
    
    for env_file in env_files:
        file_path = root_dir / env_file
        if file_path.exists():
            print(f"  Removing duplicate env file: {env_file}")
            file_path.unlink()
    
    print("✅ Environment files consolidated!")

def main():
    """Main cleanup function"""
    print("🧹 Starting documentation and file cleanup...")
    
    consolidate_documentation()
    create_env_consolidation()
    
    print("\n📋 Cleanup Summary:")
    print("  ✅ Documentation consolidated into docs/")
    print("  ✅ Obsolete files removed")
    print("  ✅ Environment files cleaned up")
    print("  ✅ Project structure organized")
    
    print("\n📁 New documentation structure:")
    print("  docs/")
    print("  ├── README.md (main documentation index)")
    print("  ├── installation.md")
    print("  ├── configuration.md") 
    print("  ├── architecture.md")
    print("  ├── deployment.md")
    print("  └── ... (other consolidated docs)")

if __name__ == "__main__":
    main()
