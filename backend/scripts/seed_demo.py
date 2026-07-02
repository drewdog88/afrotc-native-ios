"""Seed a local SQLite database for the web prototype with the detachment's REAL data.

The schools/contacts and cadets below were read (read-only) from the existing Neon
production database — the actual Det 695 recruiting footprint across the Seattle and
Portland Catholic/Jesuit high schools, and the actual cadet roster. Coordinates for
each school were geocoded from their real campus addresses so the Territory map draws
the real recruiting territory.

Two datasets have no real source and are marked DEMO where they appear:
  * RECRUITS — production has zero potential-recruits entered, but the funnel/trend
    analytics are the app's non-negotiable feature, so we seed a plausible pipeline
    anchored to the REAL schools above (backdated stage events give the trend a shape).
  * EVENTS — the only rows in production are two "API Smoke Event" test artifacts, so
    we seed a few realistic outreach events tied to the REAL schools instead.

    uv run python scripts/seed_demo.py

Idempotent-ish: wipes the recruit/cadet/follow-up/event/contact tables first so
re-running gives a clean, deterministic dataset. Writes ONLY to the local dev DB
(app.core.database) — never point this at, or write to, production.
"""
from __future__ import annotations

import sys
from datetime import date, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import hash_password, now_utc  # noqa: E402
from app.models import (  # noqa: E402
    Cadet,
    FollowUp,
    PotentialRecruit,
    RecruitmentEvent,
    RecruitStageEvent,
    UniversityContact,
    User,
)
from app.models.enums import (  # noqa: E402
    CadetStatus,
    EventStatus,
    SchoolType,
)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Det695Demo!"  # prototype-only credential

# ---------------------------------------------------------------------------
# REAL contacts — the detachment's actual recruiting relationships, read from the
# production Neon DB. lat/lng geocoded from each school's real campus address so the
# Territory map plots the true Seattle/Portland footprint.
# (university_name, contact_name, contact_title, email, phone, address, notes, lat, lng, is_active)
# ---------------------------------------------------------------------------
CONTACTS = [
    ("Seattle Preparatory School", "Ann Alokolaro", "Director of Admissions", "aalokolaro@seaprep.org", "(206) 577-2146", "2400 11th Ave E, Seattle, WA 98102", "Catholic Preparatory School — AFROTC Recruitment Contact", 47.6395, -122.3178, True),
    ("Cristo Rey Jesuit Seattle", "Flor Gonzalez", "Admissions", "fgonzalez@cristoreyseattle.org", "(206) 688-2108", "1401 E Jefferson St, Seattle, WA 98122", "Jesuit High School — AFROTC Recruitment Contact", 47.6035, -122.3140, True),
    ("Bishop Blanchet HS", "General Office", "General Contact", "mainoffice@bishopblanchet.org", "(206) 527-7711", "8200 Wallingford Ave N, Seattle, WA 98103", "Catholic High School — AFROTC Recruitment Contact", 47.6905, -122.3350, True),
    ("Holy Names Academy", "General Office", "General Contact", "admissions@holynames-sea.org", "(206) 323-4272", "728 21st Ave E, Seattle, WA 98112", "Catholic High School — AFROTC Recruitment Contact", 47.6262, -122.3065, True),
    ("O’Dea High School", "General Office", "General Contact", "info@odea.org", "(206) 622-6596", "802 Terry Ave, Seattle, WA 98104", "Catholic High School — AFROTC Recruitment Contact", 47.6072, -122.3270, True),
    ("Eastside Catholic HS", "General Office", "General Contact", "admissions@eastsidecatholic.org", "(425) 295-3000", "232 228th Ave SE, Sammamish, WA 98074", "Catholic High School — AFROTC Recruitment Contact", 47.5862, -122.0355, True),
    ("Jesuit High School", "Admissions Office", "Contact", "admissions@jesuitportland.org", "(503) 291-5423", "9000 SW Beaverton Hillsdale Hwy, Portland, OR 97225", "Jesuit High School — AFROTC Recruitment Contact", 45.4917, -122.7530, True),
    ("Central Catholic HS", "General Office", "General Contact", "admissions@centralcatholichigh.org", "(503) 235-3138", "2401 SE Stark St, Portland, OR 97214", "Catholic High School — AFROTC Recruitment Contact", 45.5192, -122.6392, True),
    ("St. Mary’s Academy", "General Office", "General Contact", "info@smapdx.org", "(503) 228-8306", "1615 SW 5th Ave, Portland, OR 97201", "Catholic High School — AFROTC Recruitment Contact", 45.5128, -122.6810, True),
    ("Valley Catholic HS", "General Office", "General Contact", "admissions@valleycatholic.org", "(503) 644-3745", "4275 SW 148th Ave, Beaverton, OR 97007", "Catholic High School — AFROTC Recruitment Contact", 45.4788, -122.8130, True),
    ("De La Salle North Catholic HS", "General Office", "General Contact", "admissions@delasallenorth.org", "(503) 285-9385", "7528 N Fenwick Ave, Portland, OR 97217", "Catholic High School — AFROTC Recruitment Contact", 45.5822, -122.6720, True),
    ("La Salle Catholic College Prep", "General Office", "General Contact", "admissions@lsprep.org", "(503) 659-4155", "11999 SE Fuller Rd, Milwaukie, OR 97222", "Catholic Preparatory School — AFROTC Recruitment Contact", 45.4468, -122.5588, True),
    ("St. Elizabeth Ann Seton Catholic HS", "General Office", "General Contact", "info@setonhigh.org", "(360) 258-1932", "Vancouver, WA 98684", "Catholic High School — AFROTC Recruitment Contact", 45.6795, -122.5090, True),
]

# ---------------------------------------------------------------------------
# REAL cadets — the actual roster read from the production Neon DB.
# (first, last, email, phone, major, grad_year, rank, status, gpa, unenrollment_date)
# ---------------------------------------------------------------------------
CADETS = [
    ("Aviv", "Brill", "brill28@up.edu", "5108153687", "Biochemistry", 2028, "C/3C", CadetStatus.ACTIVE, 3.8, None),
    ("John", "Smith", "john.smith@up.edu", "555-0101", "Computer Science", 2026, "C/2d Lt", CadetStatus.GRADUATED, 3.8, None),
    ("Sarah", "Johnson", "sarah.johnson@up.edu", "555-0102", "Engineering", 2026, "C/2d Lt", CadetStatus.GRADUATED, 3.9, None),
    ("Mike", "Davis", "mike.davis@up.edu", "555-0103", "Physics", 2026, "C/2d Lt", CadetStatus.GRADUATED, 3.7, None),
    ("Emily", "Wilson", "emily.wilson@up.edu", "555-0201", "Biology", 2027, "C/1st Lt", CadetStatus.ACTIVE, 3.6, None),
    ("David", "Brown", "david.brown@up.edu", "555-0202", "Chemistry", 2027, "C/1st Lt", CadetStatus.ACTIVE, 3.5, None),
    ("Lisa", "Garcia", "lisa.garcia@up.edu", "555-0203", "Mathematics", 2027, "C/1st Lt", CadetStatus.INACTIVE, 3.2, date(2024, 9, 15)),
    ("Tom", "Miller", "tom.miller@up.edu", "555-0204", "Psychology", 2027, "C/1st Lt", CadetStatus.INACTIVE, 2.8, date(2024, 12, 10)),
    ("Jessica", "Taylor", "jessica.taylor@up.edu", "555-0301", "Business", 2028, "C/Capt", CadetStatus.ACTIVE, 3.7, None),
    ("Ryan", "Anderson", "ryan.anderson@up.edu", "555-0302", "Economics", 2028, "C/Capt", CadetStatus.ACTIVE, 3.4, None),
    ("Amanda", "Thomas", "amanda.thomas@up.edu", "555-0303", "Political Science", 2028, "C/Capt", CadetStatus.ACTIVE, 3.8, None),
    ("Chris", "Jackson", "chris.jackson@up.edu", "555-0304", "History", 2028, "C/Capt", CadetStatus.INACTIVE, 2.9, date(2024, 6, 15)),
    ("Rachel", "White", "rachel.white@up.edu", "555-0305", "English", 2028, "C/Capt", CadetStatus.INACTIVE, 3.1, date(2024, 6, 15)),
    ("Kevin", "Harris", "kevin.harris@up.edu", "555-0401", "Computer Engineering", 2029, "C/3C", CadetStatus.ACTIVE, 3.9, None),
    ("Nicole", "Clark", "nicole.clark@up.edu", "555-0402", "Mechanical Engineering", 2029, "C/3C", CadetStatus.ACTIVE, 3.6, None),
    ("Alex", "Lewis", "alex.lewis@up.edu", "555-0403", "Electrical Engineering", 2029, "C/3C", CadetStatus.ACTIVE, 3.7, None),
    ("Megan", "Robinson", "megan.robinson@up.edu", "555-0404", "Civil Engineering", 2029, "C/3C", CadetStatus.ACTIVE, 3.5, None),
    ("Daniel", "Walker", "daniel.walker@up.edu", "555-0405", "Aerospace Engineering", 2029, "C/3C", CadetStatus.ACTIVE, 3.8, None),
    ("Sophie", "Hall", "sophie.hall@up.edu", "555-0406", "Chemical Engineering", 2029, "C/3C", CadetStatus.ACTIVE, 2.7, None),
]

# ---------------------------------------------------------------------------
# DEMO recruits — production holds zero potential-recruits, but the funnel + trend
# analytics are the app's core feature, so we seed a plausible pipeline anchored to
# the REAL schools above. Each recruit's stage path is backdated so the trend renders.
# (first, last, real_school, path_of_stages, weeks_ago)
# ---------------------------------------------------------------------------
RECRUITS = [
    ("Marcus", "Ellison", "Seattle Preparatory School", ["lead", "contacted", "applied", "enrolled", "commissioned"], 11),
    ("Sofia", "Reyes", "Jesuit High School", ["lead", "contacted", "applied", "enrolled", "commissioned"], 10),
    ("Jordan", "Pak", "Bishop Blanchet HS", ["lead", "contacted", "applied", "enrolled"], 9),
    ("Ava", "Thompson", "Central Catholic HS", ["lead", "contacted", "applied", "enrolled"], 8),
    ("Liam", "Osei", "Holy Names Academy", ["lead", "contacted", "applied", "enrolled"], 8),
    ("Grace", "Nakamura", "St. Mary’s Academy", ["lead", "contacted", "applied"], 6),
    ("Noah", "Delgado", "O’Dea High School", ["lead", "contacted", "applied"], 6),
    ("Maya", "Brennan", "Eastside Catholic HS", ["lead", "contacted", "applied"], 5),
    ("Ethan", "Kowalski", "Valley Catholic HS", ["lead", "contacted"], 4),
    ("Isabella", "Cho", "Cristo Rey Jesuit Seattle", ["lead", "contacted"], 4),
    ("Caleb", "Ferreira", "De La Salle North Catholic HS", ["lead", "contacted"], 3),
    ("Zoe", "Abara", "La Salle Catholic College Prep", ["lead", "contacted"], 3),
    ("Dylan", "Meyer", "Bishop Blanchet HS", ["lead"], 2),
    ("Harper", "Singh", "Central Catholic HS", ["lead"], 2),
    ("Owen", "Vasquez", "Seattle Preparatory School", ["lead"], 1),
    ("Nora", "Hassan", "St. Elizabeth Ann Seton Catholic HS", ["lead"], 1),
    ("Leo", "Whitfield", "Holy Names Academy", ["lead"], 0),
    ("Priya", "Raman", "Jesuit High School", ["lead", "contacted", "declined"], 7),
]

# ---------------------------------------------------------------------------
# DEMO events — production's events are test artifacts, so we seed realistic outreach
# tied to the REAL schools (FK + coords resolved from the seeded contacts).
# (title, event_type, university_name, days_from_now, status, attendees)
# ---------------------------------------------------------------------------
EVENTS = [
    ("Seattle Prep Info Session", "info_session", "Seattle Preparatory School", 12, EventStatus.SCHEDULED, 0),
    ("Jesuit Portland College & Career Fair", "college_fair", "Jesuit High School", 5, EventStatus.SCHEDULED, 0),
    ("Bishop Blanchet Leadership Night", "info_session", "Bishop Blanchet HS", -8, EventStatus.COMPLETED, 34),
    ("Central Catholic STEM Expo", "tabling", "Central Catholic HS", -3, EventStatus.COMPLETED, 52),
    ("Eastside Catholic ROTC Tabling", "tabling", "Eastside Catholic HS", 20, EventStatus.SCHEDULED, 0),
]


def reset_tables(db) -> None:
    db.execute(delete(RecruitStageEvent))
    db.execute(delete(FollowUp))
    db.execute(delete(PotentialRecruit))
    db.execute(delete(Cadet))
    db.execute(delete(RecruitmentEvent))  # FK -> university_contact, delete first
    db.execute(delete(UniversityContact))
    db.commit()


def ensure_admin(db) -> User:
    from app.models.enums import UserRole

    admin = db.scalar(select(User).where(User.username == ADMIN_USERNAME))
    if admin is None:
        admin = User(
            username=ADMIN_USERNAME,
            email="admin@det695.local",
            first_name="Detachment",
            last_name="Admin",
            role=UserRole.ADMIN.value,
            is_active=True,
            secret_question="Set after first login",
            secret_answer_hash=hash_password("unset"),
        )
        db.add(admin)
    # Prototype: known password, no forced change so we log straight into the app.
    admin.password_hash = hash_password(ADMIN_PASSWORD)
    admin.force_password_change = False
    db.commit()
    db.refresh(admin)
    return admin


def seed_contacts(db) -> None:
    for name, cname, title, email, phone, address, notes, lat, lng, active in CONTACTS:
        db.add(
            UniversityContact(
                university_name=name,
                contact_name=cname,
                contact_title=title,
                email=email,
                phone=phone,
                address=address,
                notes=notes,
                is_active=active,
                latitude=lat,
                longitude=lng,
            )
        )
    db.commit()


def seed_events(db) -> None:
    """Seed outreach events, wiring each to its real school (FK + coords)."""
    by_name = {c.university_name: c for c in db.scalars(select(UniversityContact)).all()}
    today = now_utc().date()
    for title, etype, uni_name, days, status, attendees in EVENTS:
        school = by_name.get(uni_name)
        db.add(
            RecruitmentEvent(
                title=title,
                description=None,
                event_date=today + timedelta(days=days),
                start_time=time(18, 0) if etype == "info_session" else time(10, 0),
                location=school.address if school else None,
                university_id=school.id if school else None,
                event_type=etype,
                status=status.value,
                attendees_count=attendees,
                latitude=school.latitude if school else None,
                longitude=school.longitude if school else None,
            )
        )
    db.commit()


def seed_recruits(db, admin: User) -> None:
    now = now_utc()
    for first, last, school, path, weeks_ago in RECRUITS:
        created = now - timedelta(weeks=weeks_ago)
        recruit = PotentialRecruit(
            first_name=first,
            last_name=last,
            email=f"{first.lower()}.{last.lower()}@example.com",
            current_school=school,
            school_type=SchoolType.HIGH_SCHOOL.value,
            stage=path[-1],
            gpa=round(3.2 + (hash((first, last)) % 70) / 100, 2),
        )
        db.add(recruit)
        db.flush()  # assign id
        recruit.created_at = created

        # One event per transition, spaced ~1.5 weeks apart from created date.
        prev = None
        for idx, stage in enumerate(path):
            changed = created + timedelta(days=int(idx * 11))
            db.add(
                RecruitStageEvent(
                    recruit_id=recruit.id,
                    from_stage=prev,
                    to_stage=stage,
                    changed_at=changed,
                    changed_by_id=admin.id,
                    note="Seeded demo transition",
                )
            )
            prev = stage
    db.commit()


def seed_cadets(db) -> None:
    for first, last, email, phone, major, year, rank, status, gpa, unenroll in CADETS:
        db.add(
            Cadet(
                first_name=first,
                last_name=last,
                email=email,
                phone=phone,
                major=major,
                graduation_year=year,
                cadet_rank=rank,
                status=status.value,
                gpa=gpa,
                unenrollment_date=unenroll,
            )
        )
    db.commit()


def seed_followups(db, admin: User) -> None:
    now = now_utc()
    recruits = db.scalars(
        select(PotentialRecruit).where(PotentialRecruit.stage.in_(["contacted", "applied"]))
    ).all()
    for offset, recruit in enumerate(recruits[:5]):
        db.add(
            FollowUp(
                note=f"Check in with {recruit.full_name} about next steps.",
                due_date=now + timedelta(days=offset - 1),
                assignee_id=admin.id,
                created_by_id=admin.id,
                recruit_id=recruit.id,
            )
        )
    db.commit()


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        reset_tables(db)
        admin = ensure_admin(db)
        seed_contacts(db)
        seed_events(db)
        seed_recruits(db, admin)
        seed_cadets(db)
        seed_followups(db, admin)

        n_contacts = len(db.scalars(select(UniversityContact.id)).all())
        n_events = len(db.scalars(select(RecruitmentEvent.id)).all())
        n_recruits = len(db.scalars(select(PotentialRecruit.id)).all())
        n_transitions = len(db.scalars(select(RecruitStageEvent.id)).all())
        n_cadets = len(db.scalars(select(Cadet.id)).all())
        n_follow = len(db.scalars(select(FollowUp.id)).all())
        print(
            f"Seeded: {n_contacts} real contacts, {n_events} events, {n_recruits} recruits, "
            f"{n_transitions} stage events, {n_cadets} real cadets, {n_follow} follow-ups."
        )
        print(f"Login: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
