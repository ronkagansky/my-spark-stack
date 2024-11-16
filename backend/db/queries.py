from typing import Optional

from sqlalchemy.orm import joinedload
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Chat, User


def get_chat_for_user(db: Session, chat_id: int, current_user: User) -> Optional[Chat]:
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.user_id == current_user.id)
        .options(joinedload(Chat.messages), joinedload(Chat.project))
        .first()
    )
    return chat
