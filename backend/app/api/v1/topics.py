from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import RequestAuthContext, require_workspace_admin, require_workspace_member
from app.core.database import DatabaseConfigurationError
from app.core.errors import ApiError
from app.db.session import get_session
from app.models.topics import TOPIC_STATUS_VALUES
from app.schemas.topics import (
    AddTagRequest,
    AttachDocumentRequest,
    TopicCreate,
    TopicDetail,
    TopicListResponse,
    TopicMergeRequest,
    TopicMergeResponse,
    TopicUpdate,
)
from app.services.topics.merge_service import TopicMergeService
from app.services.topics.service import TopicService


router = APIRouter(prefix="/topics", tags=["topics"])


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

def get_db_session() -> Iterator[Session]:
    try:
        yield from get_session()
    except DatabaseConfigurationError as exc:
        raise ApiError(message=str(exc)) from exc


def get_topic_service(session: Annotated[Session, Depends(get_db_session)]) -> TopicService:
    return TopicService(session)


def get_merge_service(session: Annotated[Session, Depends(get_db_session)]) -> TopicMergeService:
    return TopicMergeService(session)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=TopicListResponse)
def list_topics(
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[TopicService, Depends(get_topic_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    tag_id: Annotated[str | None, Query()] = None,
    order_by: Annotated[str, Query()] = "created_at_desc",
) -> TopicListResponse:
    if status_filter is not None and status_filter not in TOPIC_STATUS_VALUES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status. Allowed: {TOPIC_STATUS_VALUES}",
        )
    _validate_order_by(order_by)
    return service.list_topics(
        workspace_id=auth.workspace_id,
        limit=limit,
        offset=offset,
        status=status_filter,
        tag_id=tag_id,
        order_by=order_by,
    )


@router.post("", response_model=TopicDetail, status_code=status.HTTP_201_CREATED)
def create_topic(
    request: TopicCreate,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[TopicService, Depends(get_topic_service)],
) -> TopicDetail:
    return service.create_topic(
        workspace_id=auth.workspace_id,
        user_id=auth.user_id,
        request=request,
    )


@router.get("/{topic_id}", response_model=TopicDetail)
def get_topic(
    topic_id: str,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[TopicService, Depends(get_topic_service)],
) -> TopicDetail:
    return service.get_topic(topic_id, workspace_id=auth.workspace_id)


@router.put("/{topic_id}", response_model=TopicDetail)
def update_topic(
    topic_id: str,
    request: TopicUpdate,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[TopicService, Depends(get_topic_service)],
) -> TopicDetail:
    return service.update_topic(topic_id, workspace_id=auth.workspace_id, request=request)


@router.delete("/{topic_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
def delete_topic(
    topic_id: str,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[TopicService, Depends(get_topic_service)],
) -> Response:
    service.delete_topic(topic_id, workspace_id=auth.workspace_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{topic_id}/approve", response_model=TopicDetail)
def approve_topic(
    topic_id: str,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_admin)],
    service: Annotated[TopicService, Depends(get_topic_service)],
) -> TopicDetail:
    return service.approve_topic(topic_id, workspace_id=auth.workspace_id, user_id=auth.user_id)


@router.post("/{topic_id}/archive", response_model=TopicDetail)
def archive_topic(
    topic_id: str,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[TopicService, Depends(get_topic_service)],
) -> TopicDetail:
    return service.archive_topic(topic_id, workspace_id=auth.workspace_id)


@router.post("/{topic_id}/documents", response_model=TopicDetail, status_code=status.HTTP_201_CREATED)
def attach_document(
    topic_id: str,
    request: AttachDocumentRequest,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[TopicService, Depends(get_topic_service)],
) -> TopicDetail:
    return service.attach_document(topic_id, workspace_id=auth.workspace_id, request=request)


@router.delete("/{topic_id}/documents/{document_id}", response_model=TopicDetail)
def detach_document(
    topic_id: str,
    document_id: str,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[TopicService, Depends(get_topic_service)],
) -> TopicDetail:
    return service.detach_document(topic_id, document_id, workspace_id=auth.workspace_id)


@router.post("/{topic_id}/tags", response_model=TopicDetail, status_code=status.HTTP_201_CREATED)
def add_tag(
    topic_id: str,
    request: AddTagRequest,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[TopicService, Depends(get_topic_service)],
) -> TopicDetail:
    return service.add_tag(topic_id, workspace_id=auth.workspace_id, tag_id=request.tag_id)


@router.delete("/{topic_id}/tags/{tag_id}", response_model=TopicDetail)
def remove_tag(
    topic_id: str,
    tag_id: str,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[TopicService, Depends(get_topic_service)],
) -> TopicDetail:
    return service.remove_tag(topic_id, tag_id, workspace_id=auth.workspace_id)


@router.post("/{topic_id}/merge", response_model=TopicMergeResponse)
def merge_topic(
    topic_id: str,
    request: TopicMergeRequest,
    auth: Annotated[RequestAuthContext, Depends(require_workspace_member)],
    service: Annotated[TopicService, Depends(get_topic_service)],
    merge_service: Annotated[TopicMergeService, Depends(get_merge_service)],
) -> TopicMergeResponse:
    # Verify topic exists in workspace before merge
    service.get_topic(topic_id, workspace_id=auth.workspace_id)
    return merge_service.merge(workspace_id=auth.workspace_id, request=request)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_ALLOWED_ORDER_BY = {"created_at_desc", "created_at_asc", "title_asc", "title_desc"}


def _validate_order_by(value: str) -> None:
    if value not in _ALLOWED_ORDER_BY:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid order_by. Allowed: {sorted(_ALLOWED_ORDER_BY)}",
        )
