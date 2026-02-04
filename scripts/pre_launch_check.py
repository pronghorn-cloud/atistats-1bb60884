#!/usr/bin/env python3
"""Pre-launch checklist script for ATI Stats application.

This script performs comprehensive checks before deploying to production:
- Database connectivity and migrations
- Required environment variables
- Service health checks
- Security configuration validation

Usage:
    python -m scripts.pre_launch_check
    # or
    make pre-launch-check
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Tuple, List
from dataclasses import dataclass
from enum import Enum

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class CheckStatus(Enum):
    PASS = "✅"
    FAIL = "❌"
    WARN = "⚠️"
    SKIP = "⏭️"


@dataclass
class CheckResult:
    name: str
    status: CheckStatus
    message: str
    details: str = ""


class PreLaunchChecker:
    """Pre-launch checklist runner."""
    
    def __init__(self):
        self.results: List[CheckResult] = []
        self.is_production = os.getenv("DEBUG", "true").lower() == "false"
    
    def add_result(self, name: str, status: CheckStatus, message: str, details: str = ""):
        """Add a check result."""
        self.results.append(CheckResult(name, status, message, details))
    
    async def check_environment_variables(self) -> CheckResult:
        """Check required environment variables are set."""
        required_vars = [
            "DATABASE_URL",
            "SECRET_KEY",
        ]
        
        recommended_vars = [
            "REDIS_URL",
            "ALLOWED_ORIGINS",
        ]
        
        production_vars = [
            "SENTRY_DSN",  # Error tracking
        ]
        
        missing_required = [v for v in required_vars if not os.getenv(v)]
        missing_recommended = [v for v in recommended_vars if not os.getenv(v)]
        missing_production = [v for v in production_vars if not os.getenv(v)]
        
        if missing_required:
            return CheckResult(
                "Environment Variables",
                CheckStatus.FAIL,
                f"Missing required variables: {', '.join(missing_required)}",
            )
        
        if self.is_production and missing_production:
            return CheckResult(
                "Environment Variables",
                CheckStatus.WARN,
                f"Missing production variables: {', '.join(missing_production)}",
            )
        
        if missing_recommended:
            return CheckResult(
                "Environment Variables",
                CheckStatus.WARN,
                f"Missing recommended variables: {', '.join(missing_recommended)}",
            )
        
        return CheckResult(
            "Environment Variables",
            CheckStatus.PASS,
            "All required environment variables are set",
        )
    
    async def check_database_connection(self) -> CheckResult:
        """Check database connectivity."""
        try:
            from src.db.session import engine
            from sqlalchemy import text
            
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                result.fetchone()
            
            return CheckResult(
                "Database Connection",
                CheckStatus.PASS,
                "Successfully connected to database",
            )
        except Exception as e:
            return CheckResult(
                "Database Connection",
                CheckStatus.FAIL,
                f"Failed to connect to database: {str(e)}",
            )
    
    async def check_database_migrations(self) -> CheckResult:
        """Check if database migrations are up to date."""
        try:
            from alembic.config import Config
            from alembic.script import ScriptDirectory
            from alembic.runtime.migration import MigrationContext
            from src.db.session import engine
            
            alembic_cfg = Config("alembic.ini")
            script = ScriptDirectory.from_config(alembic_cfg)
            
            async with engine.connect() as conn:
                def get_current_rev(connection):
                    context = MigrationContext.configure(connection)
                    return context.get_current_revision()
                
                current_rev = await conn.run_sync(get_current_rev)
            
            head_rev = script.get_current_head()
            
            if current_rev == head_rev:
                return CheckResult(
                    "Database Migrations",
                    CheckStatus.PASS,
                    f"Migrations up to date (revision: {current_rev[:8] if current_rev else 'None'})",
                )
            else:
                return CheckResult(
                    "Database Migrations",
                    CheckStatus.FAIL,
                    f"Migrations pending. Current: {current_rev}, Head: {head_rev}",
                    "Run 'alembic upgrade head' to apply migrations",
                )
        except Exception as e:
            return CheckResult(
                "Database Migrations",
                CheckStatus.WARN,
                f"Could not check migrations: {str(e)}",
            )
    
    async def check_redis_connection(self) -> CheckResult:
        """Check Redis connectivity (if configured)."""
        redis_url = os.getenv("REDIS_URL")
        
        if not redis_url:
            return CheckResult(
                "Redis Connection",
                CheckStatus.SKIP,
                "Redis URL not configured",
            )
        
        try:
            import redis.asyncio as redis
            
            client = redis.from_url(redis_url)
            await client.ping()
            await client.close()
            
            return CheckResult(
                "Redis Connection",
                CheckStatus.PASS,
                "Successfully connected to Redis",
            )
        except Exception as e:
            return CheckResult(
                "Redis Connection",
                CheckStatus.WARN,
                f"Failed to connect to Redis: {str(e)}",
            )
    
    async def check_secret_key_strength(self) -> CheckResult:
        """Check if SECRET_KEY is strong enough."""
        secret_key = os.getenv("SECRET_KEY", "")
        
        if len(secret_key) < 32:
            return CheckResult(
                "Secret Key Strength",
                CheckStatus.FAIL,
                f"SECRET_KEY is too short ({len(secret_key)} chars, minimum 32)",
            )
        
        # Check for common weak keys
        weak_keys = ["secret", "password", "changeme", "development", "test"]
        if any(weak in secret_key.lower() for weak in weak_keys):
            return CheckResult(
                "Secret Key Strength",
                CheckStatus.WARN,
                "SECRET_KEY contains common weak patterns",
            )
        
        return CheckResult(
            "Secret Key Strength",
            CheckStatus.PASS,
            "SECRET_KEY appears to be strong",
        )
    
    async def check_debug_mode(self) -> CheckResult:
        """Check DEBUG mode is disabled for production."""
        debug = os.getenv("DEBUG", "true").lower()
        
        if debug == "true" and self.is_production:
            return CheckResult(
                "Debug Mode",
                CheckStatus.FAIL,
                "DEBUG mode is enabled in production!",
            )
        
        if debug == "true":
            return CheckResult(
                "Debug Mode",
                CheckStatus.WARN,
                "DEBUG mode is enabled (acceptable for non-production)",
            )
        
        return CheckResult(
            "Debug Mode",
            CheckStatus.PASS,
            "DEBUG mode is disabled",
        )
    
    async def check_cors_configuration(self) -> CheckResult:
        """Check CORS configuration."""
        allowed_origins = os.getenv("ALLOWED_ORIGINS", "[\"*\"]")
        
        if '*' in allowed_origins and self.is_production:
            return CheckResult(
                "CORS Configuration",
                CheckStatus.FAIL,
                "CORS allows all origins in production!",
            )
        
        if '*' in allowed_origins:
            return CheckResult(
                "CORS Configuration",
                CheckStatus.WARN,
                "CORS allows all origins (acceptable for development)",
            )
        
        return CheckResult(
            "CORS Configuration",
            CheckStatus.PASS,
            "CORS is properly configured",
        )
    
    async def check_application_health(self) -> CheckResult:
        """Check if the application can start."""
        try:
            from src.main import app
            from src.core.config import settings
            
            return CheckResult(
                "Application Health",
                CheckStatus.PASS,
                f"Application '{settings.APP_NAME}' loaded successfully",
            )
        except Exception as e:
            return CheckResult(
                "Application Health",
                CheckStatus.FAIL,
                f"Failed to load application: {str(e)}",
            )
    
    async def run_all_checks(self):
        """Run all pre-launch checks."""
        checks = [
            self.check_environment_variables,
            self.check_secret_key_strength,
            self.check_debug_mode,
            self.check_cors_configuration,
            self.check_application_health,
            self.check_database_connection,
            self.check_database_migrations,
            self.check_redis_connection,
        ]
        
        for check in checks:
            try:
                result = await check()
                self.results.append(result)
            except Exception as e:
                self.results.append(CheckResult(
                    check.__name__.replace("check_", "").replace("_", " ").title(),
                    CheckStatus.FAIL,
                    f"Check failed with error: {str(e)}",
                ))
    
    def print_results(self):
        """Print check results."""
        print("="*60)
        print("ATI Stats - Pre-Launch Checklist")
        print("="*60)
        print(f"Environment: {'PRODUCTION' if self.is_production else 'Development'}")
        print("-"*60)
        print()
        
        for result in self.results:
            print(f"{result.status.value} {result.name}")
            print(f"   {result.message}")
            if result.details:
                print(f"   → {result.details}")
            print()
        
        # Summary
        passed = sum(1 for r in self.results if r.status == CheckStatus.PASS)
        failed = sum(1 for r in self.results if r.status == CheckStatus.FAIL)
        warnings = sum(1 for r in self.results if r.status == CheckStatus.WARN)
        skipped = sum(1 for r in self.results if r.status == CheckStatus.SKIP)
        
        print("-"*60)
        print(f"Summary: {passed} passed, {failed} failed, {warnings} warnings, {skipped} skipped")
        print("="*60)
        
        if failed > 0:
            print("\n❌ Pre-launch checks FAILED. Please fix the issues above.")
            return False
        elif warnings > 0 and self.is_production:
            print("\n⚠️  Pre-launch checks passed with WARNINGS. Review before production deployment.")
            return True
        else:
            print("\n✅ All pre-launch checks PASSED!")
            return True


async def main():
    """Run pre-launch checks."""
    checker = PreLaunchChecker()
    await checker.run_all_checks()
    success = checker.print_results()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
