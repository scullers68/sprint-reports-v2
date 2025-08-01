"""
Standardized response formatting for Sprint Reports API.

Provides consistent response structures and HATEOAS links.
"""

from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode
from pydantic import BaseModel
from fastapi import Request


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginationLinks(BaseModel):
    """HATEOAS pagination links."""
    self: str
    first: str
    last: str
    next: Optional[str] = None
    prev: Optional[str] = None


class APIResponse(BaseModel):
    """Standardized API response structure."""
    data: Any
    meta: Optional[Dict[str, Any]] = None
    links: Optional[Dict[str, str]] = None
    message: Optional[str] = None


class ListResponse(BaseModel):
    """Response structure for list endpoints."""
    data: List[Any]
    meta: PaginationMeta
    links: PaginationLinks


def create_success_response(
    data: Any,
    message: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    links: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Create a standardized success response."""
    response = {"data": data}
    
    if message:
        response["message"] = message
    if meta:
        response["meta"] = meta
    if links:
        response["links"] = links
    
    return response


def create_list_response(
    items: List[Any],
    total: int,
    page: int,
    per_page: int,
    request: Request,
    additional_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a standardized paginated list response."""
    total_pages = (total + per_page - 1) // per_page
    has_next = page < total_pages
    has_prev = page > 1
    
    # Build base URL
    base_url = str(request.url).split('?')[0]
    base_params = dict(request.query_params)
    base_params.update(additional_params or {})
    
    # Create pagination metadata
    meta = PaginationMeta(
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev
    )
    
    # Create pagination links
    def build_url(page_num: int) -> str:
        params = base_params.copy()
        params['page'] = page_num
        params['per_page'] = per_page
        return f"{base_url}?{urlencode(params)}"
    
    links = PaginationLinks(
        self=build_url(page),
        first=build_url(1),
        last=build_url(total_pages),
        next=build_url(page + 1) if has_next else None,
        prev=build_url(page - 1) if has_prev else None
    )
    
    return {
        "data": items,
        "meta": meta.dict(),
        "links": links.dict(exclude_none=True)
    }


def create_resource_response(
    resource: Any,
    request: Request,
    resource_name: str,
    resource_id: Union[int, str]
) -> Dict[str, Any]:
    """Create a response for a single resource with HATEOAS links."""
    # Build self link
    self_link = f"{request.base_url}api/v1/{resource_name}/{resource_id}"
    
    # Build collection link
    collection_link = f"{request.base_url}api/v1/{resource_name}"
    
    links = {
        "self": self_link,
        "collection": collection_link
    }
    
    return create_success_response(
        data=resource,
        links=links
    )


def create_created_response(
    resource: Any,
    request: Request,
    resource_name: str,
    resource_id: Union[int, str],
    message: Optional[str] = None
) -> Dict[str, Any]:
    """Create a response for newly created resources."""
    default_message = f"{resource_name.capitalize()} created successfully"
    
    return create_resource_response(
        resource=resource,
        request=request,
        resource_name=resource_name,
        resource_id=resource_id
    ) | {"message": message or default_message}


def create_updated_response(
    resource: Any,
    request: Request,
    resource_name: str,
    resource_id: Union[int, str],
    message: Optional[str] = None
) -> Dict[str, Any]:
    """Create a response for updated resources."""
    default_message = f"{resource_name.capitalize()} updated successfully"
    
    return create_resource_response(
        resource=resource,
        request=request,
        resource_name=resource_name,
        resource_id=resource_id
    ) | {"message": message or default_message}


def create_deleted_response(
    resource_name: str,
    resource_id: Union[int, str],
    message: Optional[str] = None
) -> Dict[str, Any]:
    """Create a response for deleted resources."""
    default_message = f"{resource_name.capitalize()} deleted successfully"
    
    return {
        "message": message or default_message,
        "data": {
            "resource_type": resource_name,
            "resource_id": str(resource_id),
            "deleted": True
        }
    }


def create_async_response(
    task_id: str,
    message: str = "Task started successfully",
    estimated_duration: Optional[int] = None
) -> Dict[str, Any]:
    """Create a response for asynchronous operations."""
    data = {
        "task_id": task_id,
        "status": "pending",
        "message": message
    }
    
    if estimated_duration:
        data["estimated_duration_seconds"] = estimated_duration
    
    return create_success_response(data=data)


class ResponseBuilder:
    """Helper class for building consistent API responses."""
    
    def __init__(self, request: Request):
        self.request = request
    
    def success(
        self,
        data: Any,
        message: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build a success response."""
        return create_success_response(data, message, meta)
    
    def list(
        self,
        items: List[Any],
        total: int,
        page: int = 1,
        per_page: int = 25,
        additional_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build a paginated list response."""
        return create_list_response(
            items, total, page, per_page, self.request, additional_params
        )
    
    def resource(
        self,
        resource: Any,
        resource_name: str,
        resource_id: Union[int, str]
    ) -> Dict[str, Any]:
        """Build a single resource response."""
        return create_resource_response(
            resource, self.request, resource_name, resource_id
        )
    
    def created(
        self,
        resource: Any,
        resource_name: str,
        resource_id: Union[int, str],
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build a created resource response."""
        return create_created_response(
            resource, self.request, resource_name, resource_id, message
        )
    
    def updated(
        self,
        resource: Any,
        resource_name: str,
        resource_id: Union[int, str],
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build an updated resource response."""
        return create_updated_response(
            resource, self.request, resource_name, resource_id, message
        )
    
    def deleted(
        self,
        resource_name: str,
        resource_id: Union[int, str],
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build a deleted resource response."""
        return create_deleted_response(resource_name, resource_id, message)
    
    def async_task(
        self,
        task_id: str,
        message: str = "Task started successfully",
        estimated_duration: Optional[int] = None
    ) -> Dict[str, Any]:
        """Build an async task response."""
        return create_async_response(task_id, message, estimated_duration)