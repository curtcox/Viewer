"""Server invocation tracking."""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Union

from sqlalchemy import or_

from cid import CID as ValidatedCID
from models import ServerInvocation
from db_access._common import save_entity


@dataclass(frozen=True)
class ServerInvocationInput:
    """Optional CID metadata recorded alongside a ``ServerInvocation``.

    Instances capture the optional content identifiers associated with an
    invocation.  ``create_server_invocation`` always requires
    ``server_name`` and ``result_cid`` arguments while all attributes on this
    helper remain optional.
    """
    # These fields may be supplied as either raw CID strings or validated
    # ``cid.CID`` instances.  The public helpers will normalize values before
    # persisting them to the database.
    servers_cid: Optional[Union[str, ValidatedCID]] = None
    variables_cid: Optional[Union[str, ValidatedCID]] = None
    secrets_cid: Optional[Union[str, ValidatedCID]] = None
    request_details_cid: Optional[Union[str, ValidatedCID]] = None
    invocation_cid: Optional[Union[str, ValidatedCID]] = None
    external_calls_cid: Optional[Union[str, ValidatedCID]] = None


def create_server_invocation(
    server_name: str,
    result_cid: Union[str, ValidatedCID],
    cid_metadata: Optional[
        Union[ServerInvocationInput, Dict[str, Optional[Union[str, ValidatedCID]]]]
    ] = None,
    **legacy_kwargs: Optional[Union[str, ValidatedCID]],
) -> ServerInvocation:
    """Persist a ``ServerInvocation`` record.

    Args:
        server_name: Name of the executed server.
        result_cid: CID that stores the invocation result payload.
        cid_metadata: Optional ``ServerInvocationInput`` (or mapping with the
            same keys) that captures auxiliary CIDs.  All fields on the data
            structure are optional.
        **legacy_kwargs: Backwards compatible keyword arguments matching the
            ``ServerInvocationInput`` fields.  This supports older call sites
            that have not yet adopted the container helper.

    Raises:
        TypeError: If ``cid_metadata`` is neither ``ServerInvocationInput`` nor
            a mapping of optional CID values.
    """
    field_names = set(ServerInvocationInput.__annotations__)
    merged: Dict[str, Optional[Union[str, ValidatedCID]]] = {}

    if isinstance(cid_metadata, ServerInvocationInput):
        merged.update(asdict(cid_metadata))
    elif isinstance(cid_metadata, dict):
        merged.update({k: cid_metadata[k] for k in cid_metadata if k in field_names})
    elif cid_metadata is not None:
        raise TypeError(
            "cid_metadata must be a ServerInvocationInput or mapping of optional CID fields"
        )

    merged.update({k: v for k, v in legacy_kwargs.items() if k in field_names})

    cid_data = ServerInvocationInput(**merged)

    def _normalize_optional(value: Optional[Union[str, ValidatedCID]]) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, ValidatedCID):
            return value.value
        return value

    invocation = ServerInvocation(
        server_name=server_name,
        result_cid=_normalize_optional(result_cid),
        servers_cid=_normalize_optional(cid_data.servers_cid),
        variables_cid=_normalize_optional(cid_data.variables_cid),
        secrets_cid=_normalize_optional(cid_data.secrets_cid),
        request_details_cid=_normalize_optional(cid_data.request_details_cid),
        invocation_cid=_normalize_optional(cid_data.invocation_cid),
        external_calls_cid=_normalize_optional(cid_data.external_calls_cid),
    )
    save_entity(invocation)
    return invocation


def get_server_invocations(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> List[ServerInvocation]:
    """Return invocation events ordered from newest to oldest."""

    query = ServerInvocation.query

    if start:
        query = query.filter(ServerInvocation.invoked_at >= start)
    if end:
        query = query.filter(ServerInvocation.invoked_at <= end)

    return (
        query
        .order_by(ServerInvocation.invoked_at.desc(), ServerInvocation.id.desc())
        .all()
    )


def get_server_invocations_by_server(server_name: str) -> List[ServerInvocation]:
    """Return invocation events for a specific server ordered from newest to oldest."""
    return (
        ServerInvocation.query
        .filter(ServerInvocation.server_name == server_name)
        .order_by(ServerInvocation.invoked_at.desc(), ServerInvocation.id.desc())
        .all()
    )


def get_server_invocations_by_result_cids(
    result_cids: Iterable[Union[str, ValidatedCID]],
) -> List[ServerInvocation]:
    """Return invocation events matching any of the provided result CIDs."""

    normalized_values = set()
    for cid in result_cids:
        if not cid:
            continue
        if isinstance(cid, ValidatedCID):
            normalized_values.add(cid.value)
        else:
            normalized_values.add(cid)

    cid_values = normalized_values
    if not cid_values:
        return []

    return (
        ServerInvocation.query
        .filter(ServerInvocation.result_cid.in_(cid_values))
        .order_by(ServerInvocation.invoked_at.desc(), ServerInvocation.id.desc())
        .all()
    )


def find_server_invocations_by_cid(
    cid_value: Union[str, ValidatedCID],
) -> List[ServerInvocation]:
    """Return invocation events that reference a CID in any tracked column."""
    if not cid_value:
        return []

    normalized_value = cid_value.value if isinstance(cid_value, ValidatedCID) else cid_value
    if not normalized_value:
        return []

    filters = [
        ServerInvocation.result_cid == normalized_value,
        ServerInvocation.invocation_cid == normalized_value,
        ServerInvocation.request_details_cid == normalized_value,
        ServerInvocation.servers_cid == normalized_value,
        ServerInvocation.variables_cid == normalized_value,
        ServerInvocation.secrets_cid == normalized_value,
        ServerInvocation.external_calls_cid == normalized_value,
    ]

    return ServerInvocation.query.filter(or_(*filters)).all()
