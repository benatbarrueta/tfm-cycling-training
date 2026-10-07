from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    google_subject: Mapped[str | None] = mapped_column(String(255), unique=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(2048))
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    cyclist_profile: Mapped["CyclistProfile | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="sessions")


class CyclistProfile(Base):
    __tablename__ = "cyclist_profiles"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    ftp: Mapped[float] = mapped_column(nullable=False)
    weekly_hours: Mapped[float] = mapped_column(nullable=False)
    available_days: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    modality: Mapped[str] = mapped_column(String(32), nullable=False)
    level: Mapped[str] = mapped_column(String(32), nullable=False)
    objective: Mapped[str] = mapped_column(String(32), nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/Madrid")
    onboarding_completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user: Mapped[User] = relationship(back_populates="cyclist_profile")


class ActivityRecord(Base):
    __tablename__ = "activities"
    __table_args__ = (
        Index("ix_activities_user_started_at", "user_id", "started_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    sport: Mapped[str] = mapped_column(String(32), nullable=False)
    duration_minutes: Mapped[float] = mapped_column(Float, nullable=False)
    distance_km: Mapped[float | None] = mapped_column(Float)
    average_power: Mapped[float | None] = mapped_column(Float)
    normalized_power: Mapped[float | None] = mapped_column(Float)
    average_heart_rate: Mapped[float | None] = mapped_column(Float)
    intensity_factor: Mapped[float | None] = mapped_column(Float)
    tss: Mapped[float | None] = mapped_column(Float)
    aerobic_decoupling: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    external_source_id: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(String(4000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class SeasonPlan(Base):
    __tablename__ = "season_plans"
    __table_args__ = (Index("ix_season_plans_user_status", "user_id", "status"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    objective: Mapped[str] = mapped_column(String(32), nullable=False)
    modality: Mapped[str] = mapped_column(String(32), nullable=False)
    level: Mapped[str] = mapped_column(String(32), nullable=False)
    ftp_snapshot: Mapped[float] = mapped_column(Float, nullable=False)
    weekly_hours_snapshot: Mapped[float] = mapped_column(Float, nullable=False)
    available_days_snapshot: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    generator_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    phases: Mapped[list["TrainingPhase"]] = relationship(back_populates="season_plan", cascade="all, delete-orphan")
    weeks: Mapped[list["PlannedWeek"]] = relationship(back_populates="season_plan", cascade="all, delete-orphan")


class TrainingPhase(Base):
    __tablename__ = "training_phases"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    season_plan_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("season_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    phase_type: Mapped[str] = mapped_column(String(32), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    week_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    season_plan: Mapped[SeasonPlan] = relationship(back_populates="phases")
    weeks: Mapped[list["PlannedWeek"]] = relationship(back_populates="training_phase")


class PlannedWeek(Base):
    __tablename__ = "planned_weeks"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    season_plan_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("season_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    training_phase_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("training_phases.id", ondelete="CASCADE"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    focus: Mapped[str] = mapped_column(String(64), nullable=False)
    provisional_target_tss: Mapped[float] = mapped_column(Float, nullable=False)
    provisional_hours: Mapped[float] = mapped_column(Float, nullable=False)
    requested_target_tss: Mapped[float | None] = mapped_column(Float)
    adapted_target_tss: Mapped[float | None] = mapped_column(Float)
    estimated_total_tss: Mapped[float | None] = mapped_column(Float)
    expected_aerobic_decoupling: Mapped[float | None] = mapped_column(Float)
    response_prediction_method: Mapped[str | None] = mapped_column(String(64))
    load_decision: Mapped[str | None] = mapped_column(String(32))
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    season_plan: Mapped[SeasonPlan] = relationship(back_populates="weeks")
    training_phase: Mapped[TrainingPhase] = relationship(back_populates="weeks")
    workouts: Mapped[list["PlannedWorkout"]] = relationship(back_populates="planned_week", cascade="all, delete-orphan")

    @property
    def phase(self) -> str:
        return self.training_phase.phase_type


class PlannedWorkout(Base):
    __tablename__ = "planned_workouts"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    planned_week_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("planned_weeks.id", ondelete="CASCADE"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    day: Mapped[str] = mapped_column(String(16), nullable=False)
    workout_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_tss: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_tss: Mapped[float | None] = mapped_column(Float)
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    target_power_min: Mapped[float | None] = mapped_column(Float)
    target_power_max: Mapped[float | None] = mapped_column(Float)
    warmup: Mapped[dict | None] = mapped_column(JSON)
    intervals: Mapped[dict | None] = mapped_column(JSON)
    cooldown: Mapped[dict | None] = mapped_column(JSON)
    predicted_aerobic_decoupling: Mapped[float | None] = mapped_column(Float)
    aerobic_response: Mapped[str | None] = mapped_column(String(32))
    outside_training_range_features: Mapped[list[str] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    planned_week: Mapped[PlannedWeek] = relationship(back_populates="workouts")
