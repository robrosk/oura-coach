import sys
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.storage.models import Base, OuraRawEvent, User
from app.storage import repo


class CleanupScopeTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.SessionLocal = sessionmaker(bind=engine)

    def test_cleanup_scoped_to_user(self):
        db = self.SessionLocal()
        try:
            user_a = User(email="a@example.com")
            user_b = User(email="b@example.com")
            db.add_all([user_a, user_b])
            db.commit()
            db.refresh(user_a)
            db.refresh(user_b)

            old_day = (date.today() - timedelta(days=10)).isoformat()
            old_time = datetime.utcnow() - timedelta(days=10)

            db.add_all(
                [
                    OuraRawEvent(
                        user_id=user_a.id,
                        endpoint="daily_sleep",
                        record_id="a1",
                        day=old_day,
                        payload="{}",
                        fetched_at=old_time,
                    ),
                    OuraRawEvent(
                        user_id=user_b.id,
                        endpoint="daily_sleep",
                        record_id="b1",
                        day=old_day,
                        payload="{}",
                        fetched_at=old_time,
                    ),
                ]
            )
            db.commit()

            result = repo.cleanup_old_events(db, max_days=1, user_id=user_a.id)
            self.assertEqual(result["total_deleted"], 1)

            remaining_a = db.execute(
                select(OuraRawEvent).where(OuraRawEvent.user_id == user_a.id)
            ).scalars().all()
            remaining_b = db.execute(
                select(OuraRawEvent).where(OuraRawEvent.user_id == user_b.id)
            ).scalars().all()

            self.assertEqual(len(remaining_a), 0)
            self.assertEqual(len(remaining_b), 1)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
