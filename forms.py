import re
from typing import Any, Optional as OptionalType

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import (
    BooleanField,
    RadioField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.fields.core import Field
from wtforms.validators import DataRequired, Optional, Regexp, ValidationError

from alias_definition import AliasDefinitionError, parse_alias_definition


def _strip_filter(value: Any) -> Any:
    return value.strip() if isinstance(value, str) else value

class EntityForm(FlaskForm):  # type: ignore[misc]
    """Base form for all entity types (Server, Variable, Secret).

    This base class consolidates common fields and validation logic that was
    previously duplicated across ServerForm, VariableForm, and SecretForm.

    The form automatically customizes labels based on the entity_type parameter.
    """

    name = StringField(
        'Name',
        validators=[
            DataRequired(),
            Regexp(
                r'^[a-zA-Z0-9._-]+$',
                message='Name can only contain letters, numbers, dots, hyphens, and underscores'
            )
        ],
        filters=[_strip_filter],
    )
    definition = TextAreaField(
        'Definition',
        validators=[DataRequired()],
        render_kw={'rows': 15}
    )
    enabled = BooleanField('Enabled', default=True)
    template = BooleanField('Template', default=False)
    submit = SubmitField('Save')

    def __init__(self, *args: Any, entity_type: str = 'Entity', **kwargs: Any) -> None:
        """Initialize the form with entity-specific labels.

        Args:
            *args: Positional arguments for FlaskForm
            entity_type: Type of entity (e.g., 'Server', 'Variable', 'Secret')
            **kwargs: Keyword arguments for FlaskForm
        """
        super().__init__(*args, **kwargs)
        self.name.label.text = f'{entity_type} Name'
        self.definition.label.text = f'{entity_type} Definition'
        self.submit.label.text = f'Save {entity_type}'

    def validate_name(self, field: Field) -> None:
        """Validate name format for URL safety."""
        if not re.match(r'^[a-zA-Z0-9._-]+$', field.data):
            raise ValidationError(f'{self.name.label.text} contains invalid characters for URLs')


class FileUploadForm(FlaskForm):  # type: ignore[misc]
    upload_type = RadioField('Upload Method', choices=[
        ('file', 'Upload File'),
        ('text', 'Paste Text'),
        ('url', 'Download from URL')
    ], default='file', validators=[DataRequired()])
    file = FileField('Choose File', validators=[Optional()])
    text_content = TextAreaField('Text Content', validators=[Optional()], render_kw={'rows': 10, 'placeholder': 'Paste your text content here...'})
    url = StringField('URL', validators=[Optional()], render_kw={'placeholder': 'https://example.com/file.pdf'})
    submit = SubmitField('Upload')

    def validate(self, extra_validators: OptionalType[Any] = None) -> bool:
        if not super().validate(extra_validators):
            return False

        if self.upload_type.data == 'file':
            if not self.file.data:
                self.file.errors.append('File is required when using file upload.')
                return False
        elif self.upload_type.data == 'text':
            if not self.text_content.data or not self.text_content.data.strip():
                self.text_content.errors.append('Text content is required when using text upload.')
                return False
        elif self.upload_type.data == 'url':
            if not self.url.data or not self.url.data.strip():
                self.url.errors.append('URL is required when using URL upload.')
                return False
            # Basic URL validation
            url = self.url.data.strip()
            if not (url.startswith('http://') or url.startswith('https://')):
                self.url.errors.append('URL must start with http:// or https://')
                return False

        return True


class EditCidForm(FlaskForm):  # type: ignore[misc]
    text_content = TextAreaField(
        'CID Content',
        validators=[DataRequired()],
        render_kw={'rows': 15, 'placeholder': 'Update the CID content here...'},
    )
    alias_name = StringField(
        'Alias Name (optional)',
        validators=[
            Optional(),
            Regexp(
                r'^[a-zA-Z0-9._-]+$',
                message='Alias name can only contain letters, numbers, dots, hyphens, and underscores',
            ),
        ],
        filters=[_strip_filter],
    )
    submit = SubmitField('Save Changes')

class ServerForm(EntityForm):
    """Form for server management."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize ServerForm with 'Server' labels."""
        super().__init__(*args, entity_type='Server', **kwargs)

class VariableForm(EntityForm):
    """Form for variable management."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize VariableForm with 'Variable' labels."""
        super().__init__(*args, entity_type='Variable', **kwargs)


class BulkVariablesForm(FlaskForm):  # type: ignore[misc]
    variables_json = TextAreaField(
        'Variables JSON',
        validators=[DataRequired()],
        render_kw={'rows': 18, 'spellcheck': 'false'},
    )
    submit = SubmitField('Save Variables')


class BulkSecretsForm(FlaskForm):  # type: ignore[misc]
    secrets_json = TextAreaField(
        'Secrets JSON',
        validators=[DataRequired()],
        render_kw={'rows': 18, 'spellcheck': 'false'},
    )
    submit = SubmitField('Save Secrets')

class AliasForm(FlaskForm):  # type: ignore[misc]
    name = StringField(
        'Alias Name',
        validators=[
            DataRequired(),
            Regexp(
                r'^[a-zA-Z0-9._-]+$',
                message='Alias name can only contain letters, numbers, dots, hyphens, and underscores'
            ),
        ],
        filters=[_strip_filter],
    )
    definition = TextAreaField(
        'Alias Definition',
        validators=[Optional()],
        filters=[_strip_filter],
        render_kw={
            'rows': 10,
            'placeholder': 'pattern -> /target [glob]\n# Add related aliases or notes on following lines',
        },
    )
    enabled = BooleanField('Enabled', default=True)
    template = BooleanField('Template', default=False)
    submit = SubmitField('Save Alias')

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._parsed_definition: Any = None

    @property
    def parsed_definition(self) -> Any:
        return self._parsed_definition

    def validate(self, extra_validators: OptionalType[Any] = None) -> bool:
        if not super().validate(extra_validators):
            return False

        try:
            self._parsed_definition = parse_alias_definition(
                self.definition.data or '',
                alias_name=self.name.data or None,
            )
        except AliasDefinitionError as exc:
            self.definition.errors.append(str(exc))
            return False

        return True


class SecretForm(EntityForm):
    """Form for secret management."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize SecretForm with 'Secret' labels."""
        super().__init__(*args, entity_type='Secret', **kwargs)


class ExportForm(FlaskForm):  # type: ignore[misc]
    snapshot = BooleanField('Snapshot', default=True)
    include_aliases = BooleanField('Aliases', default=True)
    include_disabled_aliases = BooleanField('Disabled aliases')
    include_template_aliases = BooleanField('Template aliases')
    selected_aliases = SelectMultipleField(coerce=str, validate_choice=False)
    include_servers = BooleanField('Servers', default=True)
    include_disabled_servers = BooleanField('Disabled servers')
    include_template_servers = BooleanField('Template servers')
    selected_servers = SelectMultipleField(coerce=str, validate_choice=False)
    include_variables = BooleanField('Variables', default=True)
    include_disabled_variables = BooleanField('Disabled variables')
    include_template_variables = BooleanField('Template variables')
    selected_variables = SelectMultipleField(coerce=str, validate_choice=False)
    include_secrets = BooleanField('Secrets')
    include_disabled_secrets = BooleanField('Disabled secrets')
    include_template_secrets = BooleanField('Template secrets')
    selected_secrets = SelectMultipleField(coerce=str, validate_choice=False)
    include_history = BooleanField('Change History')
    include_source = BooleanField('Application Source Files')
    include_cid_map = BooleanField('CID Content Map', default=True)
    include_unreferenced_cid_data = BooleanField('Include Unreferenced CID Content')
    secret_key = StringField(
        'Secret Encryption Key',
        validators=[Optional()],
        render_kw={'placeholder': 'Required when exporting secrets'},
    )
    submit = SubmitField('Generate JSON Export')

    def validate(self, extra_validators: OptionalType[Any] = None) -> bool:
        if not super().validate(extra_validators):
            return False

        if self.include_secrets.data and not (self.secret_key.data and self.secret_key.data.strip()):
            self.secret_key.errors.append('Encryption key is required when exporting secrets.')
            return False

        return True


class ImportForm(FlaskForm):  # type: ignore[misc]
    import_source = RadioField(
        'Import Method',
        choices=[
            ('file', 'Upload JSON File'),
            ('text', 'Paste JSON Text'),
            ('url', 'Load JSON from URL'),
        ],
        default='file',
        validators=[DataRequired()],
    )
    import_file = FileField('JSON File', validators=[Optional()])
    import_text = TextAreaField(
        'JSON Text',
        validators=[Optional()],
        render_kw={'rows': 10, 'placeholder': '{"aliases": []}'},
    )
    import_url = StringField(
        'JSON URL',
        validators=[Optional()],
        render_kw={'placeholder': 'https://example.com/export.json'},
    )
    include_aliases = BooleanField('Aliases')
    include_servers = BooleanField('Servers')
    include_variables = BooleanField('Variables')
    include_secrets = BooleanField('Secrets')
    include_history = BooleanField('Change History')
    include_source = BooleanField('Application Source Files')
    process_cid_map = BooleanField('Process CID Map', default=True)
    secret_key = StringField(
        'Secret Decryption Key',
        validators=[Optional()],
        render_kw={'placeholder': 'Required when importing secrets'},
    )
    submit = SubmitField('Import Data')

    def validate(self, extra_validators: OptionalType[Any] = None) -> bool:
        if not super().validate(extra_validators):
            return False

        if not any([
            self.include_aliases.data,
            self.include_servers.data,
            self.include_variables.data,
            self.include_secrets.data,
            self.include_history.data,
            self.include_source.data,
        ]):
            message = 'Select at least one data type to import.'
            self.include_aliases.errors.append(message)
            return False

        source = self.import_source.data
        if source == 'file':
            file_storage = self.import_file.data
            if not getattr(file_storage, 'filename', None):
                self.import_file.errors.append('Choose a JSON file to upload.')
                return False
        elif source == 'text':
            if not (self.import_text.data and self.import_text.data.strip()):
                self.import_text.errors.append('Paste JSON content to import.')
                return False
        elif source == 'url':
            if not (self.import_url.data and self.import_url.data.strip()):
                self.import_url.errors.append('Provide a URL to download JSON from.')
                return False

        if self.include_secrets.data and not (self.secret_key.data and self.secret_key.data.strip()):
            self.secret_key.errors.append('Decryption key is required when importing secrets.')
            return False

        return True
