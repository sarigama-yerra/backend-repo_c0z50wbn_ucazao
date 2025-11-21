import os
import random
import string
from datetime import datetime, timedelta, date
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from schemas import (
    League,
    Team,
    Player,
    Member,
    Match,
    CreateLeagueRequest,
    JoinLeagueRequest,
)

app = FastAPI(title="JustPlay League Manager API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Mock Data Store (in-memory for this prototype)
# ---------------------------------------------------------------------------
MOCK_LEAGUES: dict[str, League] = {}
MOCK_MATCHES: dict[str, List[Match]] = {}


def _gen_id(prefix: str) -> str:
    return f"{prefix}_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


def _gen_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


# ---------------------------------------------------------------------------
# Health & Schema
# ---------------------------------------------------------------------------
@app.get("/")
def read_root():
    return {"message": "JustPlay League Manager Backend is running"}


@app.get("/schema")
def get_schema_overview():
    return {
        "models": ["League", "Team", "Player", "Member", "Match"],
        "version": 1,
    }


# ---------------------------------------------------------------------------
# League APIs
# ---------------------------------------------------------------------------
@app.post("/api/leagues", response_model=League)
def create_league(payload: CreateLeagueRequest):
    league_id = _gen_id("league")
    code = _gen_code()

    organizer = Member(
        id=_gen_id("user"),
        name=payload.organizer_name,
        role="organizer",
        joined_at=datetime.utcnow(),
    )

    league = League(
        id=league_id,
        code=code,
        name=payload.name,
        description=payload.description,
        sport=payload.sport,
        location=payload.location,
        start_date=payload.start_date,
        avatar=payload.avatar,
        allow_free_join=payload.allow_free_join,
        number_of_teams=payload.number_of_teams,
        organizer=organizer,
        teams=[],
        members=[organizer],
    )

    MOCK_LEAGUES[league_id] = league
    MOCK_MATCHES[league_id] = []
    return league


@app.get("/api/leagues", response_model=List[League])
def list_leagues():
    return list(MOCK_LEAGUES.values())


@app.get("/api/leagues/{league_id}", response_model=League)
def get_league(league_id: str):
    league = MOCK_LEAGUES.get(league_id)
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    return league


class UpdateLeagueRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[date] = None
    avatar: Optional[str] = None
    allow_free_join: Optional[bool] = None
    number_of_teams: Optional[int] = None


@app.patch("/api/leagues/{league_id}", response_model=League)
def update_league(league_id: str, payload: UpdateLeagueRequest):
    league = MOCK_LEAGUES.get(league_id)
    if not league:
        raise HTTPException(status_code=404, detail="League not found")

    data = payload.model_dump(exclude_unset=True)
    updated = league.model_copy(update=data)
    MOCK_LEAGUES[league_id] = updated
    return updated


# ---------------------------------------------------------------------------
# Membership
# ---------------------------------------------------------------------------
@app.post("/api/leagues/{league_id}/join", response_model=League)
def join_league(league_id: str, payload: JoinLeagueRequest):
    league = MOCK_LEAGUES.get(league_id)
    if not league:
        raise HTTPException(status_code=404, detail="League not found")

    member = Member(id=_gen_id("user"), name=payload.name, role="member", joined_at=datetime.utcnow())
    updated_members = list(league.members) + [member]
    updated = league.model_copy(update={"members": updated_members})
    MOCK_LEAGUES[league_id] = updated
    return updated


@app.post("/api/leagues/join/{code}", response_model=League)
def join_league_by_code(code: str, payload: JoinLeagueRequest):
    for league in MOCK_LEAGUES.values():
        if league.code == code:
            member = Member(id=_gen_id("user"), name=payload.name, role="member", joined_at=datetime.utcnow())
            updated_members = list(league.members) + [member]
            updated = league.model_copy(update={"members": updated_members})
            MOCK_LEAGUES[league.id] = updated
            return updated
    raise HTTPException(status_code=404, detail="Invalid code")


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------
class CreateTeamRequest(BaseModel):
    name: str
    avatar: Optional[str] = None


@app.post("/api/leagues/{league_id}/teams", response_model=League)
def add_team(league_id: str, payload: CreateTeamRequest):
    league = MOCK_LEAGUES.get(league_id)
    if not league:
        raise HTTPException(status_code=404, detail="League not found")

    new_team = Team(id=_gen_id("team"), name=payload.name, avatar=payload.avatar, players=[])
    updated_teams = list(league.teams) + [new_team]
    updated = league.model_copy(update={"teams": updated_teams})
    MOCK_LEAGUES[league_id] = updated
    return updated


@app.delete("/api/leagues/{league_id}/teams/{team_id}", response_model=League)
def remove_team(league_id: str, team_id: str):
    league = MOCK_LEAGUES.get(league_id)
    if not league:
        raise HTTPException(status_code=404, detail="League not found")

    updated_teams = [t for t in league.teams if t.id != team_id]
    updated = league.model_copy(update={"teams": updated_teams})
    MOCK_LEAGUES[league_id] = updated
    return updated


class AddPlayerRequest(BaseModel):
    team_id: str
    name: str
    avatar: Optional[str] = None
    position: Optional[str] = None


@app.post("/api/leagues/{league_id}/players", response_model=League)
def add_player(league_id: str, payload: AddPlayerRequest):
    league = MOCK_LEAGUES.get(league_id)
    if not league:
        raise HTTPException(status_code=404, detail="League not found")

    player = Player(id=_gen_id("player"), name=payload.name, avatar=payload.avatar, position=payload.position)

    teams = []
    for t in league.teams:
        if t.id == payload.team_id:
            teams.append(t.model_copy(update={"players": list(t.players) + [player]}))
        else:
            teams.append(t)

    updated = league.model_copy(update={"teams": teams})
    MOCK_LEAGUES[league_id] = updated
    return updated


# ---------------------------------------------------------------------------
# Scheduling & Results
# ---------------------------------------------------------------------------
class GenerateScheduleRequest(BaseModel):
    rounds: int = 1
    start_at: Optional[datetime] = None
    days_between: int = 7


@app.post("/api/leagues/{league_id}/schedule", response_model=List[Match])
def generate_schedule(league_id: str, payload: GenerateScheduleRequest):
    league = MOCK_LEAGUES.get(league_id)
    if not league:
        raise HTTPException(status_code=404, detail="League not found")

    teams = league.teams
    if len(teams) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 teams to schedule matches")

    start_time = payload.start_at or datetime.utcnow() + timedelta(days=1)

    matches: List[Match] = []
    when = start_time
    for r in range(1, payload.rounds + 1):
        for i in range(0, len(teams), 2):
            if i + 1 < len(teams):
                home = teams[i]
                away = teams[i + 1]
                matches.append(
                    Match(
                        id=_gen_id("match"),
                        league_id=league_id,
                        round=r,
                        home_team_id=home.id,
                        away_team_id=away.id,
                        court=None,
                        scheduled_at=when,
                    )
                )
                when = when + timedelta(days=payload.days_between)

    MOCK_MATCHES[league_id] = matches
    return matches


@app.get("/api/leagues/{league_id}/schedule", response_model=List[Match])
def get_schedule(league_id: str):
    return MOCK_MATCHES.get(league_id, [])


class UpdateResultRequest(BaseModel):
    match_id: str
    home_score: int
    away_score: int


@app.post("/api/leagues/{league_id}/results", response_model=List[Match])
def update_result(league_id: str, payload: UpdateResultRequest):
    matches = MOCK_MATCHES.get(league_id, [])
    found = False
    updated_list: List[Match] = []
    for m in matches:
        if m.id == payload.match_id:
            updated_list.append(
                m.model_copy(update={"home_score": payload.home_score, "away_score": payload.away_score})
            )
            found = True
        else:
            updated_list.append(m)

    if not found:
        raise HTTPException(status_code=404, detail="Match not found")

    MOCK_MATCHES[league_id] = updated_list
    return updated_list


# ---------------------------------------------------------------------------
# Standings (computed)
# ---------------------------------------------------------------------------
class Standing(BaseModel):
    team_id: str
    team_name: str
    played: int
    wins: int
    losses: int
    points_for: int
    points_against: int


@app.get("/api/leagues/{league_id}/standings", response_model=List[Standing])
def standings(league_id: str):
    league = MOCK_LEAGUES.get(league_id)
    if not league:
        raise HTTPException(status_code=404, detail="League not found")

    stats: dict[str, Standing] = {}
    for t in league.teams:
        stats[t.id] = Standing(
            team_id=t.id,
            team_name=t.name,
            played=0,
            wins=0,
            losses=0,
            points_for=0,
            points_against=0,
        )

    for m in MOCK_MATCHES.get(league_id, []):
        if m.home_score is None or m.away_score is None:
            continue
        h = stats[m.home_team_id]
        a = stats[m.away_team_id]
        h.played += 1
        a.played += 1
        h.points_for += m.home_score
        h.points_against += m.away_score
        a.points_for += m.away_score
        a.points_against += m.home_score
        if m.home_score > m.away_score:
            h.wins += 1
            a.losses += 1
        elif m.away_score > m.home_score:
            a.wins += 1
            h.losses += 1

    # Sort: wins desc, point diff desc
    table = sorted(
        stats.values(),
        key=lambda s: (s.wins, s.points_for - s.points_against),
        reverse=True,
    )
    return table


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
