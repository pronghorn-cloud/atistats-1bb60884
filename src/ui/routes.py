"""UI routes for the web interface."""

from datetime import date, timedelta
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select, and_, or_, extract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.session import get_db
from src.models.ati_request import ATIRequest, RequestStatus, RequestOutcome
from src.models.public_body import PublicBody

ui_router = APIRouter(tags=["UI"])
templates = Jinja2Templates(directory="src/templates")


# Helper function to calculate stats for a public body
async def get_body_stats(db: AsyncSession, body_id: UUID) -> dict:
    """Calculate statistics for a specific public body."""
    # Total requests
    total_result = await db.execute(
        select(func.count(ATIRequest.id)).where(ATIRequest.public_body_id == body_id)
    )
    total_requests = total_result.scalar() or 0
    
    # Completed count
    completed_result = await db.execute(
        select(func.count(ATIRequest.id)).where(
            and_(ATIRequest.public_body_id == body_id, ATIRequest.status == RequestStatus.completed)
        )
    )
    completed_count = completed_result.scalar() or 0
    
    # Average response time
    avg_result = await db.execute(
        select(
            func.avg(
                func.extract('epoch', ATIRequest.completion_date) - 
                func.extract('epoch', ATIRequest.submission_date)
            ) / 86400
        ).where(
            and_(ATIRequest.public_body_id == body_id, ATIRequest.completion_date.isnot(None))
        )
    )
    avg_response_days = avg_result.scalar() or 0
    
    # On-time compliance rate (completed within due date)
    on_time_result = await db.execute(
        select(func.count(ATIRequest.id)).where(
            and_(
                ATIRequest.public_body_id == body_id,
                ATIRequest.completion_date.isnot(None),
                ATIRequest.completion_date <= ATIRequest.due_date
            )
        )
    )
    on_time_count = on_time_result.scalar() or 0
    compliance_rate = (on_time_count / completed_count * 100) if completed_count > 0 else 0
    
    # Full disclosure rate
    full_disclosure_result = await db.execute(
        select(func.count(ATIRequest.id)).where(
            and_(
                ATIRequest.public_body_id == body_id,
                ATIRequest.outcome == RequestOutcome.full_disclosure
            )
        )
    )
    full_disclosure_count = full_disclosure_result.scalar() or 0
    full_disclosure_rate = (full_disclosure_count / completed_count * 100) if completed_count > 0 else 0
    
    return {
        'total_requests': total_requests,
        'completed_count': completed_count,
        'avg_response_days': avg_response_days,
        'compliance_rate': compliance_rate,
        'full_disclosure_rate': full_disclosure_rate
    }


async def get_year_stats(db: AsyncSession, year: int, body_id: Optional[UUID] = None) -> dict:
    """Calculate statistics for a specific year."""
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    
    base_filter = and_(
        ATIRequest.submission_date >= start_date,
        ATIRequest.submission_date <= end_date
    )
    if body_id:
        base_filter = and_(base_filter, ATIRequest.public_body_id == body_id)
    
    # Total requests
    total_result = await db.execute(
        select(func.count(ATIRequest.id)).where(base_filter)
    )
    total_requests = total_result.scalar() or 0
    
    # Completed
    completed_filter = and_(base_filter, ATIRequest.status == RequestStatus.completed)
    completed_result = await db.execute(
        select(func.count(ATIRequest.id)).where(completed_filter)
    )
    completed_count = completed_result.scalar() or 0
    
    # Avg response time
    avg_filter = and_(base_filter, ATIRequest.completion_date.isnot(None))
    avg_result = await db.execute(
        select(
            func.avg(
                func.extract('epoch', ATIRequest.completion_date) - 
                func.extract('epoch', ATIRequest.submission_date)
            ) / 86400
        ).where(avg_filter)
    )
    avg_response_days = avg_result.scalar() or 0
    
    # Compliance rate
    on_time_filter = and_(
        base_filter,
        ATIRequest.completion_date.isnot(None),
        ATIRequest.completion_date <= ATIRequest.due_date
    )
    on_time_result = await db.execute(
        select(func.count(ATIRequest.id)).where(on_time_filter)
    )
    on_time_count = on_time_result.scalar() or 0
    compliance_rate = (on_time_count / completed_count * 100) if completed_count > 0 else 0
    
    return {
        'total_requests': total_requests,
        'completed_count': completed_count,
        'avg_response_days': avg_response_days or 0,
        'compliance_rate': compliance_rate
    }


@ui_router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    """Render the main dashboard with overview statistics."""
    
    # Get total counts
    total_requests_result = await db.execute(select(func.count(ATIRequest.id)))
    total_requests = total_requests_result.scalar() or 0
    
    total_bodies_result = await db.execute(select(func.count(PublicBody.id)))
    total_public_bodies = total_bodies_result.scalar() or 0
    
    # Get overdue count (requests past due_date that aren't completed)
    today = date.today()
    overdue_result = await db.execute(
        select(func.count(ATIRequest.id)).where(
            and_(
                ATIRequest.due_date < today,
                ATIRequest.status.notin_([RequestStatus.completed, RequestStatus.abandoned, RequestStatus.transferred])
            )
        )
    )
    overdue_count = overdue_result.scalar() or 0
    
    # Calculate average response time for completed requests
    avg_response_result = await db.execute(
        select(
            func.avg(
                func.extract('epoch', ATIRequest.completion_date) - 
                func.extract('epoch', ATIRequest.submission_date)
            ) / 86400  # Convert seconds to days
        ).where(ATIRequest.completion_date.isnot(None))
    )
    avg_response_days = avg_response_result.scalar() or 0
    
    # Get status distribution for chart
    status_result = await db.execute(
        select(ATIRequest.status, func.count(ATIRequest.id))
        .group_by(ATIRequest.status)
    )
    status_counts = {str(row[0].value): row[1] for row in status_result.fetchall()}
    status_labels = list(status_counts.keys())
    status_data = list(status_counts.values())
    
    # Get outcome distribution for chart
    outcome_result = await db.execute(
        select(ATIRequest.outcome, func.count(ATIRequest.id))
        .where(ATIRequest.outcome.isnot(None))
        .group_by(ATIRequest.outcome)
    )
    outcome_counts = {str(row[0].value): row[1] for row in outcome_result.fetchall()}
    outcome_labels = [label.replace('_', ' ').title() for label in outcome_counts.keys()]
    outcome_data = list(outcome_counts.values())
    
    # Get monthly trends (last 12 months)
    twelve_months_ago = today - timedelta(days=365)
    monthly_result = await db.execute(
        select(
            func.date_trunc('month', ATIRequest.submission_date).label('month'),
            func.count(ATIRequest.id)
        )
        .where(ATIRequest.submission_date >= twelve_months_ago)
        .group_by('month')
        .order_by('month')
    )
    monthly_data = monthly_result.fetchall()
    month_labels = [row[0].strftime('%b %Y') if row[0] else '' for row in monthly_data]
    month_received_data = [row[1] for row in monthly_data]
    
    # Get completed by month
    completed_monthly_result = await db.execute(
        select(
            func.date_trunc('month', ATIRequest.completion_date).label('month'),
            func.count(ATIRequest.id)
        )
        .where(ATIRequest.completion_date >= twelve_months_ago)
        .group_by('month')
        .order_by('month')
    )
    completed_monthly = {row[0]: row[1] for row in completed_monthly_result.fetchall() if row[0]}
    month_completed_data = [completed_monthly.get(row[0], 0) for row in monthly_data]
    
    # Get recent requests
    recent_result = await db.execute(
        select(ATIRequest, PublicBody.name.label('public_body_name'))
        .outerjoin(PublicBody, ATIRequest.public_body_id == PublicBody.id)
        .order_by(ATIRequest.created_at.desc())
        .limit(5)
    )
    recent_requests = []
    for row in recent_result.fetchall():
        req = row[0]
        recent_requests.append({
            'id': str(req.id),
            'request_number': req.request_number,
            'status': req.status.value if req.status else 'unknown',
            'public_body_name': row.public_body_name,
            'is_deemed_refusal': req.is_deemed_refusal
        })
    
    # Get top public bodies by request volume
    top_bodies_result = await db.execute(
        select(PublicBody, func.count(ATIRequest.id).label('request_count'))
        .outerjoin(ATIRequest, PublicBody.id == ATIRequest.public_body_id)
        .group_by(PublicBody.id)
        .order_by(func.count(ATIRequest.id).desc())
        .limit(5)
    )
    top_public_bodies = [
        {
            'id': str(row[0].id),
            'name': row[0].name,
            'abbreviation': row[0].abbreviation,
            'request_count': row[1]
        }
        for row in top_bodies_result.fetchall()
    ]
    
    stats = {
        'total_requests': total_requests,
        'total_public_bodies': total_public_bodies,
        'avg_response_days': avg_response_days or 0,
        'overdue_count': overdue_count
    }
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "stats": stats,
            "status_labels": status_labels,
            "status_data": status_data,
            "outcome_labels": outcome_labels,
            "outcome_data": outcome_data,
            "month_labels": month_labels,
            "month_received_data": month_received_data,
            "month_completed_data": month_completed_data,
            "recent_requests": recent_requests,
            "top_public_bodies": top_public_bodies
        }
    )


@ui_router.get("/public-bodies", response_class=HTMLResponse)
async def public_bodies_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = None,
    active: Optional[str] = None,
    page: int = Query(1, ge=1)
):
    """List all public bodies with search and filtering."""
    per_page = 12
    offset = (page - 1) * per_page
    
    # Build query
    query = select(PublicBody, func.count(ATIRequest.id).label('request_count'))
    query = query.outerjoin(ATIRequest, PublicBody.id == ATIRequest.public_body_id)
    query = query.group_by(PublicBody.id)
    
    # Apply filters
    if search:
        search_filter = or_(
            PublicBody.name.ilike(f'%{search}%'),
            PublicBody.abbreviation.ilike(f'%{search}%')
        )
        query = query.where(search_filter)
    
    if active == 'true':
        query = query.where(PublicBody.is_active == True)
    elif active == 'false':
        query = query.where(PublicBody.is_active == False)
    
    # Get total count
    count_query = select(func.count(PublicBody.id))
    if search:
        count_query = count_query.where(or_(
            PublicBody.name.ilike(f'%{search}%'),
            PublicBody.abbreviation.ilike(f'%{search}%')
        ))
    if active == 'true':
        count_query = count_query.where(PublicBody.is_active == True)
    elif active == 'false':
        count_query = count_query.where(PublicBody.is_active == False)
    
    total_result = await db.execute(count_query)
    total_count = total_result.scalar() or 0
    total_pages = (total_count + per_page - 1) // per_page
    
    # Execute query with pagination
    query = query.order_by(PublicBody.name).offset(offset).limit(per_page)
    result = await db.execute(query)
    
    public_bodies = [
        {
            'id': str(row[0].id),
            'name': row[0].name,
            'abbreviation': row[0].abbreviation,
            'description': row[0].description,
            'is_active': row[0].is_active,
            'request_count': row[1]
        }
        for row in result.fetchall()
    ]
    
    return templates.TemplateResponse(
        "public_bodies/list.html",
        {
            "request": request,
            "public_bodies": public_bodies,
            "total_count": total_count,
            "total_pages": total_pages,
            "current_page": page,
            "search": search,
            "active": active
        }
    )


@ui_router.get("/public-bodies/{body_id}", response_class=HTMLResponse)
async def public_body_detail(
    request: Request,
    body_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Show detailed view for a specific public body."""
    # Get public body
    result = await db.execute(
        select(PublicBody).where(PublicBody.id == body_id)
    )
    body = result.scalar_one_or_none()
    
    if not body:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request},
            status_code=404
        )
    
    # Get stats
    stats = await get_body_stats(db, body_id)
    
    # Get outcome distribution
    outcome_result = await db.execute(
        select(ATIRequest.outcome, func.count(ATIRequest.id))
        .where(and_(ATIRequest.public_body_id == body_id, ATIRequest.outcome.isnot(None)))
        .group_by(ATIRequest.outcome)
    )
    outcome_counts = {str(row[0].value): row[1] for row in outcome_result.fetchall()}
    outcome_labels = [label.replace('_', ' ').title() for label in outcome_counts.keys()]
    outcome_data = list(outcome_counts.values())
    
    # Get monthly trends (last 12 months)
    today = date.today()
    twelve_months_ago = today - timedelta(days=365)
    monthly_result = await db.execute(
        select(
            func.date_trunc('month', ATIRequest.submission_date).label('month'),
            func.count(ATIRequest.id)
        )
        .where(and_(
            ATIRequest.public_body_id == body_id,
            ATIRequest.submission_date >= twelve_months_ago
        ))
        .group_by('month')
        .order_by('month')
    )
    monthly_data = monthly_result.fetchall()
    month_labels = [row[0].strftime('%b %Y') if row[0] else '' for row in monthly_data]
    month_data = [row[1] for row in monthly_data]
    
    # Get recent requests
    recent_result = await db.execute(
        select(ATIRequest)
        .where(ATIRequest.public_body_id == body_id)
        .order_by(ATIRequest.created_at.desc())
        .limit(10)
    )
    recent_requests = recent_result.scalars().all()
    
    return templates.TemplateResponse(
        "public_bodies/detail.html",
        {
            "request": request,
            "body": body,
            "stats": stats,
            "outcome_labels": outcome_labels,
            "outcome_data": outcome_data,
            "month_labels": month_labels,
            "month_data": month_data,
            "recent_requests": recent_requests
        }
    )


@ui_router.get("/requests", response_class=HTMLResponse)
async def requests_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = None,
    public_body: Optional[str] = None,
    status: Optional[str] = None,
    outcome: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    overdue: Optional[str] = None,
    page: int = Query(1, ge=1)
):
    """List ATI requests with search and filtering."""
    per_page = 20
    offset = (page - 1) * per_page
    today = date.today()
    
    # Build base query
    query = select(ATIRequest).options(selectinload(ATIRequest.public_body))
    count_query = select(func.count(ATIRequest.id))
    
    filters = []
    
    # Search filter
    if search:
        search_filter = or_(
            ATIRequest.request_number.ilike(f'%{search}%'),
            ATIRequest.summary.ilike(f'%{search}%')
        )
        filters.append(search_filter)
    
    # Public body filter
    if public_body:
        try:
            pb_uuid = UUID(public_body)
            filters.append(ATIRequest.public_body_id == pb_uuid)
        except ValueError:
            pass
    
    # Status filter
    if status:
        try:
            status_enum = RequestStatus(status)
            filters.append(ATIRequest.status == status_enum)
        except ValueError:
            pass
    
    # Outcome filter
    if outcome:
        try:
            outcome_enum = RequestOutcome(outcome)
            filters.append(ATIRequest.outcome == outcome_enum)
        except ValueError:
            pass
    
    # Date filters
    if date_from:
        try:
            from_date = date.fromisoformat(date_from)
            filters.append(ATIRequest.submission_date >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = date.fromisoformat(date_to)
            filters.append(ATIRequest.submission_date <= to_date)
        except ValueError:
            pass
    
    # Overdue filter
    if overdue == 'true':
        filters.append(and_(
            ATIRequest.due_date < today,
            ATIRequest.status.notin_([RequestStatus.completed, RequestStatus.abandoned, RequestStatus.transferred])
        ))
    
    # Apply filters
    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
    
    # Get total count
    total_result = await db.execute(count_query)
    total_count = total_result.scalar() or 0
    total_pages = (total_count + per_page - 1) // per_page
    
    # Execute query
    query = query.order_by(ATIRequest.submission_date.desc()).offset(offset).limit(per_page)
    result = await db.execute(query)
    requests_list = result.scalars().all()
    
    # Add is_overdue flag to each request
    for req in requests_list:
        req.is_overdue = (
            req.due_date and 
            req.due_date < today and 
            req.status not in [RequestStatus.completed, RequestStatus.abandoned, RequestStatus.transferred]
        )
    
    # Get public bodies for filter dropdown
    pb_result = await db.execute(select(PublicBody).order_by(PublicBody.name))
    public_bodies = pb_result.scalars().all()
    
    return templates.TemplateResponse(
        "requests/list.html",
        {
            "request": request,
            "requests": requests_list,
            "public_bodies": public_bodies,
            "total_count": total_count,
            "total_pages": total_pages,
            "current_page": page,
            "search": search,
            "public_body": public_body,
            "status": status,
            "outcome": outcome,
            "date_from": date_from,
            "date_to": date_to,
            "overdue": overdue == 'true'
        }
    )


@ui_router.get("/requests/{request_id}", response_class=HTMLResponse)
async def request_detail(
    request: Request,
    request_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Show detailed view for a specific ATI request."""
    result = await db.execute(
        select(ATIRequest)
        .options(selectinload(ATIRequest.public_body))
        .where(ATIRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    
    if not req:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request},
            status_code=404
        )
    
    today = date.today()
    is_overdue = (
        req.due_date and 
        req.due_date < today and 
        req.status not in [RequestStatus.completed, RequestStatus.abandoned, RequestStatus.transferred]
    )
    
    # Calculate response time if completed
    response_time = None
    if req.completion_date and req.submission_date:
        response_time = (req.completion_date - req.submission_date).days
    
    return templates.TemplateResponse(
        "requests/detail.html",
        {
            "request": request,
            "req": req,
            "is_overdue": is_overdue,
            "response_time": response_time
        }
    )


@ui_router.get("/compare", response_class=HTMLResponse)
async def compare(
    request: Request,
    db: AsyncSession = Depends(get_db),
    type: str = Query("bodies", regex="^(bodies|years)$"),
    body1: Optional[str] = None,
    body2: Optional[str] = None,
    year1: Optional[int] = None,
    year2: Optional[int] = None,
    body_filter: Optional[str] = None
):
    """Comparison tools for public bodies and year-over-year analysis."""
    # Get all public bodies for dropdowns
    pb_result = await db.execute(select(PublicBody).order_by(PublicBody.name))
    public_bodies = pb_result.scalars().all()
    
    # Get available years
    years_result = await db.execute(
        select(func.distinct(extract('year', ATIRequest.submission_date)))
        .where(ATIRequest.submission_date.isnot(None))
        .order_by(extract('year', ATIRequest.submission_date).desc())
    )
    available_years = [int(y[0]) for y in years_result.fetchall() if y[0]]
    if not available_years:
        available_years = [date.today().year, date.today().year - 1]
    
    context = {
        "request": request,
        "comparison_type": type,
        "public_bodies": public_bodies,
        "available_years": available_years,
        "body1_id": body1,
        "body2_id": body2,
        "year1": year1,
        "year2": year2,
        "body_filter": body_filter
    }
    
    if type == "bodies" and body1 and body2:
        # Body-to-body comparison
        try:
            body1_uuid = UUID(body1)
            body2_uuid = UUID(body2)
            
            # Get body details
            b1_result = await db.execute(select(PublicBody).where(PublicBody.id == body1_uuid))
            b2_result = await db.execute(select(PublicBody).where(PublicBody.id == body2_uuid))
            body1_obj = b1_result.scalar_one_or_none()
            body2_obj = b2_result.scalar_one_or_none()
            
            if body1_obj and body2_obj:
                stats1 = await get_body_stats(db, body1_uuid)
                stats2 = await get_body_stats(db, body2_uuid)
                
                # Get outcome distributions
                outcomes = ['full_disclosure', 'partial_disclosure', 'no_disclosure', 'no_records_exist']
                outcome_labels = [o.replace('_', ' ').title() for o in outcomes]
                
                outcome_data1 = []
                outcome_data2 = []
                for outcome in outcomes:
                    try:
                        outcome_enum = RequestOutcome(outcome)
                        r1 = await db.execute(
                            select(func.count(ATIRequest.id)).where(
                                and_(ATIRequest.public_body_id == body1_uuid, ATIRequest.outcome == outcome_enum)
                            )
                        )
                        r2 = await db.execute(
                            select(func.count(ATIRequest.id)).where(
                                and_(ATIRequest.public_body_id == body2_uuid, ATIRequest.outcome == outcome_enum)
                            )
                        )
                        outcome_data1.append(r1.scalar() or 0)
                        outcome_data2.append(r2.scalar() or 0)
                    except ValueError:
                        outcome_data1.append(0)
                        outcome_data2.append(0)
                
                # Get monthly data for last 12 months
                today = date.today()
                twelve_months_ago = today - timedelta(days=365)
                
                monthly1_result = await db.execute(
                    select(
                        func.date_trunc('month', ATIRequest.submission_date).label('month'),
                        func.count(ATIRequest.id)
                    )
                    .where(and_(
                        ATIRequest.public_body_id == body1_uuid,
                        ATIRequest.submission_date >= twelve_months_ago
                    ))
                    .group_by('month')
                    .order_by('month')
                )
                monthly1 = {row[0]: row[1] for row in monthly1_result.fetchall() if row[0]}
                
                monthly2_result = await db.execute(
                    select(
                        func.date_trunc('month', ATIRequest.submission_date).label('month'),
                        func.count(ATIRequest.id)
                    )
                    .where(and_(
                        ATIRequest.public_body_id == body2_uuid,
                        ATIRequest.submission_date >= twelve_months_ago
                    ))
                    .group_by('month')
                    .order_by('month')
                )
                monthly2 = {row[0]: row[1] for row in monthly2_result.fetchall() if row[0]}
                
                # Generate month labels and data
                all_months = sorted(set(list(monthly1.keys()) + list(monthly2.keys())))
                month_labels = [m.strftime('%b %Y') if m else '' for m in all_months]
                month_data1 = [monthly1.get(m, 0) for m in all_months]
                month_data2 = [monthly2.get(m, 0) for m in all_months]
                
                context.update({
                    "body1": body1_obj,
                    "body2": body2_obj,
                    "stats1": stats1,
                    "stats2": stats2,
                    "outcome_labels": outcome_labels,
                    "outcome_data1": outcome_data1,
                    "outcome_data2": outcome_data2,
                    "month_labels": month_labels,
                    "month_data1": month_data1,
                    "month_data2": month_data2
                })
        except ValueError:
            pass
    
    elif type == "years" and year1 and year2:
        # Year-over-year comparison
        body_uuid = None
        if body_filter:
            try:
                body_uuid = UUID(body_filter)
            except ValueError:
                pass
        
        year1_stats = await get_year_stats(db, year1, body_uuid)
        year2_stats = await get_year_stats(db, year2, body_uuid)
        
        # Get monthly breakdown for each year
        year1_monthly = []
        year2_monthly = []
        
        for month in range(1, 13):
            # Year 1
            start1 = date(year1, month, 1)
            if month == 12:
                end1 = date(year1 + 1, 1, 1) - timedelta(days=1)
            else:
                end1 = date(year1, month + 1, 1) - timedelta(days=1)
            
            filter1 = and_(
                ATIRequest.submission_date >= start1,
                ATIRequest.submission_date <= end1
            )
            if body_uuid:
                filter1 = and_(filter1, ATIRequest.public_body_id == body_uuid)
            
            r1 = await db.execute(select(func.count(ATIRequest.id)).where(filter1))
            year1_monthly.append(r1.scalar() or 0)
            
            # Year 2
            start2 = date(year2, month, 1)
            if month == 12:
                end2 = date(year2 + 1, 1, 1) - timedelta(days=1)
            else:
                end2 = date(year2, month + 1, 1) - timedelta(days=1)
            
            filter2 = and_(
                ATIRequest.submission_date >= start2,
                ATIRequest.submission_date <= end2
            )
            if body_uuid:
                filter2 = and_(filter2, ATIRequest.public_body_id == body_uuid)
            
            r2 = await db.execute(select(func.count(ATIRequest.id)).where(filter2))
            year2_monthly.append(r2.scalar() or 0)
        
        context.update({
            "year1": year1,
            "year2": year2,
            "year1_stats": year1_stats,
            "year2_stats": year2_stats,
            "year1_monthly": year1_monthly,
            "year2_monthly": year2_monthly
        })
    
    return templates.TemplateResponse("compare.html", context)
