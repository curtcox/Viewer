import unittest
import uuid

from alias_definition import format_primary_alias_line
from app import app, db
from entity_references import (
    extract_references_from_bytes,
    extract_references_from_target,
    extract_references_from_text,
)
from models import CID, Alias, Server


class TestEntityReferences(unittest.TestCase):
    """Ensure entity cross-reference helpers detect aliases, servers, and CIDs."""

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False

        with self.app.app_context():
            db.create_all()

        self.user_id = self._create_user()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _create_user(self) -> str:
        return f'user-{uuid.uuid4().hex}'

    def _create_alias(self, name: str, target: str) -> str:
        with self.app.app_context():
            definition_text = format_primary_alias_line(
                'literal',
                None,
                target,
                alias_name=name,
            )
            alias = Alias(
                name=name,
                definition=definition_text,
            )
            db.session.add(alias)
            db.session.commit()
            return alias.name

    def _create_server(self, name: str, definition: str) -> str:
        with self.app.app_context():
            server = Server(name=name, definition=definition)
            db.session.add(server)
            db.session.commit()
            return server.name

    def _create_cid(self, value: str, content: bytes) -> str:
        with self.app.app_context():
            record = CID(
                path=f'/{value}',
                file_data=content,
                file_size=len(content),
            )
            db.session.add(record)
            db.session.commit()
            return value

    def test_extract_references_from_text(self):
        alias_name = self._create_alias('docs', '/docs')
        server_name = self._create_server('status', 'print("ok")')
        cid_value = self._create_cid('cidvalue123', b'data')

        text = f"Visit /{alias_name} then /servers/{server_name} and /{cid_value}"

        with self.app.test_request_context('/'):
            references = extract_references_from_text(text, self.user_id)

        alias_names = [ref['name'] for ref in references['aliases']]
        server_names = [ref['name'] for ref in references['servers']]
        cid_values = [ref['cid'] for ref in references['cids']]

        self.assertIn(alias_name, alias_names)
        self.assertIn(server_name, server_names)
        self.assertIn(cid_value, cid_values)

    def test_extract_references_from_target_detects_server_and_cid(self):
        server_name = self._create_server('reports', 'return None')
        cid_value = self._create_cid('targetcid', b'hello world')

        with self.app.test_request_context('/'):
            server_refs = extract_references_from_target(f'/servers/{server_name}', self.user_id)
            server_exec_refs = extract_references_from_target(f'/{server_name}', self.user_id)
            cid_refs = extract_references_from_target(f'/{cid_value}', self.user_id)

        self.assertEqual(server_refs['servers'][0]['name'], server_name)
        self.assertEqual(server_exec_refs['servers'][0]['name'], server_name)
        self.assertEqual(cid_refs['cids'][0]['cid'], cid_value)

    def test_extract_references_from_bytes(self):
        alias_name = self._create_alias('landing', '/landing')
        content = f"Route /{alias_name} forwards to /servers/updates then /updates".encode('utf-8')
        self._create_server('updates', 'return {}')
        self._create_cid('contentcid', content)

        with self.app.test_request_context('/'):
            references = extract_references_from_bytes(content, self.user_id)

        alias_names = [ref['name'] for ref in references['aliases']]
        server_names = [ref['name'] for ref in references['servers']]

        self.assertIn(alias_name, alias_names)
        self.assertIn('updates', server_names)


__all__ = ['TestEntityReferences']
