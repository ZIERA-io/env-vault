from datetime import datetime, timedelta


def test_cleanup_expired_revoked_tokens(client):
    from database import SessionLocal
    from models import RevokedToken
    from auth import cleanup_expired_revoked_tokens

    db = SessionLocal()
    try:
        db.add(RevokedToken(jti="old", revoked_at=datetime.utcnow() - timedelta(days=8)))
        db.add(RevokedToken(jti="recent", revoked_at=datetime.utcnow() - timedelta(days=1)))
        db.commit()

        deleted = cleanup_expired_revoked_tokens(db)
        assert deleted == 1
        remaining = [t.jti for t in db.query(RevokedToken).all()]
        assert remaining == ["recent"]
    finally:
        db.close()
