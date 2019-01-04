import copy
import datetime
import typing as t

from .base import Column

if t.TYPE_CHECKING:
    import table  # noqa
    from ..custom_types import Datetime  # noqa


class Varchar(Column):

    def __init__(self, length: int = 255, default: str = None,
                 **kwargs) -> None:
        self.length = length
        self.default = default
        super().__init__(**kwargs)

    def format_value(self, value: str):
        if not value:
            return 'null'
        # TODO sanitize input
        return f"'{value}'"


class Integer(Column):

    def __init__(self, default: int = None, **kwargs) -> None:
        self.default = default
        super().__init__(**kwargs)


class Serial(Column):

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)


class PrimaryKey(Column):

    column_type = 'SERIAL'

    def __init__(self, **kwargs) -> None:
        kwargs.update({
            'primary': True,
            'key': True
        })
        self.default = 'DEFAULT'
        super().__init__(**kwargs)


class Timestamp(Column):

    def __init__(self, default: 'Datetime' = None, **kwargs) -> None:
        self.default = default
        super().__init__(**kwargs)

    def format_value(self, value: t.Optional[datetime.datetime]):
        if not value:
            return 'null'
        dt_string = value.isoformat().replace('T', ' ')
        return f"'{dt_string}'"


class Boolean(Column):

    def __init__(self, default: bool = False, **kwargs) -> None:
        self.default = default
        super().__init__(**kwargs)


class ForeignKey(Integer):
    """
    Need to think about how this will work ...

    http://www.postgresqltutorial.com/postgresql-foreign-key/

    some_band.manager
    >>> 1
    Band.select.columns(Band.name, Band.manager.name)

    I'm not sure  about explicit joins ... only useful if we want to specify
    inner and outer joins.

    Join(Band, User)

    To get the actual User object.

    User.object().where(User.id == some_band.manager)

    OR

    some_band.related_object('manager')
    > is just a proxy to the above

    class Band(Table):
        manager = ForeignKey(User)

    To change the manager:
    some_band.manager = some_manager_id
    some_band.save()
    Or:
    some_band.set_related_object('manager', some_manager)

    """

    column_type = 'INTEGER'

    def __init__(self, references: t.Type['table.Table'], **kwargs) -> None:
        super().__init__(**kwargs)
        self.references = references

        # Allow columns on the referenced table to be accessed via auto
        # completion.
        for column in references.Meta.columns:
            # We have to set limits to the call chain because Table 1 can
            # reference Table 2, which references Table 1, creating an endless
            # loop. For now an arbitrary limit is set of 10 levels deep.
            # When querying a call chain more than 10 levels deep, an error
            # will be raised. Often there are more effective ways of
            # structuring a query than joining so many tables anyway.
            if len(column.call_chain) > 10:
                continue

            _column = copy.deepcopy(column)
            _column.call_chain.append(self)

            setattr(self, column._name, _column)
