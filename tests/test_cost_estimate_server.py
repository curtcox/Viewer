def test_cost_estimate_returns_float(memory_db_app, memory_client):
    # Register the cost_estimate server definition
    from database import db
    from models import Server

    with memory_db_app.app_context():
        db.session.add(
            Server(
                name="cost_estimate",
                definition=open(
                    "reference/templates/servers/definitions/cost_estimate.py", "r"
                ).read(),
                enabled=True,
            )
        )
        db.session.commit()

    response = memory_client.get("/cost_estimate/echo", follow_redirects=True)
    output = response.get_data(as_text=True)

    assert response.mimetype == "text/plain"
    assert float(output) >= 0

    response_with_inputs = memory_client.get(
        "/cost_estimate/echo?input_size=100&output_size=100&execution_time=10",
        follow_redirects=True,
    )
    assert float(response_with_inputs.get_data(as_text=True)) > float(output)

