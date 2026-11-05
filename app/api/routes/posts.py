from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.comment import Comment
from app.models.post import Post
from app.models.reaction import Reaction
from app.models.user import User
from app.schemas.post import CommentCreate, CommentRead, PostCreate, PostRead, PostUpdate

router = APIRouter(prefix="/posts", tags=["posts"])


def serialize_post(post: Post, db: Session) -> dict:
    return {
        "id": post.id, "title": post.title, "body": post.body, "author": post.author,
        "created_at": post.created_at, "updated_at": post.updated_at,
        "reaction_count": db.scalar(select(func.count(Reaction.id)).where(Reaction.post_id == post.id)) or 0,
        "comment_count": db.scalar(select(func.count(Comment.id)).where(Comment.post_id == post.id)) or 0,
    }


def get_post_or_404(post_id: int, db: Session) -> Post:
    post = db.scalar(select(Post).options(joinedload(Post.author)).where(Post.id == post_id))
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.get("", response_model=list[PostRead])
def list_posts(db: Session = Depends(get_db), limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0)):
    posts = db.scalars(select(Post).options(joinedload(Post.author)).order_by(Post.created_at.desc()).offset(offset).limit(limit)).unique().all()
    return [serialize_post(post, db) for post in posts]


@router.post("", response_model=PostRead, status_code=status.HTTP_201_CREATED)
def create_post(payload: PostCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    post = Post(**payload.model_dump(), author_id=current_user.id)
    db.add(post)
    db.commit()
    db.refresh(post)
    return serialize_post(post, db)


@router.get("/{post_id}", response_model=PostRead)
def read_post(post_id: int, db: Session = Depends(get_db)):
    return serialize_post(get_post_or_404(post_id, db), db)


@router.patch("/{post_id}", response_model=PostRead)
def update_post(post_id: int, payload: PostUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    post = get_post_or_404(post_id, db)
    if post.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own posts")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(post, key, value)
    db.commit()
    db.refresh(post)
    return serialize_post(post, db)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    post = get_post_or_404(post_id, db)
    if post.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own posts")
    db.delete(post)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{post_id}/comments", response_model=list[CommentRead])
def list_comments(post_id: int, db: Session = Depends(get_db), limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0)):
    get_post_or_404(post_id, db)
    return db.scalars(select(Comment).where(Comment.post_id == post_id).order_by(Comment.created_at).offset(offset).limit(limit)).all()


@router.post("/{post_id}/comments", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
def create_comment(post_id: int, payload: CommentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    get_post_or_404(post_id, db)
    comment = Comment(post_id=post_id, author_id=current_user.id, body=payload.body)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.put("/{post_id}/reaction", status_code=status.HTTP_204_NO_CONTENT)
def add_reaction(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    get_post_or_404(post_id, db)
    existing = db.scalar(select(Reaction).where(Reaction.post_id == post_id, Reaction.user_id == current_user.id))
    if existing is None:
        db.add(Reaction(post_id=post_id, user_id=current_user.id))
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{post_id}/reaction", status_code=status.HTTP_204_NO_CONTENT)
def remove_reaction(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    get_post_or_404(post_id, db)
    reaction = db.scalar(select(Reaction).where(Reaction.post_id == post_id, Reaction.user_id == current_user.id))
    if reaction is not None:
        db.delete(reaction)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
