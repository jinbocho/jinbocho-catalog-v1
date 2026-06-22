from typing import TypedDict


class OpenApiTagMetadata(TypedDict):
	name: str
	description: str


class OpenApiConfig(TypedDict):
	title: str
	description: str
	version: str
	tags: list[OpenApiTagMetadata]


OPENAPI_TAGS_METADATA: list[OpenApiTagMetadata] = [
	{"name": "rooms", "description": "Operations on rooms"},
	{"name": "bookcases", "description": "Operations on bookcases"},
	{"name": "sections", "description": "Operations on sections"},
	{"name": "shelves", "description": "Operations on shelves"},
	{"name": "records", "description": "Operations on bibliographic records"},
	{"name": "books", "description": "Operations on owned books"},
	{"name": "ingestion", "description": "ISBN lookup and metadata ingestion"},
	{"name": "export", "description": "Book export"},
	{"name": "map", "description": "Bookcase mapping"},
	{"name": "health", "description": "Health check"},
]

SECURITY_SCHEME = {
	"bearerAuth": {
		"type": "http",
		"scheme": "bearer",
		"bearerFormat": "JWT",
		"description": "JWT token from auth-service",
	}
}

OPENAPI_CONFIG: OpenApiConfig = {
	"title": "Catalog Service API",
	"description": "Manage books, locations, and catalog metadata",
	"version": "1.0.0",
	"tags": OPENAPI_TAGS_METADATA,
}
