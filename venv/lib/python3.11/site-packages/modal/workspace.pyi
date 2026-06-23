import datetime
import modal._workspace
import modal.client
import modal.object
import typing
import typing_extensions

class WorkspaceMemberInfo:
    """Metadata about a Workspace member."""

    name: str
    email: str
    user_id: str
    role: typing.Literal["user", "manager", "owner"]
    joined_at: datetime.datetime
    last_active_at: typing.Optional[datetime.datetime]

    def __init__(
        self,
        name: str,
        email: str,
        user_id: str,
        role: typing.Literal["user", "manager", "owner"],
        joined_at: datetime.datetime,
        last_active_at: typing.Optional[datetime.datetime],
    ) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
        ...

    def __repr__(self):
        """Return repr(self)."""
        ...

    def __eq__(self, other):
        """Return self==value."""
        ...

    def __setattr__(self, name, value):
        """Implement setattr(self, name, value)."""
        ...

    def __delattr__(self, name):
        """Implement delattr(self, name)."""
        ...

    def __hash__(self):
        """Return hash(self)."""
        ...

class Workspace(modal.object.Object):
    _name: typing.Optional[str]

    def __init__(self):
        """mdmd:hidden"""
        ...

    @property
    def name(self) -> typing.Optional[str]: ...
    @property
    def members(self) -> WorkspaceMembersManager: ...
    @staticmethod
    def from_context(*, client: typing.Optional[modal.client.Client] = None) -> Workspace:
        """Look up the Workspace associated with the current context.

        This returns the Workspace that the active Modal credentials authenticate against
        (i.e., your active profile or the `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET` environment
        variables). If called inside a Modal container, it returns the Workspace that the
        container is running in.
        """
        ...

class WorkspaceMembersManager:
    """mdmd:namespace
    Namespace with methods for managing the membership of a Workspace.
    """
    def __init__(self, workspace: Workspace):
        """mdmd:hidden"""
        ...

    class __list_spec(typing_extensions.Protocol):
        def __call__(self, /) -> list[modal._workspace.WorkspaceMemberInfo]:
            """Return the members of the Workspace.

            **Examples:**

            ```python notest
            members = modal.Workspace.from_context().members.list()
            print([m.name for m in members])
            ```
            """
            ...

        async def aio(self, /) -> list[modal._workspace.WorkspaceMemberInfo]:
            """Return the members of the Workspace.

            **Examples:**

            ```python notest
            members = modal.Workspace.from_context().members.list()
            print([m.name for m in members])
            ```
            """
            ...

    list: __list_spec
