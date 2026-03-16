from sqlalchemy import text
from sqlalchemy.orm import Session


def hard_delete_comment_thread(db: Session, comment_id: int) -> None:
    db.execute(
        text(
            """
            DELETE FROM likes
            WHERE target_type = 3
              AND target_id IN (
                SELECT id FROM comments WHERE id = :cid OR root_id = :cid OR parent_id = :cid
              )
            """
        ),
        {"cid": comment_id},
    )

    db.execute(
        text(
            """
            DELETE FROM comments
            WHERE id = :cid OR root_id = :cid OR parent_id = :cid
            """
        ),
        {"cid": comment_id},
    )


def hard_delete_answer(db: Session, answer_id: int) -> None:
    db.execute(
        text(
            """
            DELETE FROM likes
            WHERE target_type = 3
              AND target_id IN (SELECT id FROM comments WHERE answer_id = :aid)
            """
        ),
        {"aid": answer_id},
    )

    db.execute(text("DELETE FROM comments WHERE answer_id = :aid"), {"aid": answer_id})
    db.execute(text("DELETE FROM likes WHERE target_type = 2 AND target_id = :aid"), {"aid": answer_id})
    db.execute(text("DELETE FROM collection_items WHERE answer_id = :aid"), {"aid": answer_id})
    db.execute(text("DELETE FROM answers WHERE id = :aid"), {"aid": answer_id})


def hard_delete_question(db: Session, question_id: int) -> None:
    db.execute(
        text(
            """
            DELETE FROM likes
            WHERE target_type = 3
              AND target_id IN (
                SELECT c.id
                FROM comments c
                JOIN answers a ON c.answer_id = a.id
                WHERE a.question_id = :qid
              )
            """
        ),
        {"qid": question_id},
    )

    db.execute(
        text(
            """
            DELETE FROM comments
            WHERE answer_id IN (SELECT id FROM answers WHERE question_id = :qid)
            """
        ),
        {"qid": question_id},
    )

    db.execute(
        text(
            """
            DELETE FROM likes
            WHERE target_type = 2
              AND target_id IN (SELECT id FROM answers WHERE question_id = :qid)
            """
        ),
        {"qid": question_id},
    )

    db.execute(
        text(
            """
            DELETE FROM collection_items
            WHERE answer_id IN (SELECT id FROM answers WHERE question_id = :qid)
            """
        ),
        {"qid": question_id},
    )

    db.execute(text("DELETE FROM answers WHERE question_id = :qid"), {"qid": question_id})
    db.execute(text("DELETE FROM likes WHERE target_type = 1 AND target_id = :qid"), {"qid": question_id})
    db.execute(text("DELETE FROM follows WHERE target_type = 1 AND target_id = :qid"), {"qid": question_id})
    db.execute(text("DELETE FROM question_tags WHERE question_id = :qid"), {"qid": question_id})
    db.execute(text("DELETE FROM questions WHERE id = :qid"), {"qid": question_id})


def hard_delete_user(db: Session, user_id: int) -> None:
    db.execute(text("DELETE FROM follows WHERE user_id = :uid OR (target_type = 4 AND target_id = :uid)"), {"uid": user_id})
    db.execute(text("DELETE FROM likes WHERE user_id = :uid"), {"uid": user_id})

    db.execute(
        text(
            """
            DELETE FROM likes
            WHERE target_type = 3
              AND target_id IN (SELECT id FROM comments WHERE user_id = :uid)
            """
        ),
        {"uid": user_id},
    )

    db.execute(
        text(
            """
            DELETE FROM likes
            WHERE target_type = 3
              AND target_id IN (
                SELECT c.id
                FROM comments c
                JOIN answers a ON c.answer_id = a.id
                WHERE a.user_id = :uid
              )
            """
        ),
        {"uid": user_id},
    )

    db.execute(
        text(
            """
            DELETE FROM comments
            WHERE answer_id IN (SELECT id FROM answers WHERE user_id = :uid)
            """
        ),
        {"uid": user_id},
    )
    db.execute(text("DELETE FROM comments WHERE user_id = :uid"), {"uid": user_id})

    db.execute(
        text(
            """
            DELETE FROM collection_items
            WHERE answer_id IN (SELECT id FROM answers WHERE user_id = :uid)
            """
        ),
        {"uid": user_id},
    )

    db.execute(
        text(
            """
            DELETE FROM likes
            WHERE target_type = 2
              AND target_id IN (SELECT id FROM answers WHERE user_id = :uid)
            """
        ),
        {"uid": user_id},
    )
    db.execute(text("DELETE FROM answers WHERE user_id = :uid"), {"uid": user_id})

    db.execute(
        text(
            """
            DELETE FROM likes
            WHERE target_type = 3
              AND target_id IN (
                SELECT c.id
                FROM comments c
                JOIN answers a ON c.answer_id = a.id
                JOIN questions q ON a.question_id = q.id
                WHERE q.user_id = :uid
              )
            """
        ),
        {"uid": user_id},
    )

    db.execute(
        text(
            """
            DELETE FROM comments
            WHERE answer_id IN (
              SELECT a.id FROM answers a JOIN questions q ON a.question_id = q.id WHERE q.user_id = :uid
            )
            """
        ),
        {"uid": user_id},
    )

    db.execute(
        text(
            """
            DELETE FROM likes
            WHERE target_type = 2
              AND target_id IN (
                SELECT a.id FROM answers a JOIN questions q ON a.question_id = q.id WHERE q.user_id = :uid
              )
            """
        ),
        {"uid": user_id},
    )

    db.execute(
        text(
            """
            DELETE FROM collection_items
            WHERE answer_id IN (
                SELECT a.id FROM answers a JOIN questions q ON a.question_id = q.id WHERE q.user_id = :uid
            )
            """
        ),
        {"uid": user_id},
    )

    db.execute(
        text(
            """
            DELETE FROM answers
            WHERE question_id IN (SELECT id FROM questions WHERE user_id = :uid)
            """
        ),
        {"uid": user_id},
    )

    db.execute(
        text(
            """
            DELETE FROM likes
            WHERE target_type = 1
              AND target_id IN (SELECT id FROM questions WHERE user_id = :uid)
            """
        ),
        {"uid": user_id},
    )

    db.execute(
        text(
            """
            DELETE FROM follows
            WHERE target_type = 1
              AND target_id IN (SELECT id FROM questions WHERE user_id = :uid)
            """
        ),
        {"uid": user_id},
    )

    db.execute(
        text(
            """
            DELETE FROM question_tags
            WHERE question_id IN (SELECT id FROM questions WHERE user_id = :uid)
            """
        ),
        {"uid": user_id},
    )

    db.execute(text("DELETE FROM questions WHERE user_id = :uid"), {"uid": user_id})

    db.execute(
        text(
            """
            DELETE FROM collection_items
            WHERE collection_id IN (SELECT id FROM collections WHERE user_id = :uid)
            """
        ),
        {"uid": user_id},
    )
    db.execute(text("DELETE FROM collections WHERE user_id = :uid"), {"uid": user_id})

    db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_id})
