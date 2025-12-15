"""Unit tests for routes/crud_factory.py and routes/messages.py."""
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('SESSION_SECRET', 'test-secret-key')

from flask import Blueprint, Flask
from werkzeug.exceptions import NotFound

from routes.crud_factory import (
    EntityRouteConfig,
    create_delete_route,
    create_enabled_toggle_route,
    create_edit_route,
    create_list_route,
    create_new_route,
    create_view_route,
    register_standard_crud_routes,
)
from routes.messages import EntityMessages


class TestEntityMessages(unittest.TestCase):
    """Test the EntityMessages class."""

    def test_created_message(self):
        """Test created success message."""
        result = EntityMessages.created('server', 'api')
        self.assertEqual(result, 'Server "api" created successfully!')

    def test_updated_message(self):
        """Test updated success message."""
        result = EntityMessages.updated('variable', 'API_KEY')
        self.assertEqual(result, 'Variable "API_KEY" updated successfully!')

    def test_deleted_message(self):
        """Test deleted success message."""
        result = EntityMessages.deleted('secret', 'PASSWORD')
        self.assertEqual(result, 'Secret "PASSWORD" deleted successfully!')

    def test_already_exists_with_vowel_article(self):
        """Test already_exists message uses 'An' for vowel-starting entity types."""
        result = EntityMessages.already_exists('alias', 'home')
        self.assertEqual(result, 'An Alias named "home" already exists.')

    def test_already_exists_with_consonant_article(self):
        """Test already_exists message uses 'A' for consonant-starting entity types."""
        result = EntityMessages.already_exists('server', 'api')
        self.assertEqual(result, 'A Server named "api" already exists.')

    def test_already_exists_title_cases_entity_type(self):
        """Test that entity_type is title-cased in already_exists message."""
        result = EntityMessages.already_exists('variable', 'MY_VAR')
        self.assertEqual(result, 'A Variable named "MY_VAR" already exists.')

    def test_not_found_message(self):
        """Test not_found error message."""
        result = EntityMessages.not_found('server', 'missing')
        self.assertEqual(result, 'Server "missing" not found.')

    def test_bulk_updated_message(self):
        """Test bulk_updated success message."""
        result = EntityMessages.bulk_updated('variables', 5)
        self.assertEqual(result, 'Variables updated successfully! (5 items)')

    def test_bulk_updated_singular(self):
        """Test bulk_updated with single item."""
        result = EntityMessages.bulk_updated('secrets', 1)
        self.assertEqual(result, 'Secrets updated successfully! (1 items)')


class TestEntityRouteConfig(unittest.TestCase):
    """Test the EntityRouteConfig class."""

    def test_init_with_defaults(self):
        """Test EntityRouteConfig initialization with default values."""
        mock_entity_class = Mock()
        mock_get_by_name = Mock()
        mock_get_entities = Mock()
        mock_form_class = Mock()

        config = EntityRouteConfig(
            entity_class=mock_entity_class,
            entity_type='server',
            plural_name='servers',
            get_by_name_func=mock_get_by_name,
            get_entities_func=mock_get_entities,
            form_class=mock_form_class,
        )

        self.assertEqual(config.entity_class, mock_entity_class)
        self.assertEqual(config.entity_type, 'server')
        self.assertEqual(config.plural_name, 'servers')
        self.assertEqual(config.param_name, 'server_name')  # Default
        self.assertEqual(config.list_template, 'servers.html')  # Default
        self.assertEqual(config.view_template, 'server_view.html')  # Default
        self.assertIsNone(config.build_list_context)
        self.assertIsNone(config.build_view_context)

    def test_init_with_custom_param_name(self):
        """Test EntityRouteConfig with custom parameter name."""
        config = EntityRouteConfig(
            entity_class=Mock(),
            entity_type='alias',
            plural_name='aliases',
            get_by_name_func=Mock(),
            get_entities_func=Mock(),
            form_class=Mock(),
            param_name='custom_param',
        )

        self.assertEqual(config.param_name, 'custom_param')

    def test_init_with_custom_templates(self):
        """Test EntityRouteConfig with custom template names."""
        config = EntityRouteConfig(
            entity_class=Mock(),
            entity_type='variable',
            plural_name='variables',
            get_by_name_func=Mock(),
            get_entities_func=Mock(),
            form_class=Mock(),
            list_template='custom_list.html',
            view_template='custom_view.html',
        )

        self.assertEqual(config.list_template, 'custom_list.html')
        self.assertEqual(config.view_template, 'custom_view.html')

    def test_init_with_context_builders(self):
        """Test EntityRouteConfig with context builder functions."""
        mock_list_builder = Mock()
        mock_view_builder = Mock()

        config = EntityRouteConfig(
            entity_class=Mock(),
            entity_type='secret',
            plural_name='secrets',
            get_by_name_func=Mock(),
            get_entities_func=Mock(),
            form_class=Mock(),
            build_list_context=mock_list_builder,
            build_view_context=mock_view_builder,
        )

        self.assertEqual(config.build_list_context, mock_list_builder)
        self.assertEqual(config.build_view_context, mock_view_builder)


class TestCrudFactoryRoutes(unittest.TestCase):
    """Test CRUD factory route creation."""

    def setUp(self):
        """Set up test fixtures."""
        # Create fresh app and blueprint for each test to avoid conflicts
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True

        # Mock entity and functions
        self.mock_entity = Mock()
        self.mock_entity.name = 'test-entity'
        self.mock_entity.enabled = True
        self.mock_entity.updated_at = datetime.now(timezone.utc)

        self.mock_get_by_name = Mock(return_value=self.mock_entity)
        self.mock_get_entities = Mock(return_value=[self.mock_entity])

        self.config = EntityRouteConfig(
            entity_class=Mock,
            entity_type='test',
            plural_name='tests',
            get_by_name_func=self.mock_get_by_name,
            get_entities_func=self.mock_get_entities,
            form_class=Mock,
        )

    def _create_blueprint(self):
        """Create a fresh blueprint for each test."""
        return Blueprint('test', __name__)

    def test_create_list_route_registers_correct_url(self):
        """Test that create_list_route registers the correct URL pattern."""
        bp = self._create_blueprint()
        route_func = create_list_route(bp, self.config)

        self.assertEqual(route_func.__name__, 'tests')

        # Register blueprint with app to access routes
        self.app.register_blueprint(bp)

        # Check that the route was registered
        rules = list(self.app.url_map.iter_rules())
        self.assertTrue(any(rule.rule == '/tests' for rule in rules))

    def test_create_view_route_uses_custom_param_name(self):
        """Test that create_view_route uses the custom parameter name."""
        bp = self._create_blueprint()
        custom_config = EntityRouteConfig(
            entity_class=Mock,
            entity_type='alias',
            plural_name='aliases',
            get_by_name_func=self.mock_get_by_name,
            get_entities_func=self.mock_get_entities,
            form_class=Mock,
            param_name='alias_name',  # Custom parameter name
        )

        route_func = create_view_route(bp, custom_config)

        self.assertEqual(route_func.__name__, 'view_alias')

        # Register blueprint with app to access routes
        self.app.register_blueprint(bp)

        # Check that the route uses the custom parameter
        rules = list(self.app.url_map.iter_rules())
        alias_rule = next((r for r in rules if 'alias_name' in str(r.rule)), None)
        self.assertIsNotNone(alias_rule, "Should have route with alias_name parameter")

    def test_create_enabled_toggle_route_has_correct_name(self):
        """Test that enabled toggle route has correct function name."""
        bp = self._create_blueprint()
        route_func = create_enabled_toggle_route(bp, self.config)

        self.assertEqual(route_func.__name__, 'update_test_enabled')

    def test_create_delete_route_has_correct_name(self):
        """Test that delete route has correct function name."""
        bp = self._create_blueprint()
        route_func = create_delete_route(bp, self.config)

        self.assertEqual(route_func.__name__, 'delete_test')

    def test_register_standard_crud_routes_creates_all_routes(self):
        """Test that register_standard_crud_routes creates all 4 routes."""
        bp = self._create_blueprint()
        register_standard_crud_routes(bp, self.config)

        # Register the blueprint with the app to access routes
        self.app.register_blueprint(bp)

        # Check that all 4 routes were created
        rules = list(self.app.url_map.iter_rules())
        route_patterns = [r.rule for r in rules]

        self.assertIn('/tests', route_patterns, "Should have list route")
        self.assertTrue(
            any('test_name' in pattern for pattern in route_patterns),
            "Should have view route with parameter"
        )

    @patch('routes.crud_factory.render_template')
    @patch('routes.crud_factory.wants_structured_response', return_value=False)
    def test_list_route_calls_get_entities(self, mock_wants, mock_render):
        """Test that list route calls get_entities."""
        mock_render.return_value = 'rendered'

        bp = self._create_blueprint()
        route_func = create_list_route(bp, self.config)

        with self.app.test_request_context():
            route_func()

            self.mock_get_entities.assert_called_once()
            mock_render.assert_called_once()

    @patch('routes.crud_factory.abort')
    def test_view_route_aborts_404_when_entity_not_found(self, mock_abort):
        """Test that view route aborts with 404 when entity not found."""
        # Make abort raise NotFound exception like the real abort does
        mock_abort.side_effect = NotFound()

        config_not_found = EntityRouteConfig(
            entity_class=Mock,
            entity_type='test',
            plural_name='tests',
            get_by_name_func=Mock(return_value=None),  # Entity not found
            get_entities_func=Mock(),
            form_class=Mock,
        )

        bp = self._create_blueprint()
        route_func = create_view_route(bp, config_not_found)

        with self.app.test_request_context():
            # Should raise NotFound when entity not found
            with self.assertRaises(NotFound):
                route_func(test_name='missing')

            mock_abort.assert_called_once_with(404)

    @patch('routes.crud_factory.save_entity')
    @patch('routes.crud_factory.extract_enabled_value_from_request', return_value=False)
    def test_enabled_toggle_route_updates_entity(self, mock_extract, mock_save):
        """Test that enabled toggle route updates entity.enabled."""

        bp = self._create_blueprint()
        route_func = create_enabled_toggle_route(bp, self.config)

        with self.app.test_request_context(method='POST'):
            # Mock redirect to avoid actual redirect
            with patch('routes.crud_factory.redirect'):
                with patch('routes.crud_factory.url_for', return_value='/tests'):
                    route_func(test_name='test-entity')

                    self.assertFalse(self.mock_entity.enabled)
                    mock_save.assert_called_once_with(self.mock_entity)

    @patch('routes.crud_factory.delete_entity')
    @patch('routes.crud_factory.flash')
    def test_delete_route_deletes_entity_and_flashes_message(self, mock_flash, mock_delete):
        """Test that delete route deletes entity and shows success message."""

        bp = self._create_blueprint()
        route_func = create_delete_route(bp, self.config)

        with self.app.test_request_context(method='POST'):
            with patch('routes.crud_factory.redirect'):
                with patch('routes.crud_factory.url_for', return_value='/tests'):
                    route_func(test_name='test-entity')

                    mock_delete.assert_called_once_with(self.mock_entity)
                    mock_flash.assert_called_once()
                    # Verify the flash message contains the entity name
                    flash_call_args = mock_flash.call_args[0]
                    self.assertIn('test-entity', flash_call_args[0])


class TestCrudFactoryBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility of factory-generated routes."""

    def test_default_param_name_matches_entity_type(self):
        """Test that default parameter name matches Flask conventions."""
        test_cases = [
            ('alias', 'aliases', 'alias_name'),
            ('server', 'servers', 'server_name'),
            ('variable', 'variables', 'variable_name'),
            ('secret', 'secrets', 'secret_name'),
        ]

        for entity_type, plural_name, expected_param in test_cases:
            config = EntityRouteConfig(
                entity_class=Mock(),
                entity_type=entity_type,
                plural_name=plural_name,
                get_by_name_func=Mock(),
                get_entities_func=Mock(),
                form_class=Mock(),
            )
            self.assertEqual(
                config.param_name,
                expected_param,
                f"Parameter name for {entity_type} should be {expected_param}"
            )

    def test_custom_param_name_overrides_default(self):
        """Test that explicitly setting param_name overrides the default."""
        config = EntityRouteConfig(
            entity_class=Mock(),
            entity_type='alias',
            plural_name='aliases',
            get_by_name_func=Mock(),
            get_entities_func=Mock(),
            form_class=Mock(),
            param_name='custom_name',
        )

        self.assertEqual(config.param_name, 'custom_name')


class TestCrudFactoryNewEditRoutes(unittest.TestCase):
    """Test new/edit route creation."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for form testing

        self.mock_entity = Mock()
        self.mock_entity.name = 'test-entity'
        self.mock_entity.definition = 'test-definition'

        self.mock_get_by_name = Mock(return_value=self.mock_entity)
        self.mock_get_entities = Mock(return_value=[self.mock_entity])

        # Mock Form
        self.mock_form = Mock()
        self.mock_form.return_value = self.mock_form
        self.mock_form.validate_on_submit.return_value = False
        self.mock_form.name.data = ''
        self.mock_form.name.id = 'name'
        self.mock_form.definition.data = ''

        self.config = EntityRouteConfig(
            entity_class=Mock,
            entity_type='test',
            plural_name='tests',
            get_by_name_func=self.mock_get_by_name,
            get_entities_func=self.mock_get_entities,
            form_class=self.mock_form,
            form_template='test_form.html',
        )

    def _create_blueprint(self):
        return Blueprint('test', __name__)

    @patch('routes.crud_factory.create_new_route')
    @patch('routes.crud_factory.create_edit_route')
    def test_register_standard_crud_routes_registers_new_edit_if_template(self, mock_edit, mock_new):
        """Test register_standard_crud_routes registers new/edit if template is present."""
        bp = self._create_blueprint()
        register_standard_crud_routes(bp, self.config)

        mock_new.assert_called_once()
        mock_edit.assert_called_once()

    @patch('routes.crud_factory.create_new_route')
    @patch('routes.crud_factory.create_edit_route')
    def test_register_standard_crud_routes_skips_new_edit_if_no_template(self, mock_edit, mock_new):
        """Test register_standard_crud_routes skips new/edit if template is missing."""
        bp = self._create_blueprint()
        config_no_template = EntityRouteConfig(
            entity_class=Mock,
            entity_type='test',
            plural_name='tests',
            get_by_name_func=self.mock_get_by_name,
            get_entities_func=self.mock_get_entities,
            form_class=self.mock_form,
        )
        register_standard_crud_routes(bp, config_no_template)

        mock_new.assert_not_called()
        mock_edit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
