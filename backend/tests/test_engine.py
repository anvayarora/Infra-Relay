from app.engine import execute
from app.extensions import db
from app.models import Execution, UITransaction, Workflow


def test_execution_pauses_and_resumes(app):
    graph = {
        "nodes": [
            {"id": "start", "type": "trigger.manual", "position": {"x": 0, "y": 0}, "data": {"settings": {}}},
            {
                "id": "approval",
                "type": "hitl.approval",
                "position": {"x": 200, "y": 0},
                "data": {"settings": {"title": "Approve", "notify": False}},
            },
            {
                "id": "done",
                "type": "data.set",
                "position": {"x": 400, "y": 0},
                "data": {"settings": {"values": {"status": "approved"}}},
            },
        ],
        "edges": [
            {"id": "e1", "source": "start", "target": "approval"},
            {"id": "e2", "source": "approval", "sourceHandle": "approved", "target": "done"},
        ],
    }
    with app.app_context():
        workflow = Workflow(
            name="Approval test",
            description="",
            status="active",
            graph_json=graph,
            settings_json={},
            created_by="admin@test.local",
        )
        db.session.add(workflow)
        db.session.flush()
        execution = Execution(
            workflow_id=workflow.id,
            input_json={},
            context_json={"input": {}, "nodes": {}, "responses": {}, "completed": [], "queue": []},
        )
        db.session.add(execution)
        db.session.commit()

        execute(execution.id)
        db.session.refresh(execution)
        assert execution.status == "waiting"

        transaction = UITransaction.query.filter_by(execution_id=execution.id).one()
        transaction.status = "responded"
        transaction.response_json = {"action": "approve", "values": {}}
        context = execution.context_json
        context["responses"]["approval"] = transaction.response_json
        execution.context_json = context
        db.session.commit()

        execute(execution.id)
        db.session.refresh(execution)
        assert execution.status == "completed"
        assert execution.output_json == {"status": "approved"}
