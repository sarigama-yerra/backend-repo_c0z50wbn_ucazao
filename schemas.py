"""
Database Schemas for JustPlay League Manager

Pydantic models below describe the core domain. Each class name maps to a
collection name using its lowercase form if/when persistence is enabled.

This initial release uses mocked data served by the API, but schemas are
defined up-front so we can seamlessly switch to MongoDB persistence later.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Literal
from datetime import date, datetime

SportType = Literal["basketball"]


class Player(BaseModel):
    id: str = Field(..., description="Unique player id")
    name: str
    avatar: Optional[HttpUrl] = None
    position: Optional[str] = None


class Team(BaseModel):
    id: str
    name: str
    avatar: Optional[HttpUrl] = None
    players: List[Player] = []


class Member(BaseModel):
    id: str
    name: str
    role: Literal["organizer", "member"] = "member"
    joined_at: datetime


class League(BaseModel):
    id: str
    code: str = Field(..., description="Short code used to join league")
    name: str
    description: Optional[str] = None
    sport: SportType = "basketball"
    location: Optional[str] = None
    start_date: Optional[date] = None
    avatar: Optional[HttpUrl] = None
    allow_free_join: bool = True
    number_of_teams: Optional[int] = None
    organizer: Member
    teams: List[Team] = []
    members: List[Member] = []


class Match(BaseModel):
    id: str
    league_id: str
    round: int
    home_team_id: str
    away_team_id: str
    court: Optional[str] = None
    scheduled_at: datetime
    home_score: Optional[int] = None
    away_score: Optional[int] = None


class CreateLeagueRequest(BaseModel):
    name: str
    description: Optional[str] = None
    sport: SportType = "basketball"
    location: Optional[str] = None
    start_date: Optional[date] = None
    avatar: Optional[HttpUrl] = None
    number_of_teams: Optional[int] = None
    allow_free_join: bool = True
    organizer_name: str


class JoinLeagueRequest(BaseModel):
    name: str
