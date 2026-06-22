from httpx import AsyncClient


async def test_full_crud_flow_room_to_book_through_real_api_and_db(client: AsyncClient) -> None:
	"""Exercises the full stack the unit suite cannot: endpoint -> use case ->
	repository -> real Postgres, across the whole location hierarchy down to
	an owned book, asserting on the actual HTTP responses."""
	room_resp = await client.post("/v1/rooms/", json={"name": "Living room"})
	assert room_resp.status_code == 201
	room_id = room_resp.json()["id"]

	bookcase_resp = await client.post("/v1/bookcases/", json={"room_id": room_id, "name": "Shelf A"})
	assert bookcase_resp.status_code == 201
	bookcase_id = bookcase_resp.json()["id"]

	section_resp = await client.post("/v1/sections/", json={"bookcase_id": bookcase_id, "section_index": 0})
	assert section_resp.status_code == 201
	section_id = section_resp.json()["id"]

	shelf_resp = await client.post("/v1/shelves/", json={"section_id": section_id, "shelf_index": 0})
	assert shelf_resp.status_code == 201
	shelf_id = shelf_resp.json()["id"]

	book_resp = await client.post(
		"/v1/books/",
		json={
			"title": "Dune",
			"main_author": "Frank Herbert",
			"room_id": room_id,
			"bookcase_id": bookcase_id,
			"section_id": section_id,
			"shelf_id": shelf_id,
			"reading_status": "to_read",
		},
	)
	assert book_resp.status_code == 201
	book = book_resp.json()
	assert book["shelf_id"] == shelf_id
	assert book["reading_status"] == "to_read"

	get_resp = await client.get(f"/v1/books/{book['id']}")
	assert get_resp.status_code == 200
	assert get_resp.json()["id"] == book["id"]

	list_resp = await client.get("/v1/books/")
	assert list_resp.status_code == 200
	assert any(b["id"] == book["id"] for b in list_resp.json())

	status_resp = await client.post(f"/v1/books/{book['id']}/reading-status", params={"reading_status": "reading"})
	assert status_resp.status_code == 200
	assert status_resp.json()["reading_status"] == "reading"

	delete_resp = await client.delete(f"/v1/books/{book['id']}")
	assert delete_resp.status_code == 204

	missing_resp = await client.get(f"/v1/books/{book['id']}")
	assert missing_resp.status_code == 404
