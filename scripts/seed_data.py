#!/usr/bin/env python3
"""Database seed script for initial data population.

This script populates the database with initial sample data for
public bodies and ATI requests. Used for development, testing,
and initial production setup.

Usage:
    python -m scripts.seed_data
    # or
    make db-seed
"""

import asyncio
import sys
from datetime import datetime, timedelta
import random
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import async_session_maker, engine
from src.db.base import Base
from src.models.public_body import PublicBody
from src.models.ati_request import ATIRequest, RequestStatus, RequestType, RequestOutcome


# Sample Public Bodies Data
PUBLIC_BODIES = [
    {
        "name": "Department of Justice",
        "abbreviation": "DOJ",
        "description": "Federal department responsible for the administration of justice.",
        "contact_email": "ati@justice.gc.ca",
        "website": "https://www.justice.gc.ca",
        "is_active": True,
    },
    {
        "name": "Department of Health",
        "abbreviation": "HC",
        "description": "Federal department responsible for national health policy.",
        "contact_email": "ati@hc-sc.gc.ca",
        "website": "https://www.canada.ca/en/health-canada.html",
        "is_active": True,
    },
    {
        "name": "Department of Finance",
        "abbreviation": "FIN",
        "description": "Federal department responsible for economic policy and government finances.",
        "contact_email": "ati@fin.gc.ca",
        "website": "https://www.canada.ca/en/department-finance.html",
        "is_active": True,
    },
    {
        "name": "Canada Revenue Agency",
        "abbreviation": "CRA",
        "description": "Agency responsible for tax administration.",
        "contact_email": "ati@cra-arc.gc.ca",
        "website": "https://www.canada.ca/en/revenue-agency.html",
        "is_active": True,
    },
    {
        "name": "Department of National Defence",
        "abbreviation": "DND",
        "description": "Federal department responsible for national defence and the Canadian Armed Forces.",
        "contact_email": "ati@forces.gc.ca",
        "website": "https://www.canada.ca/en/department-national-defence.html",
        "is_active": True,
    },
    {
        "name": "Transport Canada",
        "abbreviation": "TC",
        "description": "Federal department responsible for transportation policies and programs.",
        "contact_email": "ati@tc.gc.ca",
        "website": "https://tc.canada.ca",
        "is_active": True,
    },
    {
        "name": "Environment and Climate Change Canada",
        "abbreviation": "ECCC",
        "description": "Federal department responsible for environmental protection.",
        "contact_email": "ati@ec.gc.ca",
        "website": "https://www.canada.ca/en/environment-climate-change.html",
        "is_active": True,
    },
    {
        "name": "Immigration, Refugees and Citizenship Canada",
        "abbreviation": "IRCC",
        "description": "Federal department responsible for immigration and citizenship.",
        "contact_email": "ati@cic.gc.ca",
        "website": "https://www.canada.ca/en/immigration-refugees-citizenship.html",
        "is_active": True,
    },
]

# Request types and their relative frequencies
REQUEST_TYPES = [
    (RequestType.PERSONAL, 0.3),
    (RequestType.NON_PERSONAL, 0.5),
    (RequestType.MIXED, 0.2),
]

# Status and outcome distributions
STATUS_DISTRIBUTION = [
    (RequestStatus.COMPLETED, 0.7),
    (RequestStatus.IN_PROGRESS, 0.15),
    (RequestStatus.PENDING, 0.1),
    (RequestStatus.ON_HOLD, 0.03),
    (RequestStatus.WITHDRAWN, 0.02),
]

OUTCOME_DISTRIBUTION = [
    (RequestOutcome.FULL_DISCLOSURE, 0.25),
    (RequestOutcome.PARTIAL_DISCLOSURE, 0.45),
    (RequestOutcome.NO_RECORDS, 0.15),
    (RequestOutcome.EXEMPTION, 0.1),
    (RequestOutcome.ABANDONED, 0.03),
    (RequestOutcome.TRANSFERRED, 0.02),
]


def weighted_choice(choices: list[tuple]) -> any:
    """Make a weighted random choice."""
    items, weights = zip(*choices)
    return random.choices(items, weights=weights, k=1)[0]


def generate_request_number(public_body_abbr: str, year: int, sequence: int) -> str:
    """Generate a realistic request number."""
    return f"{public_body_abbr}-{year}-{sequence:05d}"


def generate_ati_requests(public_body: PublicBody, count: int, start_date: datetime) -> list[dict]:
    """Generate sample ATI requests for a public body."""
    requests = []
    
    for i in range(count):
        # Random date within the past 2 years
        days_ago = random.randint(0, 730)
        submission_date = start_date - timedelta(days=days_ago)
        year = submission_date.year
        
        # Generate request details
        request_type = weighted_choice(REQUEST_TYPES)
        status = weighted_choice(STATUS_DISTRIBUTION)
        
        # Calculate dates based on status
        due_date = submission_date + timedelta(days=30)
        
        if status == RequestStatus.COMPLETED:
            # Completed requests have a completion date
            days_to_complete = random.randint(5, 60)
            completion_date = submission_date + timedelta(days=days_to_complete)
            outcome = weighted_choice(OUTCOME_DISTRIBUTION)
        else:
            completion_date = None
            outcome = None
        
        # Determine if request is overdue
        is_extended = random.random() < 0.2
        if is_extended:
            extension_days = random.choice([30, 60, 90])
            due_date += timedelta(days=extension_days)
        
        requests.append({
            "request_number": generate_request_number(public_body.abbreviation, year, i + 1),
            "public_body_id": public_body.id,
            "request_type": request_type,
            "status": status,
            "outcome": outcome,
            "submission_date": submission_date.date(),
            "due_date": due_date.date(),
            "completion_date": completion_date.date() if completion_date else None,
            "is_extended": is_extended,
            "extension_days": extension_days if is_extended else None,
            "pages_processed": random.randint(10, 500) if status == RequestStatus.COMPLETED else None,
            "pages_disclosed": random.randint(5, 400) if status == RequestStatus.COMPLETED else None,
            "description": f"Sample ATI request {i + 1} for {public_body.name}",
        })
    
    return requests


async def seed_database():
    """Main function to seed the database with sample data."""
    print("="*60)
    print("ATI Stats - Database Seeding Script")
    print("="*60)
    
    async with async_session_maker() as session:
        # Check if data already exists
        from sqlalchemy import select, func
        
        existing_bodies = await session.execute(
            select(func.count(PublicBody.id))
        )
        count = existing_bodies.scalar()
        
        if count > 0:
            print(f"\n⚠️  Database already contains {count} public bodies.")
            response = input("Do you want to continue and add more data? (y/N): ")
            if response.lower() != 'y':
                print("Seeding cancelled.")
                return
        
        print("\n📥 Seeding public bodies...")
        public_bodies = []
        
        for pb_data in PUBLIC_BODIES:
            # Check if already exists
            existing = await session.execute(
                select(PublicBody).where(PublicBody.abbreviation == pb_data["abbreviation"])
            )
            if existing.scalar_one_or_none():
                print(f"  ⏭️  {pb_data['name']} already exists, skipping...")
                continue
            
            pb = PublicBody(**pb_data)
            session.add(pb)
            public_bodies.append(pb)
            print(f"  ✅ Created: {pb_data['name']} ({pb_data['abbreviation']})")
        
        await session.flush()  # Get IDs assigned
        
        # Fetch all public bodies for request generation
        all_bodies_result = await session.execute(select(PublicBody))
        all_bodies = all_bodies_result.scalars().all()
        
        print(f"\n📥 Generating ATI requests...")
        total_requests = 0
        start_date = datetime.now()
        
        for pb in all_bodies:
            # Generate varying number of requests per body
            request_count = random.randint(50, 200)
            requests_data = generate_ati_requests(pb, request_count, start_date)
            
            for req_data in requests_data:
                req = ATIRequest(**req_data)
                session.add(req)
            
            total_requests += request_count
            print(f"  ✅ Generated {request_count} requests for {pb.name}")
        
        await session.commit()
        
        print("\n" + "="*60)
        print("✅ Database seeding complete!")
        print(f"   - Public Bodies: {len(PUBLIC_BODIES)}")
        print(f"   - ATI Requests: {total_requests}")
        print("="*60)


async def reset_and_seed():
    """Reset database and seed fresh data."""
    print("⚠️  This will drop all tables and recreate them!")
    response = input("Are you sure? (type 'yes' to confirm): ")
    
    if response != 'yes':
        print("Operation cancelled.")
        return
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Database reset complete.")
    await seed_database()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed the ATI Stats database")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset database before seeding (DESTRUCTIVE)"
    )
    args = parser.parse_args()
    
    if args.reset:
        asyncio.run(reset_and_seed())
    else:
        asyncio.run(seed_database())
