"""
Property-based test for Alembic migration reversibility.

Feature: gmail-expense-tracker
Property 25: Migration Reversibility

**Validates: Requirements 8.4**

For any Alembic migration, both the upgrade and downgrade functions should 
execute successfully without errors.
"""

import pytest
from hypothesis import given, strategies as st, settings
import subprocess
import os
from pathlib import Path


# Strategy for generating migration steps (how many times to upgrade/downgrade)
migration_steps_strategy = st.integers(min_value=1, max_value=3)


@pytest.mark.property
@pytest.mark.asyncio
@settings(max_examples=3, deadline=120000)  # 120 second deadline for migration operations
@given(steps=migration_steps_strategy)
async def test_migration_upgrade_downgrade_reversibility(steps):
    """
    Property 25: Migration Reversibility
    
    **Validates: Requirements 8.4**
    
    For any Alembic migration, both the upgrade and downgrade functions should 
    execute successfully without errors. This test verifies that migrations can 
    be applied and rolled back multiple times without issues.
    """
    backend_dir = Path(__file__).parent.parent
    
    # Ensure we're at the base migration state
    result = subprocess.run(
        ["alembic", "downgrade", "base"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        timeout=30
    )
    assert result.returncode == 0, f"Failed to downgrade to base: {result.stderr}"
    
    # Test multiple upgrade/downgrade cycles
    for i in range(steps):
        # Upgrade to head
        upgrade_result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=backend_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Verify upgrade succeeded
        assert upgrade_result.returncode == 0, \
            f"Migration upgrade failed on iteration {i+1}: {upgrade_result.stderr}"
        
        # Verify no error messages in output
        assert "error" not in upgrade_result.stderr.lower(), \
            f"Upgrade contained errors: {upgrade_result.stderr}"
        
        # Downgrade one step
        downgrade_result = subprocess.run(
            ["alembic", "downgrade", "-1"],
            cwd=backend_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Verify downgrade succeeded
        assert downgrade_result.returncode == 0, \
            f"Migration downgrade failed on iteration {i+1}: {downgrade_result.stderr}"
        
        # Verify no error messages in output
        assert "error" not in downgrade_result.stderr.lower(), \
            f"Downgrade contained errors: {downgrade_result.stderr}"
    
    # Restore to head state for other tests
    final_upgrade = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        timeout=30
    )
    assert final_upgrade.returncode == 0, \
        f"Failed to restore to head: {final_upgrade.stderr}"


@pytest.mark.property
@pytest.mark.asyncio
async def test_migration_downgrade_to_base_and_upgrade():
    """
    Property 25: Migration Reversibility (Complete cycle test)
    
    **Validates: Requirements 8.4**
    
    Verifies that a complete downgrade to base and upgrade to head works correctly.
    """
    backend_dir = Path(__file__).parent.parent
    
    # Downgrade to base (remove all migrations)
    downgrade_result = subprocess.run(
        ["alembic", "downgrade", "base"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    assert downgrade_result.returncode == 0, \
        f"Failed to downgrade to base: {downgrade_result.stderr}"
    assert "error" not in downgrade_result.stderr.lower(), \
        f"Downgrade to base contained errors: {downgrade_result.stderr}"
    
    # Upgrade to head (apply all migrations)
    upgrade_result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    assert upgrade_result.returncode == 0, \
        f"Failed to upgrade to head: {upgrade_result.stderr}"
    assert "error" not in upgrade_result.stderr.lower(), \
        f"Upgrade to head contained errors: {upgrade_result.stderr}"
    
    # Verify we're at head
    current_result = subprocess.run(
        ["alembic", "current"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        timeout=10
    )
    
    assert current_result.returncode == 0, \
        f"Failed to check current migration: {current_result.stderr}"
    # Should show a revision ID when at head
    assert current_result.stdout.strip() != "", \
        "Expected to be at a migration revision, but current shows empty"
