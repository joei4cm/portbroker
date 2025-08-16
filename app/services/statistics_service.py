"""
Statistics service for tracking and retrieving request statistics
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_utils import get_logger
from app.models.strategy import APIKey, ModelStrategy, Provider, RequestStatistics

logger = get_logger(__name__)


class StatisticsService:
    """Service for managing request statistics"""

    @staticmethod
    async def track_request(
        db: AsyncSession,
        trace_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: int,
        provider_id: Optional[int] = None,
        provider_name: Optional[str] = None,
        strategy_id: Optional[int] = None,
        strategy_name: Optional[str] = None,
        strategy_type: Optional[str] = None,
        requested_model: Optional[str] = None,
        actual_model: Optional[str] = None,
        model_tier: Optional[str] = None,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        api_key_id: Optional[int] = None,
    ) -> RequestStatistics:
        """Track a request in statistics"""
        try:
            stat = RequestStatistics(
                trace_id=trace_id,
                endpoint=endpoint,
                method=method,
                provider_id=provider_id,
                provider_name=provider_name,
                strategy_id=strategy_id,
                strategy_name=strategy_name,
                strategy_type=strategy_type,
                requested_model=requested_model,
                actual_model=actual_model,
                model_tier=model_tier,
                status_code=status_code,
                duration_ms=duration_ms,
                request_size=request_size,
                response_size=response_size,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                error_code=error_code,
                error_message=error_message,
                client_ip=client_ip,
                user_agent=user_agent,
                api_key_id=api_key_id,
            )
            
            db.add(stat)
            await db.commit()
            await db.refresh(stat)
            
            logger.debug(
                "Request tracked in statistics",
                extra={
                    "trace_id": trace_id,
                    "endpoint": endpoint,
                    "provider_name": provider_name,
                    "strategy_name": strategy_name,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                }
            )
            
            return stat
            
        except Exception as e:
            logger.error(
                "Failed to track request statistics",
                extra={
                    "trace_id": trace_id,
                    "endpoint": endpoint,
                    "error": str(e),
                }
            )
            # Don't fail the main request if statistics tracking fails
            await db.rollback()
            raise

    @staticmethod
    async def get_dashboard_stats(db: AsyncSession) -> Dict:
        """Get statistics for dashboard display"""
        try:
            # Get basic counts
            providers_count = await db.scalar(
                select(func.count(Provider.id)).where(Provider.is_active == True)
            )
            
            strategies_count = await db.scalar(
                select(func.count(ModelStrategy.id)).where(ModelStrategy.is_active == True)
            )
            
            api_keys_count = await db.scalar(
                select(func.count(APIKey.id)).where(APIKey.is_active == True)
            )
            
            # Get total requests
            total_requests = await db.scalar(
                select(func.count(RequestStatistics.id))
            ) or 0
            
            # Get requests in last 24 hours
            yesterday = datetime.utcnow() - timedelta(days=1)
            requests_24h = await db.scalar(
                select(func.count(RequestStatistics.id)).where(
                    RequestStatistics.created_at >= yesterday
                )
            ) or 0
            
            # Get average response time in last 24 hours
            avg_duration = await db.scalar(
                select(func.avg(RequestStatistics.duration_ms)).where(
                    and_(
                        RequestStatistics.created_at >= yesterday,
                        RequestStatistics.status_code < 400
                    )
                )
            ) or 0
            
            # Get success rate in last 24 hours
            total_24h = await db.scalar(
                select(func.count(RequestStatistics.id)).where(
                    RequestStatistics.created_at >= yesterday
                )
            ) or 0
            
            success_24h = await db.scalar(
                select(func.count(RequestStatistics.id)).where(
                    and_(
                        RequestStatistics.created_at >= yesterday,
                        RequestStatistics.status_code < 400
                    )
                )
            ) or 0
            
            success_rate = (success_24h / total_24h * 100) if total_24h > 0 else 100
            
            return {
                "providers": providers_count or 0,
                "strategies": strategies_count or 0,
                "apiKeys": api_keys_count or 0,
                "requests": total_requests,
                "requests24h": requests_24h,
                "avgDuration": round(avg_duration, 2),
                "successRate": round(success_rate, 2),
            }
            
        except Exception as e:
            logger.error("Failed to get dashboard stats", extra={"error": str(e)})
            # Return default stats on error
            return {
                "providers": 0,
                "strategies": 0,
                "apiKeys": 0,
                "requests": 0,
                "requests24h": 0,
                "avgDuration": 0,
                "successRate": 100,
            }

    @staticmethod
    async def get_provider_stats(db: AsyncSession, days: int = 7) -> List[Dict]:
        """Get provider usage statistics"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            result = await db.execute(
                select(
                    RequestStatistics.provider_name,
                    func.count(RequestStatistics.id).label("request_count"),
                    func.avg(RequestStatistics.duration_ms).label("avg_duration"),
                    func.sum(
                        case(
                            (RequestStatistics.status_code < 400, 1),
                            else_=0
                        )
                    ).label("success_count"),
                    func.count(RequestStatistics.id).label("total_count"),
                )
                .where(
                    and_(
                        RequestStatistics.created_at >= cutoff_date,
                        RequestStatistics.provider_name.isnot(None)
                    )
                )
                .group_by(RequestStatistics.provider_name)
                .order_by(desc("request_count"))
            )
            
            provider_stats = []
            for row in result:
                success_rate = (row.success_count / row.total_count * 100) if row.total_count > 0 else 100
                provider_stats.append({
                    "provider_name": row.provider_name,
                    "request_count": row.request_count,
                    "avg_duration": round(row.avg_duration or 0, 2),
                    "success_rate": round(success_rate, 2),
                })
            
            return provider_stats
            
        except Exception as e:
            logger.error("Failed to get provider stats", extra={"error": str(e)})
            return []

    @staticmethod
    async def get_strategy_stats(db: AsyncSession, days: int = 7) -> List[Dict]:
        """Get strategy usage statistics"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            result = await db.execute(
                select(
                    RequestStatistics.strategy_name,
                    RequestStatistics.strategy_type,
                    func.count(RequestStatistics.id).label("request_count"),
                    func.avg(RequestStatistics.duration_ms).label("avg_duration"),
                    func.sum(
                        case(
                            (RequestStatistics.status_code < 400, 1),
                            else_=0
                        )
                    ).label("success_count"),
                    func.count(RequestStatistics.id).label("total_count"),
                )
                .where(
                    and_(
                        RequestStatistics.created_at >= cutoff_date,
                        RequestStatistics.strategy_name.isnot(None)
                    )
                )
                .group_by(
                    RequestStatistics.strategy_name,
                    RequestStatistics.strategy_type
                )
                .order_by(desc("request_count"))
            )
            
            strategy_stats = []
            for row in result:
                success_rate = (row.success_count / row.total_count * 100) if row.total_count > 0 else 100
                strategy_stats.append({
                    "strategy_name": row.strategy_name,
                    "strategy_type": row.strategy_type,
                    "request_count": row.request_count,
                    "avg_duration": round(row.avg_duration or 0, 2),
                    "success_rate": round(success_rate, 2),
                })
            
            return strategy_stats
            
        except Exception as e:
            logger.error("Failed to get strategy stats", extra={"error": str(e)})
            return []

    @staticmethod
    async def get_recent_activity(db: AsyncSession, limit: int = 10) -> List[Dict]:
        """Get recent activity for dashboard"""
        try:
            result = await db.execute(
                select(RequestStatistics)
                .order_by(desc(RequestStatistics.created_at))
                .limit(limit)
            )
            
            activities = []
            for stat in result.scalars():
                # Determine activity type
                if stat.endpoint.startswith("/api/anthropic"):
                    activity_type = "Anthropic Request"
                elif stat.endpoint.startswith("/api/v1/chat"):
                    activity_type = "OpenAI Request"
                elif stat.endpoint.startswith("/api/portal"):
                    activity_type = "Portal Activity"
                else:
                    activity_type = "API Request"
                
                # Create description
                if stat.provider_name and stat.strategy_name:
                    description = f"via {stat.provider_name} ({stat.strategy_name})"
                elif stat.provider_name:
                    description = f"via {stat.provider_name}"
                elif stat.strategy_name:
                    description = f"using {stat.strategy_name}"
                else:
                    description = f"{stat.method} {stat.endpoint}"
                
                # Format time
                time_diff = datetime.utcnow() - stat.created_at
                if time_diff.total_seconds() < 60:
                    time_str = "just now"
                elif time_diff.total_seconds() < 3600:
                    time_str = f"{int(time_diff.total_seconds() // 60)} min ago"
                else:
                    time_str = f"{int(time_diff.total_seconds() // 3600)} hours ago"
                
                activities.append({
                    "title": activity_type,
                    "description": description,
                    "time": time_str,
                    "status": "success" if stat.status_code < 400 else "error",
                    "duration": stat.duration_ms,
                })
            
            return activities
            
        except Exception as e:
            logger.error("Failed to get recent activity", extra={"error": str(e)})
            return []

    @staticmethod
    async def get_hourly_request_counts(db: AsyncSession, hours: int = 24) -> List[Dict]:
        """Get hourly request counts for the last N hours"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(hours=hours)
            
            result = await db.execute(
                select(
                    func.date_trunc('hour', RequestStatistics.created_at).label('hour'),
                    func.count(RequestStatistics.id).label('count'),
                    func.sum(
                        case(
                            (RequestStatistics.status_code < 400, 1),
                            else_=0
                        )
                    ).label("success_count"),
                )
                .where(RequestStatistics.created_at >= cutoff_date)
                .group_by(func.date_trunc('hour', RequestStatistics.created_at))
                .order_by('hour')
            )
            
            hourly_stats = []
            for row in result:
                success_rate = (row.success_count / row.count * 100) if row.count > 0 else 100
                hourly_stats.append({
                    "hour": row.hour.isoformat(),
                    "count": row.count,
                    "success_rate": round(success_rate, 2),
                })
            
            return hourly_stats
            
        except Exception as e:
            logger.error("Failed to get hourly request counts", extra={"error": str(e)})
            return []